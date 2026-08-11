"""Tests for git.repo driver (GitLab API style) against MockTransport."""

from __future__ import annotations

import httpx
import pytest

from norma.canalis.audit import CollectingAuditHook
from norma.canalis.capability import GIT_REPO
from norma.canalis.connector import ConnectorSpec
from norma.canalis.drivers.git_repo import GitRepoDriver
from norma.canalis.errors import RateLimited
from norma.canalis.primitives import BlobRequest, DocumentRequest
from norma.canalis.records import PageRequest


def _spec(**opts) -> ConnectorSpec:
    options = {"api_style": "gitlab", "project_id": 42, **opts}
    return ConnectorSpec(
        id="repo",
        capability=GIT_REPO,
        endpoint="https://gitlab.example",
        options=options,
    )


def test_git_repo_tree_and_blob() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url.path))
        if request.url.path.endswith("/repository/tree"):
            return httpx.Response(
                200,
                json=[
                    {"id": "abc", "path": "a.sql", "type": "blob", "size": 10},
                    {"id": "def", "path": "dir", "type": "tree"},
                ],
            )
        if "/repository/files/" in request.url.path and request.url.path.endswith("/raw"):
            return httpx.Response(200, content=b"select 1")
        return httpx.Response(404, text="nope")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://gitlab.example",
    )
    audit = CollectingAuditHook()
    driver = GitRepoDriver(_spec(), audit=audit, client=client)
    driver.connect()

    page = driver.fetch_documents(
        DocumentRequest(path="tree", params={"ref": "main"}),
        PageRequest(limit=100),
    )
    assert len(page.records) == 2
    assert page.records[0].data["path"] == "a.sql"

    blob = driver.fetch_blob(BlobRequest(path="a.sql", params={"ref": "main"}))
    assert blob == b"select 1"
    assert any(e.operation == "fetch_blob" for e in audit.events)
    driver.close()


def test_git_repo_resolve_commits() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{"id": "deadbeef", "title": "init"}],
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://gitlab.example",
    )
    driver = GitRepoDriver(_spec(), client=client)
    driver.connect()
    page = driver.fetch_documents(
        DocumentRequest(path="commits", params={"ref": "main"}),
        PageRequest(limit=1),
    )
    assert page.records[0].data["id"] == "deadbeef"
    driver.close()


def test_git_repo_rate_limited() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "3"}, text="slow")

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://gitlab.example",
    )
    driver = GitRepoDriver(_spec(), client=client)
    driver.connect()
    with pytest.raises(RateLimited) as ei:
        driver.fetch_documents(DocumentRequest(path="tree"), PageRequest(limit=10))
    assert ei.value.retry_after == 3.0
    driver.close()
