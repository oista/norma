"""Git repo driver (capability git.repo). Requires extras: norma-canalis[git].

api_style=gitlab is the only style in v0.2 (GitLab REST API v4).
Product-specific filters (SQL globs, path filters) stay in products.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

from norma.canalis.audit import AuditEvent, AuditHook, NullAuditHook
from norma.canalis.capability import GIT_REPO
from norma.canalis.connector import ConnectorSpec
from norma.canalis.errors import (
    AuthError,
    ConnectError,
    DriverUnavailable,
    NotFoundError,
    PermanentError,
    RateLimited,
    TransientError,
)
from norma.canalis.primitives import BlobRequest, DocumentRequest
from norma.canalis.records import Page, PageRequest, Record
from norma.canalis.secrets import SecretRef, SecretResolver


def _require_httpx():  # type: ignore[no-untyped-def]
    try:
        import httpx
    except ImportError as exc:
        raise DriverUnavailable(
            "git.repo driver requires httpx; install norma-canalis[git]"
        ) from exc
    return httpx


def _parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            start = section.find("<")
            end = section.find(">")
            if start >= 0 and end > start:
                return section[start + 1 : end]
    return None


class GitRepoDriver:
    """DocumentSource + BlobSource over GitLab-style repository HTTP APIs."""

    capability = GIT_REPO

    def __init__(
        self,
        spec: ConnectorSpec,
        resolver: SecretResolver | None = None,
        audit: AuditHook | None = None,
        *,
        client: Any | None = None,
        **_kwargs: Any,
    ) -> None:
        self._spec = spec
        self._resolver = resolver
        self._audit = audit or NullAuditHook()
        self._client = client
        self._owns_client = client is None
        self._connected = False
        api_style = str(self._spec.options.get("api_style", "gitlab"))
        if api_style != "gitlab":
            raise PermanentError(
                f"unsupported api_style {api_style!r}; v0.2 supports only 'gitlab'"
            )
        self._project = self._spec.options.get("project_id")
        if self._project is None:
            self._project = self._spec.options.get("project")
        if self._project is None:
            raise PermanentError(
                "git.repo requires options.project_id (int) or options.project "
                "(path with namespace)"
            )

    def connect(self) -> None:
        httpx = _require_httpx()
        if self._client is None:
            headers: dict[str, str] = {}
            # Prefer explicit secrets on ConnectorSpec; fall back to options.token_secret
            token_ref: SecretRef | None = None
            if self._spec.secrets:
                token_ref = self._spec.secrets[0]
            elif self._spec.options.get("token_secret"):
                token_ref = SecretRef(
                    name="token", env=str(self._spec.options["token_secret"])
                )
            if token_ref is not None and self._resolver is not None:
                secret = self._resolver.resolve(token_ref)
                header_name = str(
                    self._spec.options.get("token_header", "PRIVATE-TOKEN")
                )
                prefix = str(self._spec.options.get("token_prefix", ""))
                headers[header_name] = f"{prefix}{secret.get()}"
            timeout = float(self._spec.options.get("timeout", 60.0))
            base = self._spec.endpoint.rstrip("/") if self._spec.endpoint else ""
            self._client = httpx.Client(
                base_url=base, headers=headers, timeout=timeout
            )
            self._owns_client = True
        self._connected = True

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
        self._connected = False

    def capabilities(self) -> frozenset[str]:
        return frozenset({GIT_REPO})

    def health(self) -> bool:
        return self._connected and self._client is not None

    def __enter__(self) -> GitRepoDriver:
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _project_segment(self) -> str:
        project = self._project
        if isinstance(project, int) or (isinstance(project, str) and project.isdigit()):
            return str(project)
        return quote(str(project), safe="")

    def fetch_documents(self, request: DocumentRequest, page: PageRequest) -> Page:
        started = time.perf_counter()
        op = request.path or "tree"
        try:
            if op in ("tree", "list", ""):
                page_out = self._fetch_tree(request, page)
            elif op in ("commits", "resolve_ref"):
                page_out = self._fetch_commits(request, page)
            elif op in ("project", "repo"):
                page_out = self._fetch_project()
            else:
                raise PermanentError(
                    f"unknown git.repo document path {op!r}; "
                    f"expected tree|commits|project"
                )
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=GIT_REPO,
                    operation="fetch_documents",
                    target=op,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="ok",
                    record_count=len(page_out.records),
                )
            )
            return page_out
        except Exception as exc:
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=GIT_REPO,
                    operation="fetch_documents",
                    target=op,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="error",
                    error_kind=type(exc).__name__,
                )
            )
            raise

    def fetch_blob(self, request: BlobRequest) -> bytes:
        started = time.perf_counter()
        try:
            ref = str(request.params.get("ref", "HEAD"))
            encoded = quote(request.path, safe="")
            url = (
                f"/api/v4/projects/{self._project_segment()}"
                f"/repository/files/{encoded}/raw"
            )
            response = self._request("GET", url, params={"ref": ref})
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=GIT_REPO,
                    operation="fetch_blob",
                    target=request.path,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="ok",
                    record_count=1,
                )
            )
            return response.content
        except Exception as exc:
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=GIT_REPO,
                    operation="fetch_blob",
                    target=request.path,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="error",
                    error_kind=type(exc).__name__,
                )
            )
            raise

    def _fetch_tree(self, request: DocumentRequest, page: PageRequest) -> Page:
        ref = str(request.params.get("ref", "HEAD"))
        recursive = bool(request.params.get("recursive", True))
        per_page = page.limit
        url: str
        absolute = False
        params: dict[str, Any] | None
        if page.cursor and (
            page.cursor.startswith("http://")
            or page.cursor.startswith("https://")
            or page.cursor.startswith("/")
        ):
            url = page.cursor
            absolute = page.cursor.startswith("http")
            params = None
        else:
            url = f"/api/v4/projects/{self._project_segment()}/repository/tree"
            params = {
                "ref": ref,
                "recursive": recursive,
                "per_page": per_page,
                "pagination": "keyset",
            }
            if page.cursor:
                params["page_token"] = page.cursor

        response = self._request("GET", url, params=params, absolute_url=absolute)
        items = response.json()
        if not isinstance(items, list):
            items = []
        records = [
            Record(data=dict(item), source_uri=str(response.url))
            for item in items
            if isinstance(item, dict)
        ]
        link_next = _parse_link_next(response.headers.get("Link"))
        if link_next:
            return Page(records=tuple(records), next_cursor=link_next, has_more=True)
        return Page(records=tuple(records), next_cursor=None, has_more=False)

    def _fetch_commits(self, request: DocumentRequest, page: PageRequest) -> Page:
        ref = str(request.params.get("ref", "HEAD"))
        url = f"/api/v4/projects/{self._project_segment()}/repository/commits"
        response = self._request(
            "GET",
            url,
            params={"ref_name": ref, "per_page": page.limit},
        )
        items = response.json()
        if not isinstance(items, list):
            items = []
        records = [
            Record(data=dict(item), source_uri=str(response.url))
            for item in items
            if isinstance(item, dict)
        ]
        return Page(records=tuple(records), next_cursor=None, has_more=False)

    def _fetch_project(self) -> Page:
        url = f"/api/v4/projects/{self._project_segment()}"
        response = self._request("GET", url)
        payload = response.json()
        data = payload if isinstance(payload, dict) else {"value": payload}
        return Page(
            records=(Record(data=data, source_uri=str(response.url)),),
            next_cursor=None,
            has_more=False,
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        absolute_url: bool = False,
    ) -> Any:
        if self._client is None:
            raise ConnectError("GitRepoDriver is not connected")
        try:
            response = self._client.request(method, url, params=params)
        except Exception as exc:
            raise ConnectError(str(exc)) from exc

        status = response.status_code
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimited(
                f"rate limited: {status}",
                retry_after=float(retry_after) if retry_after else None,
            )
        if status in (401, 403):
            raise AuthError(f"auth failed: {status}")
        if status == 404:
            raise NotFoundError(f"not found: {url}")
        if status >= 500:
            raise TransientError(f"upstream {status}: {response.text[:200]}")
        if status >= 400:
            raise PermanentError(f"http {status}: {response.text[:200]}")
        return response
