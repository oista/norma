"""Tests for paging.iterate."""

from __future__ import annotations

import pytest

from norma.canalis.errors import PermanentError
from norma.canalis.paging import iterate
from norma.canalis.records import Page, PageRequest, Record


def test_iterate_across_cursors() -> None:
    pages = {
        None: Page(
            records=(Record({"i": 1}), Record({"i": 2})),
            next_cursor="c2",
            has_more=True,
        ),
        "c2": Page(
            records=(Record({"i": 3}),),
            next_cursor=None,
            has_more=False,
        ),
    }

    def fetch(req: PageRequest) -> Page:
        return pages[req.cursor]

    values = [r.data["i"] for r in iterate(fetch, limit=2)]
    assert values == [1, 2, 3]


def test_iterate_max_pages_guard() -> None:
    def forever(req: PageRequest) -> Page:
        return Page(
            records=(Record({"c": req.cursor}),),
            next_cursor="next",
            has_more=True,
        )

    with pytest.raises(PermanentError, match="max_pages"):
        list(iterate(forever, max_pages=3))
