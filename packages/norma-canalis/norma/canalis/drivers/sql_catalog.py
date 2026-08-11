"""SQL catalog driver (capability sql.catalog). Requires extras: norma-canalis[sql]."""

from __future__ import annotations

import time
from typing import Any, Literal

from norma.canalis.audit import AuditEvent, AuditHook, NullAuditHook
from norma.canalis.capability import SQL_CATALOG
from norma.canalis.connector import ConnectorSpec
from norma.canalis.errors import ConnectError, DriverUnavailable, PermanentError
from norma.canalis.primitives import SqlQuery
from norma.canalis.records import Page, PageRequest, Record
from norma.canalis.secrets import SecretRef, SecretResolver

PagingMode = Literal["auto", "none"]
_VALID_PAGING = frozenset({"auto", "none"})


def _require_sqlalchemy():  # type: ignore[no-untyped-def]
    try:
        import sqlalchemy
        from sqlalchemy import create_engine, literal_column, select, text
    except ImportError as exc:
        raise DriverUnavailable(
            "sql.catalog driver requires sqlalchemy; install norma-canalis[sql]"
        ) from exc
    return sqlalchemy, create_engine, text, select, literal_column


def _paged_statement(sql: str, limit: int, offset: int, select, literal_column, text):  # type: ignore[no-untyped-def]
    """Wrap product SQL via SQLAlchemy constructors; dialect picks LIMIT vs FETCH FIRST.

    Alias without ``AS`` so the form is valid on Oracle and on PG/SQLite.
    """
    inner = text(f"({sql}) _canalis_q")
    return (
        select(literal_column("*"))
        .select_from(inner)
        .limit(limit)
        .offset(offset)
    )


class SqlCatalogDriver:
    """RowSource over SQLAlchemy Engine / DB-API."""

    capability = SQL_CATALOG

    def __init__(
        self,
        spec: ConnectorSpec,
        resolver: SecretResolver | None = None,
        audit: AuditHook | None = None,
        *,
        engine: Any | None = None,
        **_kwargs: Any,
    ) -> None:
        self._spec = spec
        self._resolver = resolver
        self._audit = audit or NullAuditHook()
        self._engine = engine
        self._owns_engine = engine is None
        self._connected = False
        self._text = None
        self._select = None
        self._literal_column = None
        self._paging: PagingMode = "auto"

    def connect(self) -> None:
        _, create_engine, text, select, literal_column = _require_sqlalchemy()
        self._text = text
        self._select = select
        self._literal_column = literal_column

        raw = str(self._spec.options.get("paging", "auto")).strip().lower()
        if raw not in _VALID_PAGING:
            raise PermanentError(
                f"unsupported options.paging {raw!r}; expected auto|none"
            )
        self._paging = raw  # type: ignore[assignment]

        if self._engine is None:
            url = self._spec.endpoint
            if not url:
                raise ConnectError(
                    "sql.catalog ConnectorSpec.endpoint (DB URL) is required"
                )
            if self._resolver is not None and self._spec.secrets:
                for ref in self._spec.secrets:
                    secret = self._resolver.resolve(ref)
                    url = url.replace("{" + ref.name + "}", secret.get())
                pwd_env = self._spec.options.get("password_secret")
                if pwd_env:
                    secret = self._resolver.resolve(
                        SecretRef(name="password", env=str(pwd_env))
                    )
                    url = url.replace("{password}", secret.get())
            self._engine = create_engine(url, future=True)
            self._owns_engine = True
        self._connected = True

    def close(self) -> None:
        if self._owns_engine and self._engine is not None:
            self._engine.dispose()
        self._connected = False

    def capabilities(self) -> frozenset[str]:
        return frozenset({SQL_CATALOG})

    def health(self) -> bool:
        if not self._connected or self._engine is None:
            return False
        try:
            with self._engine.connect() as conn:
                conn.execute(self._text("SELECT 1"))
            return True
        except Exception:
            return False

    def __enter__(self) -> SqlCatalogDriver:
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_rows(self, query: SqlQuery, page: PageRequest) -> Page:
        if (
            self._engine is None
            or self._text is None
            or self._select is None
            or self._literal_column is None
        ):
            raise ConnectError("SqlCatalogDriver is not connected")
        started = time.perf_counter()
        try:
            if self._paging == "none":
                return self._fetch_none(query, page, started)
            return self._fetch_auto(query, page, started)
        except Exception as exc:
            if not isinstance(exc, PermanentError):
                self._audit.emit(
                    AuditEvent(
                        connector_id=self._spec.id,
                        capability=SQL_CATALOG,
                        operation="fetch_rows",
                        target=query.text[:120],
                        duration_ms=(time.perf_counter() - started) * 1000,
                        outcome="error",
                        error_kind=type(exc).__name__,
                    )
                )
            raise

    def _fetch_none(self, query: SqlQuery, page: PageRequest, started: float) -> Page:
        if page.cursor:
            raise PermanentError(
                "paging=none does not support cursors; omit PageRequest.cursor "
                "or set options.paging=auto"
            )
        params = dict(query.params)
        with self._engine.connect() as conn:
            result = conn.execute(self._text(query.text), params)
            rows = result.mappings().all()
        records = tuple(
            Record(data=dict(row), source_uri=f"{self._spec.id}#{i}")
            for i, row in enumerate(rows)
        )
        self._audit.emit(
            AuditEvent(
                connector_id=self._spec.id,
                capability=SQL_CATALOG,
                operation="fetch_rows",
                target=query.text[:120],
                duration_ms=(time.perf_counter() - started) * 1000,
                outcome="ok",
                record_count=len(records),
            )
        )
        return Page(records=records, next_cursor=None, has_more=False)

    def _fetch_auto(self, query: SqlQuery, page: PageRequest, started: float) -> Page:
        offset = 0
        if page.cursor:
            if not page.cursor.startswith("offset:"):
                raise PermanentError(
                    f"unsupported cursor {page.cursor!r}; expected offset:N"
                )
            offset = int(page.cursor.split(":", 1)[1])
        # Fetch limit+1 so has_more does not emit a trailing empty page.
        fetch_n = page.limit + 1
        stmt = _paged_statement(
            query.text,
            fetch_n,
            offset,
            self._select,
            self._literal_column,
            self._text,
        )
        params = dict(query.params)
        with self._engine.connect() as conn:
            result = conn.execute(stmt, params)
            rows = result.mappings().all()
        has_more = len(rows) > page.limit
        rows = rows[: page.limit]
        records = tuple(
            Record(
                data=dict(row),
                source_uri=f"{self._spec.id}#{offset + i}",
            )
            for i, row in enumerate(rows)
        )
        next_cursor = f"offset:{offset + page.limit}" if has_more else None
        self._audit.emit(
            AuditEvent(
                connector_id=self._spec.id,
                capability=SQL_CATALOG,
                operation="fetch_rows",
                target=query.text[:120],
                duration_ms=(time.perf_counter() - started) * 1000,
                outcome="ok",
                record_count=len(records),
            )
        )
        return Page(
            records=records,
            next_cursor=next_cursor,
            has_more=has_more,
        )
