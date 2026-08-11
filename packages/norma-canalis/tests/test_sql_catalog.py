"""SQL catalog driver tests against SQLite in-memory (no network)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from norma.canalis.audit import CollectingAuditHook
from norma.canalis.capability import SQL_CATALOG
from norma.canalis.connector import ConnectorSpec
from norma.canalis.drivers.sql_catalog import SqlCatalogDriver
from norma.canalis.errors import DriverUnavailable
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
