"""Session/profile-scoped agent runtime options (ADR-0020).

Precedence: explicit session override → user profile → env defaults.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_TOOL_CALLS_HARD_CAP = 50
MAX_TOKENS_ALLOWED = (2048, 4096, 8192, 16384, 32768)
CompactMode = Literal["standard", "aggressive"]
PresetName = Literal["economy", "balanced", "quality"]

TOOLTIP_TEXTS: dict[str, str] = {
    "max_tool_calls": (
        "Потолок шагов ReAct за один ответ. Меньше — дешевле и быстрее, "
        "но сложные расследования могут обрываться."
    ),
    "max_tokens": (
        "Лимит выходных токенов одного LLM-вызова. Без лимита провайдер "
        "резервирует до 65536 — отсюда ошибки 402 при нехватке кредитов."
    ),
    "skill_routing": (
        "Вкл: в prompt только skills по intent (в 2–3× меньше на узких вопросах). "
        "Выкл: все skills сразу — стабильнее, но дороже."
    ),
    "stop_after_nudge": (
        "После подсказки «Достаточно шагов…» цикл завершается сразу. "
        "Главный предохранитель от runaway на 50 шагов."
    ),
    "preflight": (
        "До ответа подтягивает KG/LDM по ключевым словам: небольшой preamble, "
        "но часто экономит лишние вызовы tools."
    ),
    "episode_memory": (
        "Подмешивает краткие итоги похожих прошлых диалогов (~1.5 KB) — лучше follow-up."
    ),
    "fact_memory": (
        "Курированные доменные факты (staging triples) в preflight `[FACTS]` "
        "и persist `[FACT]` после turn. Не episodic memory и не дубль Neo4j."
    ),
    "compact_mode": (
        "Сжатие старых результатов tools. Агрессивно — ниже пороги и compact "
        "для объёмных schema/column tools, которые в стандарте исключены."
    ),
    "nudge_after_step": (
        "На каком шаге просить модель закончить (≤ макс. tool calls)."
    ),
    "max_history_messages": (
        "Сколько сообщений user/assistant держать в истории сессии. "
        "Меньше — дешевле, хуже длинный контекст."
    ),
    "no_think": (
        "Добавляет /no_think в CONFIG: у Qwen/DeepSeek-подобных моделей "
        "отключает extended thinking — быстрее шаги tool, слабее глубина рассуждения."
    ),
}


class AgentRuntimeOptions(BaseModel):
    """Effective runtime knobs for quality ↔ token cost."""

    model_config = ConfigDict(extra="ignore")

    max_tool_calls: int = Field(default=50, ge=1, le=MAX_TOOL_CALLS_HARD_CAP)
    max_tokens: int = Field(default=8192)
    skill_routing: bool = False
    stop_after_nudge: bool = False
    preflight: bool = True
    episode_memory: bool = True
    fact_memory: bool = True
    compact_mode: CompactMode = "standard"
    nudge_after_step: int = Field(default=15, ge=1, le=MAX_TOOL_CALLS_HARD_CAP)
    max_history_messages: int = Field(default=40, ge=4, le=200)
    no_think: bool = False
    # Server-only: 0 = disabled
    turn_prompt_token_budget: int = Field(default=0, ge=0)

    @field_validator("max_tokens")
    @classmethod
    def _whitelist_max_tokens(cls, v: int) -> int:
        if int(v) not in MAX_TOKENS_ALLOWED:
            raise ValueError(f"max_tokens must be one of {MAX_TOKENS_ALLOWED}")
        return int(v)

    @model_validator(mode="after")
    def _clamp_nudge(self) -> AgentRuntimeOptions:
        if self.nudge_after_step > self.max_tool_calls:
            self.nudge_after_step = self.max_tool_calls
        return self

    def compact_threshold_chars(self) -> int:
        if self.compact_mode == "aggressive":
            return 2048
        return 4096

    def context_budget_chars(self) -> int:
        if self.compact_mode == "aggressive":
            return 16000
        return 32000

    def compact_ldm_columns(self) -> bool:
        return self.compact_mode == "aggressive"

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "max_tool_calls": self.max_tool_calls,
            "max_tokens": self.max_tokens,
            "skill_routing": self.skill_routing,
            "stop_after_nudge": self.stop_after_nudge,
            "preflight": self.preflight,
            "episode_memory": self.episode_memory,
            "fact_memory": self.fact_memory,
            "compact_mode": self.compact_mode,
            "nudge_after_step": self.nudge_after_step,
            "max_history_messages": self.max_history_messages,
            "no_think": self.no_think,
            "turn_prompt_token_budget": self.turn_prompt_token_budget,
        }


def _env_bool(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


def defaults_from_env() -> AgentRuntimeOptions:
    """Factory defaults from environment (ADR-0020)."""
    max_tokens_raw = os.getenv("AGENT_MAX_TOKENS", "8192")
    try:
        max_tokens = int(max_tokens_raw)
    except ValueError:
        max_tokens = 8192
    if max_tokens not in MAX_TOKENS_ALLOWED:
        max_tokens = 8192

    max_steps_raw = os.getenv("AGENT_MAX_TOOL_CALLS", "50")
    try:
        max_tool_calls = min(MAX_TOOL_CALLS_HARD_CAP, max(1, int(max_steps_raw)))
    except ValueError:
        max_tool_calls = 50

    nudge_raw = os.getenv("AGENT_NUDGE_AFTER_STEP", "15")
    try:
        nudge_after_step = max(1, int(nudge_raw))
    except ValueError:
        nudge_after_step = 15

    hist_raw = os.getenv("MAX_HISTORY_MESSAGES", "40")
    try:
        max_history = max(4, int(hist_raw))
    except ValueError:
        max_history = 40

    budget_raw = os.getenv("AGENT_TURN_PROMPT_TOKEN_BUDGET", "0")
    try:
        budget = max(0, int(budget_raw))
    except ValueError:
        budget = 0

    compact = (os.getenv("AGENT_COMPACT_MODE", "standard") or "standard").strip().lower()
    if compact not in ("standard", "aggressive"):
        compact = "standard"

    return AgentRuntimeOptions(
        max_tool_calls=max_tool_calls,
        max_tokens=max_tokens,
        skill_routing=_env_bool("SKILL_ROUTING_ENABLED", "false"),
        stop_after_nudge=_env_bool("AGENT_STOP_AFTER_NUDGE", "false"),
        preflight=_env_bool("PREFLIGHT_ENABLED", "true"),
        episode_memory=_env_bool("EPISODE_MEMORY_ENABLED", "true"),
        fact_memory=_env_bool("FACT_MEMORY_ENABLED", "true"),
        compact_mode=compact,  # type: ignore[arg-type]
        nudge_after_step=min(nudge_after_step, max_tool_calls),
        max_history_messages=max_history,
        no_think=_env_bool("AGENT_NO_THINK", "false"),
        turn_prompt_token_budget=budget,
    )


PRESETS: dict[PresetName, dict[str, Any]] = {
    "economy": {
        "max_tool_calls": 12,
        "max_tokens": 4096,
        "skill_routing": True,
        "stop_after_nudge": True,
        "preflight": True,
        "episode_memory": False,
        "fact_memory": False,
        "compact_mode": "aggressive",
        "nudge_after_step": 8,
        "max_history_messages": 20,
        "no_think": True,
    },
    "balanced": {
        "max_tool_calls": 50,
        "max_tokens": 8192,
        "skill_routing": False,
        "stop_after_nudge": False,
        "preflight": True,
        "episode_memory": True,
        "fact_memory": True,
        "compact_mode": "standard",
        "nudge_after_step": 15,
        "max_history_messages": 40,
        "no_think": False,
    },
    "quality": {
        "max_tool_calls": 50,
        "max_tokens": 16384,
        "skill_routing": False,
        "stop_after_nudge": False,
        "preflight": True,
        "episode_memory": True,
        "fact_memory": True,
        "compact_mode": "standard",
        "nudge_after_step": 20,
        "max_history_messages": 60,
        "no_think": False,
    },
}


def apply_preset(name: PresetName) -> AgentRuntimeOptions:
    base = defaults_from_env().model_dump()
    base.update(PRESETS[name])
    return AgentRuntimeOptions.model_validate(base)


def merge_options(
    *,
    profile_options: dict[str, Any] | AgentRuntimeOptions | None = None,
    session_options: dict[str, Any] | AgentRuntimeOptions | None = None,
) -> AgentRuntimeOptions:
    """env defaults ← profile ← session (session wins)."""
    data = defaults_from_env().model_dump()
    if profile_options is not None:
        if isinstance(profile_options, AgentRuntimeOptions):
            data.update(profile_options.model_dump(exclude_unset=False))
        else:
            data.update({k: v for k, v in profile_options.items() if v is not None})
    if session_options is not None:
        if isinstance(session_options, AgentRuntimeOptions):
            data.update(session_options.model_dump(exclude_unset=False))
        else:
            data.update({k: v for k, v in session_options.items() if v is not None})
    return AgentRuntimeOptions.model_validate(data)


def effective_options_for_session(session: Any | None) -> AgentRuntimeOptions:
    """Resolve options for a SessionState (or None → env defaults)."""
    if session is None:
        return defaults_from_env()
    cached = getattr(session, "agent_options", None)
    if isinstance(cached, AgentRuntimeOptions):
        return cached
    if isinstance(cached, dict) and cached:
        return AgentRuntimeOptions.model_validate(cached)

    profile_opts = None
    user_id = getattr(session, "user_id", None)
    if user_id:
        try:
            from users.store import get_user_store

            profile = get_user_store().get(user_id)
            if profile is not None:
                raw = getattr(profile, "agent_options", None) or {}
                if raw:
                    profile_opts = raw
        except Exception:
            profile_opts = None
    return merge_options(profile_options=profile_opts, session_options=None)
