"""HTTP REST driver (capability http.rest). Requires extras: norma-canalis[http]."""

from __future__ import annotations

import time
from typing import Any
from norma.canalis.audit import AuditEvent, AuditHook, NullAuditHook
from norma.canalis.capability import HTTP_REST
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
from norma.canalis.secrets import SecretResolver


def _require_httpx():  # type: ignore[no-untyped-def]
    try:
        import httpx
    except ImportError as exc:
        raise DriverUnavailable(
            "http.rest driver requires httpx; install norma-canalis[http]"
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


class HttpRestDriver:
    """DocumentSource + BlobSource over HTTP JSON APIs."""

    capability = HTTP_REST

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

    def connect(self) -> None:
        httpx = _require_httpx()
        if self._client is None:
            headers: dict[str, str] = {}
            token_env = self._spec.options.get("token_secret")
            if token_env and self._resolver is not None:
                from norma.canalis.secrets import SecretRef

                secret = self._resolver.resolve(
                    SecretRef(name="token", env=str(token_env))
                )
                header_name = str(self._spec.options.get("token_header", "Authorization"))
                prefix = str(self._spec.options.get("token_prefix", "Bearer "))
                headers[header_name] = f"{prefix}{secret.get()}"
            timeout = float(self._spec.options.get("timeout", 60.0))
            base = self._spec.endpoint.rstrip("/") if self._spec.endpoint else None
            self._client = httpx.Client(base_url=base or "", headers=headers, timeout=timeout)
            self._owns_client = True
        self._connected = True

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
        self._connected = False

    def capabilities(self) -> frozenset[str]:
        return frozenset({HTTP_REST})

    def health(self) -> bool:
        return self._connected and self._client is not None

    def __enter__(self) -> HttpRestDriver:
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_documents(self, request: DocumentRequest, page: PageRequest) -> Page:
        started = time.perf_counter()
        path = request.path or ""
        try:
            records, next_cursor, has_more = self._fetch_page(path, request, page)
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=HTTP_REST,
                    operation="fetch_documents",
                    target=path,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="ok",
                    record_count=len(records),
                )
            )
            return Page(records=tuple(records), next_cursor=next_cursor, has_more=has_more)
        except Exception as exc:
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=HTTP_REST,
                    operation="fetch_documents",
                    target=path,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="error",
                    error_kind=type(exc).__name__,
                )
            )
            raise

    def fetch_blob(self, request: BlobRequest) -> bytes:
        started = time.perf_counter()
        try:
            response = self._request("GET", request.path, params=request.params)
            self._audit.emit(
                AuditEvent(
                    connector_id=self._spec.id,
                    capability=HTTP_REST,
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
                    capability=HTTP_REST,
                    operation="fetch_blob",
                    target=request.path,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    outcome="error",
                    error_kind=type(exc).__name__,
                )
            )
            raise

    def _fetch_page(
        self,
        path: str,
        request: DocumentRequest,
        page: PageRequest,
    ) -> tuple[list[Record], str | None, bool]:
        params = dict(request.params)
        params.setdefault("limit", page.limit)
        url: str | None
        absolute = False
        if page.cursor and (
            page.cursor.startswith("http://")
            or page.cursor.startswith("https://")
            or page.cursor.startswith("/")
        ):
            # Link: rel=next may be absolute or a path on the same host
            url = page.cursor
            absolute = page.cursor.startswith("http")
            params = {}
        elif page.cursor and page.cursor.startswith("offset:"):
            offset = int(page.cursor.split(":", 1)[1])
            params["offset"] = offset
            params["limit"] = page.limit
            url = path
        else:
            url = path
            if page.cursor:
                params["cursor"] = page.cursor

        response = self._request(
            "GET",
            url or path,
            params=params or None,
            headers=request.headers or None,
            absolute_url=absolute,
        )
        payload = response.json()
        items = self._extract_items(payload)
        records = [
            Record(
                data=item if isinstance(item, dict) else {"value": item},
                source_uri=str(response.url),
            )
            for item in items
        ]
        link_next = _parse_link_next(response.headers.get("Link"))
        if link_next:
            return records, link_next, True
        if isinstance(payload, dict) and payload.get("next_cursor"):
            return records, str(payload["next_cursor"]), True
        # offset fallback when full page returned
        if len(records) >= page.limit:
            current_offset = int(params.get("offset", 0)) if isinstance(params, dict) else 0
            next_off = current_offset + page.limit
            return records, f"offset:{next_off}", True
        return records, None, False

    @staticmethod
    def _extract_items(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("items", "data", "results", "values"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            return [payload]
        return [{"value": payload}]

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        absolute_url: bool = False,
    ) -> Any:
        if self._client is None:
            raise ConnectError("HttpRestDriver is not connected")
        try:
            if absolute_url:
                response = self._client.request(method, url, params=params, headers=headers)
            else:
                response = self._client.request(method, url, params=params, headers=headers)
        except Exception as exc:
            # httpx.RequestError and friends
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
