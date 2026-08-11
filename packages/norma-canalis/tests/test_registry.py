"""Tests for driver registry and open_connector."""

from __future__ import annotations

import pytest

from norma.canalis.capability import HTTP_REST
from norma.canalis.connector import ConnectorSpec
from norma.canalis.errors import DriverUnavailable
from norma.canalis.registry import (
    clear_registry,
    open_connector,
    register_driver,
    unregister_driver,
)


class _StubDriver:
    capability = HTTP_REST

    def __init__(self, spec, resolver=None, audit=None, **kwargs) -> None:
        self.spec = spec
        self.connected = False

    def connect(self) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False

    def capabilities(self) -> frozenset[str]:
        return frozenset({HTTP_REST})

    def health(self) -> bool:
        return self.connected

    def __enter__(self) -> _StubDriver:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    clear_registry(rediscover=True)
    yield
    clear_registry(rediscover=True)


def test_register_and_open() -> None:
    register_driver(HTTP_REST, _StubDriver)
    spec = ConnectorSpec(id="s1", capability=HTTP_REST, endpoint="https://x")
    conn = open_connector(spec)
    assert conn.health()
    assert HTTP_REST in conn.capabilities()
    conn.close()
    unregister_driver(HTTP_REST)


def test_unknown_capability_raises_driver_unavailable() -> None:
    clear_registry(rediscover=True)
    # Ensure no factory for a known-but-unregistered custom capability
    spec = ConnectorSpec(id="s2", capability="custom.thing")
    with pytest.raises(DriverUnavailable):
        open_connector(spec)
