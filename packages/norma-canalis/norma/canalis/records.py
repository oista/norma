"""Record and page types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Record:
    """Opaque payload from an external system plus a source URI."""

    data: dict[str, Any]
    source_uri: str = ""


@dataclass(frozen=True)
class PageRequest:
    """Paging request; *cursor* is driver-opaque (offset, keyset token, Link URL)."""

    limit: int = 100
    cursor: str | None = None

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("PageRequest.limit must be >= 1")


@dataclass(frozen=True)
class Page:
    """One page of records."""

    records: tuple[Record, ...] = ()
    next_cursor: str | None = None
    has_more: bool = False

    @classmethod
    def empty(cls) -> Page:
        return cls(records=(), next_cursor=None, has_more=False)
