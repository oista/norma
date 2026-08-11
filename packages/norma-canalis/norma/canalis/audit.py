"""Audit hook contract. RBAC and persistence belong to products."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

Outcome = Literal["ok", "error"]


@dataclass(frozen=True)
class AuditEvent:
    connector_id: str
    capability: str
    operation: str
    target: str = ""
    duration_ms: float = 0.0
    outcome: Outcome = "ok"
    record_count: int = 0
    attempt: int = 1
    error_kind: str | None = None


@runtime_checkable
class AuditHook(Protocol):
    def emit(self, event: AuditEvent) -> None:
        ...


class NullAuditHook:
    """No-op audit sink."""

    def emit(self, event: AuditEvent) -> None:
        return None


class CollectingAuditHook:
    """In-memory collector for tests."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()
