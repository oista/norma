"""SQL catalog driver tests against SQLite in-memory (no network)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.oracle.base import OracleDialect
from sqlalchemy.dialects.postgresql.base import PGDialect

from norma.canalis.audit import CollectingAuditHook
from norma.canalis.capability import SQL_CATALOG
from norma.canalis.connector import ConnectorSpec
from norma.canalis.drivers.sql_catalog import SqlCatalogDriver, _paged_statement
from norma.canalis.errors import DriverUnavailable, PermanentError
from norma.canalis.paging import iterate
from norma.canalis.primitives import SqlQuery
from norma.canalis.records import PageRequest


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"))
        for i in range(5):
            conn.execute(
                text("INSERT INTO items (id, name) VALUES (:id, :name)"),
                {"id": i, "name": f"n{i}"},
            )
    return engine


def test_sql_catalog_paging(sqlite_engine) -> None:
    audit = CollectingAuditHook()
    driver = SqlCatalogDriver(
        ConnectorSpec(id="db", capability=SQL_CATALOG, endpoint="sqlite:///:memory:"),
        audit=audit,
        engine=sqlite_engine,
    )
    driver.connect()
    assert driver.health()
    page1 = driver.fetch_rows(
        SqlQuery("SELECT id, name FROM items ORDER BY id"),
        PageRequest(limit=2),
    )
    assert [r.data["id"] for r in page1.records] == [0, 1]
    assert page1.has_more
    assert page1.next_cursor == "offset:2"

    # Exact last full page must not claim has_more (limit+1 probe).
    page_last = driver.fetch_rows(
        SqlQuery("SELECT id, name FROM items ORDER BY id"),
        PageRequest(limit=2, cursor="offset:4"),
    )
    assert [r.data["id"] for r in page_last.records] == [4]
    assert not page_last.has_more
    assert page_last.next_cursor is None

    all_ids = [
        r.data["id"]
        for r in iterate(
            lambda req: driver.fetch_rows(
                SqlQuery("SELECT id, name FROM items ORDER BY id"), req
            ),
            limit=2,
        )
    ]
    assert all_ids == [0, 1, 2, 3, 4]
    assert any(e.outcome == "ok" for e in audit.events)
    driver.close()


def test_sql_extra_hint() -> None:
    err = DriverUnavailable(
        "sql.catalog driver requires sqlalchemy; install norma-canalis[sql]"
    )
    assert "norma-canalis[sql]" in str(err)


def test_paged_statement_oracle_compile() -> None:
    from sqlalchemy import literal_column, select, text

    stmt = _paged_statement(
        "SELECT id FROM items ORDER BY id",
        10,
        5,
        select,
        literal_column,
        text,
    )
    compiled = str(stmt.compile(dialect=OracleDialect(), compile_kwargs={"literal_binds": False}))
    upper = compiled.upper()
    assert "FETCH" in upper
    assert "LIMIT" not in upper


def test_paged_statement_pg_compile() -> None:
    from sqlalchemy import literal_column, select, text

    stmt = _paged_statement(
        "SELECT id FROM items ORDER BY id",
        10,
        5,
        select,
        literal_column,
        text,
    )
    compiled = str(stmt.compile(dialect=PGDialect(), compile_kwargs={"literal_binds": False}))
    upper = compiled.upper()
    assert "LIMIT" in upper
    assert "OFFSET" in upper


def test_paging_none(sqlite_engine) -> None:
    driver = SqlCatalogDriver(
        ConnectorSpec(
            id="db",
            capability=SQL_CATALOG,
            endpoint="sqlite:///:memory:",
            options={"paging": "none"},
        ),
        engine=sqlite_engine,
    )
    driver.connect()
    page = driver.fetch_rows(
        SqlQuery("SELECT id, name FROM items ORDER BY id"),
        PageRequest(limit=2),
    )
    assert [r.data["id"] for r in page.records] == [0, 1, 2, 3, 4]
    assert not page.has_more
    assert page.next_cursor is None
    driver.close()


def test_paging_none_rejects_cursor(sqlite_engine) -> None:
    driver = SqlCatalogDriver(
        ConnectorSpec(
            id="db",
            capability=SQL_CATALOG,
            endpoint="sqlite:///:memory:",
            options={"paging": "none"},
        ),
        engine=sqlite_engine,
    )
    driver.connect()
    with pytest.raises(PermanentError, match="paging=none"):
        driver.fetch_rows(
            SqlQuery("SELECT id FROM items"),
            PageRequest(limit=2, cursor="offset:2"),
        )
    driver.close()


def test_paging_option_rejected_unknown(sqlite_engine) -> None:
    driver = SqlCatalogDriver(
        ConnectorSpec(
            id="db",
            capability=SQL_CATALOG,
            endpoint="sqlite:///:memory:",
            options={"paging": "keyset"},
        ),
        engine=sqlite_engine,
    )
    with pytest.raises(PermanentError, match="auto\\|none"):
        driver.connect()
