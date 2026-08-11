"""Configurable discovery / deep / meta tool taxonomy."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolTaxonomy:
    discovery: frozenset[str] = field(default_factory=frozenset)
    deep: frozenset[str] = field(default_factory=frozenset)
    meta: frozenset[str] = field(default_factory=frozenset)

    def is_discovery_only_trace(self, tools_trace: list[dict]) -> bool:
        names = {(t.get("name") or "") for t in tools_trace}
        names -= self.meta
        names.discard("")
        return bool(names) and names <= self.discovery

    def deep_tools_in_trace(self, tools_trace: list[dict]) -> bool:
        return any((t.get("name") or "") in self.deep for t in tools_trace)

    def domain_tools_in_trace(self, tools_trace: list[dict]) -> bool:
        return any((t.get("name") or "") not in self.meta for t in tools_trace)
