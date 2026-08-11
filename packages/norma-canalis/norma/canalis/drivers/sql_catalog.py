"""SQL catalog driver (capability sql.catalog). Requires extras: norma-canalis[sql]."""

from __future__ import annotations

import time
from typing import Any

from norma.canalis.audit import AuditEvent, AuditHook, NullAuditHook
from norma.canalis.capability import SQL_CATALOG
from norma.canalis.connector import ConnectorSpec
from norma.canalis.errors import ConnectError, DriverUnavailable, PermanentError
from norma.canalis.primitives import SqlQuery
from norma.canalis.records import Page, PageRequest, Record
from norma.canalis.secrets import SecretRef, SecretResolver


def _require_sqlalchemy():  # type: ignore[no-untyped-def]
    try:
        import sqlalchemy
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise DriverUnavailable(
            "sql.catalog driver requires sqlalchemy; install norma-canalis[sql]"
        ) from exc
    return sqlalchemy, create_engine, text


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

    def connect(self) -> None:
        _, create_engine, text = _require_sqlalchemy()
        self._text = text
        if self._engine is None:
            url = self._spec.endpoint
            if not url:
                raise ConnectError("sql.catalog ConnectorSpec.endpoint (DB URL) is required")
            # Optional password injection from secrets
            if self._resolver is not None and self._spec.secrets:
                for ref in self._spec.secrets:
                    secret = self._resolver.resolve(ref)
                    # Replace {name} placeholders in URL
                    url = url.replace("{" + ref.name + "}", secret.get())
                # Also support options password_secret env override into URL via query
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
        if self._engine is None or self._text is None:
            raise ConnectError("SqlCatalogDriver is not connected")
        started = time.perf_counter()
        offset = 0
        if page.cursor:
            if not page.cursor.startswith("offset:"):
                raise PermanentError(
                    f"unsupported cursor {page.cursor!r}; expected offset:N"
                )
            offset = int(page.cursor.split(":", 1)[1])
        # Wrap product SQL with LIMIT/OFFSET for portable paging (SQLite/Postgres).
        # Products that need keyset should pass already-paged SQL and limit=page size.
        paged_sql = (
            f"SELECT * FROM ({query.text}) AS _canalis_q "
            f"LIMIT :_canalis_limit OFFSET :_canalis_offset"
        )
        params = dict(query.params)
        params["_canalis_limit"] = page.limit
        params["_canalis_offset"] = offset
        try:
            with self._engine.connect() as conn:
                result = conn.execute(self._text(paged_sql), params)
                rows = result.mappings().all()
            records = [
                Record(
                    data=dict(row),
                    source_uri=f"{self._spec.id}#{offset + i}",
                )
                for i, row in enumerate(rows)
            ]
            has_more = len(records) >= page.limit
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
                records=tuple(records),
                next_cursor=next_cursor,
                has_more=has_more,
            )
        except Exception as exc:
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
