"""Nudge helpers driven by ToolTaxonomy."""

from __future__ import annotations

from norma.libella.tools.classification import ToolTaxonomy


def maybe_append_final_answer_nudge(
    full_messages: list[dict],
    tools_trace: list[dict],
    taxonomy: ToolTaxonomy,
    *,
    text: str,
    sent: bool,
    step: int = 0,
    nudge_after_step: int = 15,
    has_evidence: bool | None = None,
) -> bool:
    """Pressure the model to synthesize once evidence is on the table.

    ``has_evidence=False`` means every domain tool came back empty: a called-but-empty
    deep tool is not readiness to answer. ``step > nudge_after_step`` stays the escape
    hatch so a long fruitless turn still terminates. ``None`` keeps legacy behaviour.
    """
    if sent or not taxonomy.domain_tools_in_trace(tools_trace):
        return sent
    over_budget = step > nudge_after_step
    if has_evidence is False and not over_budget:
        return sent
    ready = taxonomy.deep_tools_in_trace(tools_trace) or over_budget
    if not ready:
        return sent
    full_messages.append({"role": "user", "content": text})
    return True


def maybe_append_sources_contract_nudge(
    full_messages: list[dict],
    tools_trace: list[dict],
    taxonomy: ToolTaxonomy,
    *,
    text: str,
    sent: bool,
    has_evidence: bool | None = None,
) -> bool:
    """Ask for the [SOURCES] contract once there is something to cite."""
    if sent or not taxonomy.domain_tools_in_trace(tools_trace):
        return sent
    if has_evidence is False:
        return sent
    full_messages.append({"role": "user", "content": text})
    return True
