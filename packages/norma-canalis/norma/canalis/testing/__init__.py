"""Programmable fakes for product adapter tests (no corporate endpoints)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from norma.canalis.capability import HTTP_REST, SQL_CATALOG
from norma.canalis.errors import CanalisError
from norma.canalis.primitives import DocumentRequest, SqlQuery
from norma.canalis.records import Page, PageRequest, Record


@dataclass
class FakeRowSource:
    """In-memory RowSource with optional failure injection."""

    rows: Sequence[dict] = ()
    source_uri_prefix: str = "fake://rows"
    fail_on_call: int | None = None
    fail_with: CanalisError | None = None
    _call_count: int = field(default=0, init=False, repr=False)

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def capabilities(self) -> frozenset[str]:
        return frozenset({SQL_CATALOG})

    def health(self) -> bool:
        return True

    def __enter__(self) -> FakeRowSource:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def fetch_rows(self, query: SqlQuery, page: PageRequest) -> Page:
        self._call_count += 1
        if self.fail_on_call is not None and self._call_count == self.fail_on_call:
            raise self.fail_with or CanalisError("injected failure")
        offset = 0
        if page.cursor and page.cursor.startswith("offset:"):
            offset = int(page.cursor.split(":", 1)[1])
        chunk = list(self.rows[offset : offset + page.limit])
        records = tuple(
            Record(data=dict(row), source_uri=f"{self.source_uri_prefix}/{offset + i}")
            for i, row in enumerate(chunk)
        )
        next_offset = offset + page.limit
        has_more = next_offset < len(self.rows)
        return Page(
            records=records,
            next_cursor=f"offset:{next_offset}" if has_more else None,
            has_more=has_more,
        )


@dataclass
class FakeDocumentSource:
    """In-memory DocumentSource with optional failure injection."""

    documents: Sequence[dict] = ()
    source_uri_prefix: str = "fake://docs"
    fail_on_call: int | None = None
    fail_with: CanalisError | None = None
    page_factory: Callable[[DocumentRequest, PageRequest], Page] | None = None
    _call_count: int = field(default=0, init=False, repr=False)

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def capabilities(self) -> frozenset[str]:
        return frozenset({HTTP_REST})

    def health(self) -> bool:
        return True

    def __enter__(self) -> FakeDocumentSource:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def fetch_documents(self, request: DocumentRequest, page: PageRequest) -> Page:
        self._call_count += 1
        if self.fail_on_call is not None and self._call_count == self.fail_on_call:
            raise self.fail_with or CanalisError("injected failure")
        if self.page_factory is not None:
            return self.page_factory(request, page)
        offset = 0
        if page.cursor and page.cursor.startswith("offset:"):
            offset = int(page.cursor.split(":", 1)[1])
        chunk = list(self.documents[offset : offset + page.limit])
        records = tuple(
            Record(data=dict(doc), source_uri=f"{self.source_uri_prefix}/{offset + i}")
            for i, doc in enumerate(chunk)
        )
        next_offset = offset + page.limit
        has_more = next_offset < len(self.documents)
        return Page(
            records=records,
            next_cursor=f"offset:{next_offset}" if has_more else None,
            has_more=has_more,
        )
