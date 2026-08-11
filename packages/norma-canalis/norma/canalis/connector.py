"""ConnectorSpec and Connector Protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from norma.canalis.capability import validate_capability
from norma.canalis.secrets import SecretRef


@dataclass(frozen=True)
class ConnectorSpec:
    """Declarative connector identity and connection parameters."""

    id: str
    capability: str
    endpoint: str = ""
    options: dict[str, Any] = field(default_factory=dict)
    secrets: tuple[SecretRef, ...] = ()

    def __post_init__(self) -> None:
        validate_capability(self.capability)
        if not self.id:
            raise ValueError("ConnectorSpec.id must be non-empty")


@runtime_checkable
class Connector(Protocol):
    """Synchronous connector lifecycle (async is a non-goal for v0.1)."""

    def connect(self) -> None:
        """Establish the underlying connection / client."""
        ...

    def close(self) -> None:
        """Release resources."""
        ...

    def capabilities(self) -> frozenset[str]:
        """Capability slugs this connector instance supports."""
        ...

    def health(self) -> bool:
        """True if the connector is usable."""
        ...

    def __enter__(self) -> Connector:
        ...

    def __exit__(self, *args: object) -> None:
        ...
