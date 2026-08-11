"""Tool execution protocols — products implement these."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ExecutionContext:
    """Generic per-call context (no Oracle/Neo4j types)."""

    session_id: str
    step: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ToolExecutor(Protocol):
    """Product-owned tool dispatch."""

    def dispatch(self, name: str, args_model: Any, ctx: ExecutionContext) -> str:
        """Return JSON tool result string."""
        ...

    def recover_args(
        self,
        name: str,
        raw: dict,
        content_buf: str,
        messages: list[dict],
        history: list[dict],
    ) -> dict | None:
        """Optional arg recovery; return None if not applicable."""
        ...


@runtime_checkable
class PostProcessor(Protocol):
    """Optional post-tool hook (enrich empty results, hints, skill activate)."""

    def after_tool(
        self,
        name: str,
        result_json: str,
        ctx: ExecutionContext,
    ) -> str:
        ...
