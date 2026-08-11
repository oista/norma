"""TurnRecord — ordered event tape of server-side interventions in one turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

Target = Literal[
    "system_prompt",
    "messages",
    "tools",
    "loop_control",
    "final_content",
]


class StopReason(str, Enum):
    """Canonical reasons a turn finalizes (INV-LOOP-01)."""

    NATURAL = "natural"
    IDENTICAL_LOOP = "identical_loop"
    STOP_AFTER_NUDGE = "stop_after_nudge"
    TOKEN_BUDGET = "token_budget"
    MAX_STEPS = "max_steps"
    ABORT = "abort"
    BLOCKED = "blocked"


@dataclass
class InterventionEvent:
    kind: str
    mechanism_id: str
    reason: str
    target: Target
    step: int = 0
    before_len: int | None = None
    after_len: int | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind,
            "id": self.mechanism_id,
            "reason": self.reason,
            "target": self.target,
            "step": self.step,
        }
        if self.before_len is not None:
            d["before_len"] = self.before_len
        if self.after_len is not None:
            d["after_len"] = self.after_len
        if self.detail:
            d["detail"] = self.detail
        return d


@dataclass
class TurnRecord:
    """Ordered interventions for one agent turn (EXPLAIN PLAN for the loop)."""

    events: list[InterventionEvent] = field(default_factory=list)
    stop_reason: StopReason | None = None
    finalize_count: int = 0
    repaired: bool = False
    violations: list[str] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)
    # Snapshot fields used by invariant predicates
    final_content: str = ""
    display_content: str = ""
    tools_trace: list[dict] = field(default_factory=list)
    system_prompt: str = ""
    intent_label: str | None = None
    forced_finalize: bool = False
    finalize_forcing_nudges: int = 0
    # Anti-surrender axis: evidence state and strategy ladder usage
    evidence_empty: bool = False
    unexplored_strategies: list[str] = field(default_factory=list)
    strategies_fired: list[str] = field(default_factory=list)
    strategy_outcome: dict[str, str] = field(default_factory=dict)

    def record(
        self,
        *,
        kind: str,
        mechanism_id: str,
        reason: str,
        target: Target,
        step: int = 0,
        before_len: int | None = None,
        after_len: int | None = None,
        detail: dict[str, Any] | None = None,
    ) -> InterventionEvent:
        ev = InterventionEvent(
            kind=kind,
            mechanism_id=mechanism_id,
            reason=reason,
            target=target,
            step=step,
            before_len=before_len,
            after_len=after_len,
            detail=detail or {},
        )
        self.events.append(ev)
        return ev

    def mark_finalize(self, reason: StopReason) -> None:
        self.finalize_count += 1
        self.stop_reason = reason

    def to_loop_plan(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "finalize_count": self.finalize_count,
            "repaired": self.repaired,
            "violations": list(self.violations),
            "repairs": list(self.repairs),
            "quality_flags": list(self.quality_flags),
            "forced_finalize": self.forced_finalize,
            "finalize_forcing_nudges": self.finalize_forcing_nudges,
            "evidence_empty": self.evidence_empty,
            "unexplored_strategies": list(self.unexplored_strategies),
            "strategies_fired": list(self.strategies_fired),
            "strategy_outcome": dict(self.strategy_outcome),
        }
