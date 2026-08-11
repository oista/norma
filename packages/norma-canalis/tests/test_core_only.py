"""Core-only: opening http/sql drivers without extras / registration fails cleanly."""

from __future__ import annotations

import pytest

from norma.canalis.capability import HTTP_REST, SQL_CATALOG
from norma.canalis.connector import ConnectorSpec
from norma.canalis.errors import DriverUnavailable
from norma.canalis.registry import clear_registry, open_connector


@pytest.fixture(autouse=True)
def _clean() -> None:
    clear_registry(rediscover=True)
    yield
    clear_registry(rediscover=True)


def test_open_without_driver_raises() -> None:
    # With empty registry and no successful entry-point load of deps,
    # open_connector must raise DriverUnavailable (not ImportError).
    # If extras are installed in this env, entry points may register —
    # then we still verify that *explicit* missing capability fails.
    clear_registry(rediscover=False)
    from norma.canalis import registry as reg

    reg._REGISTRY.clear()
    reg._DISCOVERED = True  # skip rediscovery so factories stay empty
    with pytest.raises(DriverUnavailable):
        open_connector(ConnectorSpec(id="x", capability=HTTP_REST))
    with pytest.raises(DriverUnavailable):
        open_connector(ConnectorSpec(id="y", capability=SQL_CATALOG))
