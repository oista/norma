"""Per-turn counters collected during orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TurnMetrics:
    fallback_tool_parse_count: int = 0
    validation_recovery_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def record_fallback_parse(self) -> None:
        self.fallback_tool_parse_count += 1

    def record_validation_recovery(self) -> None:
        self.validation_recovery_count += 1

    def record_llm_usage(self, usage: object | None) -> None:
        if usage is None:
            return
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        total = int(getattr(usage, "total_tokens", 0) or 0)
        if total == 0 and (prompt or completion):
            total = prompt + completion
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += total
