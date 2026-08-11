"""Typed read primitives (Protocol mixins on Connector).

Corporate catalog models (e.g. product-specific views) stay in products;
here only generic SQL text + bind params / document requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from norma.canalis.records import Page, PageRequest


@dataclass(frozen=True)
class SqlQuery:
    """Parameterized SQL; *text* is dialect-specific, owned by the product."""

    text: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentRequest:
    """Fetch documents / API resources by path or filter."""

    path: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BlobRequest:
    """Fetch a binary or text blob by path."""

    path: str
    params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class RowSource(Protocol):
    def fetch_rows(self, query: SqlQuery, page: PageRequest) -> Page:
        """Execute *query* and return one page of row Records."""
        ...


@runtime_checkable
class DocumentSource(Protocol):
    def fetch_documents(self, request: DocumentRequest, page: PageRequest) -> Page:
        """Fetch one page of document Records."""
        ...


@runtime_checkable
class BlobSource(Protocol):
    def fetch_blob(self, request: BlobRequest) -> bytes:
        """Fetch raw bytes for *request*."""
        ...
