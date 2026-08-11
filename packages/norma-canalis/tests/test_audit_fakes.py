"""Tests for audit hooks and fake sources."""

from __future__ import annotations

import pytest

from norma.canalis.audit import AuditEvent, CollectingAuditHook, NullAuditHook
from norma.canalis.errors import TransientError
from norma.canalis.paging import iterate
from norma.canalis.primitives import DocumentRequest, SqlQuery
from norma.canalis.records import PageRequest
from norma.canalis.testing import FakeDocumentSource, FakeRowSource


def test_collecting_audit_hook() -> None:
    hook = CollectingAuditHook()
    hook.emit(
        AuditEvent(
            connector_id="c1",
            capability="http.rest",
            operation="fetch_documents",
            outcome="ok",
            record_count=2,
        )
    )
    assert len(hook.events) == 1
    assert hook.events[0].record_count == 2
    NullAuditHook().emit(hook.events[0])
    hook.clear()
    assert hook.events == []


def test_fake_row_source_paging() -> None:
    rows = [{"id": i} for i in range(5)]
    src = FakeRowSource(rows=rows)
    page1 = src.fetch_rows(SqlQuery("select 1"), PageRequest(limit=2))
    assert len(page1.records) == 2
    assert page1.has_more
    page2 = src.fetch_rows(
        SqlQuery("select 1"), PageRequest(limit=2, cursor=page1.next_cursor)
    )
    assert [r.data["id"] for r in page2.records] == [2, 3]
    all_ids = [r.data["id"] for r in iterate(lambda req: src.fetch_rows(SqlQuery("q"), req), limit=2)]
    # src already advanced; re-create
    src2 = FakeRowSource(rows=rows)
    all_ids = [
        r.data["id"]
        for r in iterate(lambda req: src2.fetch_rows(SqlQuery("q"), req), limit=2)
    ]
    assert all_ids == [0, 1, 2, 3, 4]


def test_fake_document_failure_injection() -> None:
    src = FakeDocumentSource(
        documents=[{"n": 1}],
        fail_on_call=1,
        fail_with=TransientError("nope"),
    )
    with pytest.raises(TransientError):
        src.fetch_documents(DocumentRequest(path="/x"), PageRequest(limit=10))
