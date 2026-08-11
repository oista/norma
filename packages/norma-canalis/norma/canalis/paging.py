"""Page iteration helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TypeVar

from norma.canalis.errors import PermanentError
from norma.canalis.records import Page, PageRequest, Record

T = TypeVar("T")

DEFAULT_MAX_PAGES = 10_000


def iterate(
    fetch: Callable[[PageRequest], Page],
    *,
    limit: int = 100,
    cursor: str | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> Iterator[Record]:
    """Yield records across pages until exhausted or *max_pages* is hit."""
    if max_pages < 1:
        raise PermanentError("max_pages must be >= 1")
    request = PageRequest(limit=limit, cursor=cursor)
    pages = 0
    while True:
        pages += 1
        if pages > max_pages:
            raise PermanentError(
                f"paging aborted: exceeded max_pages={max_pages}"
            )
        page = fetch(request)
        yield from page.records
        if not page.has_more or page.next_cursor is None:
            return
        request = PageRequest(limit=limit, cursor=page.next_cursor)
