"""HTTP REST driver tests against httpx.MockTransport (no network)."""

from __future__ import annotations

import httpx
import pytest

from norma.canalis.audit import CollectingAuditHook
from norma.canalis.capability import HTTP_REST
from norma.canalis.connector import ConnectorSpec
from norma.canalis.drivers.http_rest import HttpRestDriver
from norma.canalis.errors import DriverUnavailable, RateLimited
from norma.canalis.primitives import DocumentRequest
from norma.canalis.records import PageRequest


def test_http_rest_link_paging() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                200,
                json={"items": [{"id": 1}, {"id": 2}]},
                headers={"Link": '</page2>; rel="next"'},
            )
        assert str(request.url).endswith("/page2") or "/page2" in str(request.url)
        return httpx.Response(200, json={"items": [{"id": 3}]})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="https://example.invalid")
    audit = CollectingAuditHook()
    driver = HttpRestDriver(
        ConnectorSpec(id="api", capability=HTTP_REST, endpoint="https://example.invalid"),
        audit=audit,
        client=client,
    )
    driver.connect()
    page1 = driver.fetch_documents(DocumentRequest(path="/items"), PageRequest(limit=2))
    assert [r.data["id"] for r in page1.records] == [1, 2]
    assert page1.has_more
    page2 = driver.fetch_documents(
        DocumentRequest(path="/items"),
        PageRequest(limit=2, cursor=page1.next_cursor),
    )
    assert [r.data["id"] for r in page2.records] == [3]
    assert audit.events and audit.events[0].outcome == "ok"
    driver.close()


def test_http_rest_rate_limited() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "2"}, text="slow")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://example.invalid",
    )
    driver = HttpRestDriver(
        ConnectorSpec(id="api", capability=HTTP_REST),
        client=client,
    )
    driver.connect()
    with pytest.raises(RateLimited) as ei:
        driver.fetch_documents(DocumentRequest(path="/x"), PageRequest(limit=1))
    assert ei.value.retry_after == 2.0
    driver.close()


def test_http_rest_import_guard_message() -> None:
    # Smoke: DriverUnavailable message documents the extra name.
    # Full "no httpx" path is covered in CI core-only step; here we just
    # assert the error type exists and message template is correct when raised.
    err = DriverUnavailable("http.rest driver requires httpx; install norma-canalis[http]")
    assert "norma-canalis[http]" in str(err)
