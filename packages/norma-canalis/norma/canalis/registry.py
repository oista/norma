"""Driver registry and open_connector factory."""

from __future__ import annotations

from collections.abc import Callable
from importlib import metadata
from typing import Any

from norma.canalis.audit import AuditHook, NullAuditHook
from norma.canalis.capability import validate_capability
from norma.canalis.connector import Connector, ConnectorSpec
from norma.canalis.errors import DriverUnavailable, PermanentError
from norma.canalis.secrets import EnvSecretResolver, SecretResolver

DriverFactory = Callable[..., Connector]

_ENTRY_POINT_GROUP = "norma.canalis.drivers"

# capability -> factory (explicit registration wins over entry points)
_REGISTRY: dict[str, DriverFactory] = {}
_DISCOVERED = False


def register_driver(capability: str, factory: DriverFactory) -> None:
    """Register a driver factory for *capability* (tests / explicit wiring)."""
    validate_capability(capability)
    _REGISTRY[capability] = factory


def unregister_driver(capability: str) -> None:
    _REGISTRY.pop(capability, None)


def clear_registry(*, rediscover: bool = False) -> None:
    """Clear explicit registrations; optionally reset discovery cache."""
    global _DISCOVERED
    _REGISTRY.clear()
    if rediscover:
        _DISCOVERED = False


def _discover_entry_points() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _DISCOVERED = True
    try:
        eps = metadata.entry_points()
    except Exception:
        return
    # Python 3.10+ SelectableGroups vs legacy dict
    selected: Any
    if hasattr(eps, "select"):
        selected = eps.select(group=_ENTRY_POINT_GROUP)
    else:
        selected = eps.get(_ENTRY_POINT_GROUP, [])  # type: ignore[union-attr]
    for ep in selected:
        try:
            factory = ep.load()
        except Exception:
            # Missing optional dependency — skip; open_connector will raise later.
            continue
        # Prefer factory.capability attribute if present; else entry-point name mapping.
        cap = getattr(factory, "capability", None)
        if isinstance(cap, str):
            if cap not in _REGISTRY:
                _REGISTRY[cap] = factory
        else:
            # Map known entry-point names to capabilities
            name_map = {
                "http_rest": "http.rest",
                "sql_catalog": "sql.catalog",
                "git_repo": "git.repo",
            }
            mapped = name_map.get(ep.name)
            if mapped and mapped not in _REGISTRY:
                _REGISTRY[mapped] = factory


def _resolve_factory(capability: str) -> DriverFactory:
    validate_capability(capability)
    if capability in _REGISTRY:
        return _REGISTRY[capability]
    _discover_entry_points()
    if capability in _REGISTRY:
        return _REGISTRY[capability]
    raise DriverUnavailable(
        f"no driver registered for capability {capability!r}; "
        f"install the matching extra (e.g. norma-canalis[http] or [sql]) "
        f"or call register_driver()"
    )


def open_connector(
    spec: ConnectorSpec,
    *,
    resolver: SecretResolver | None = None,
    audit: AuditHook | None = None,
    **kwargs: Any,
) -> Connector:
    """Create and connect a connector for *spec*."""
    factory = _resolve_factory(spec.capability)
    resolver = resolver or EnvSecretResolver()
    audit = audit or NullAuditHook()
    try:
        connector = factory(spec=spec, resolver=resolver, audit=audit, **kwargs)
    except TypeError:
        # Factories may be classes or callables with different signatures
        try:
            connector = factory(spec, resolver, audit, **kwargs)
        except TypeError as exc:
            raise PermanentError(
                f"driver factory for {spec.capability!r} rejected arguments: {exc}"
            ) from exc
    connector.connect()
    return connector
