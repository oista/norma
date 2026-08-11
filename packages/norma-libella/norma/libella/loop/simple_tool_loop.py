"""Minimal read-only tool loop for platform assistants.

Uses ToolExecutor protocol — no product-domain imports.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from norma.libella.contract.record import StopReason, TurnRecord
from norma.libella.tools.protocol import ExecutionContext, ToolExecutor

CompleteFn = Callable[..., Awaitable[Any]]


async def stream_tool_loop(
    *,
    executor: ToolExecutor,
    complete_with_tools: CompleteFn,
    messages: list[dict],
    openai_tools: list[dict],
    session_id: str,
    max_iterations: int = 8,
    on_delta: Callable[[str], None] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield event dicts: {type: delta|tool|done|error, ...}.

    `complete_with_tools(messages, tools) -> object` with `.tool_calls` and `.content`
    (OpenAI-like message). Tool call: `.function.name`, `.function.arguments`.
    """
    record = TurnRecord()
    for step in range(1, max_iterations + 1):
        msg = await complete_with_tools(messages=messages, tools=openai_tools)
        tool_calls = getattr(msg, "tool_calls", None) or []
        content = getattr(msg, "content", None) or ""

        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": [
                        {
                            "id": getattr(tc, "id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for i, tc in enumerate(tool_calls)
                    ],
                }
            )
            for tc in tool_calls:
                name = tc.function.name
                try:
                    raw_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    raw_args = {}
                # Lightweight namespace object for executor
                args_model = type("Args", (), raw_args)()
                ctx = ExecutionContext(session_id=session_id, step=step)
                result = executor.dispatch(name, args_model, ctx)
                yield {"type": "tool", "name": name, "result": result, "step": step}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": getattr(tc, "id", name),
                        "content": result,
                    }
                )
            continue

        if content:
            if on_delta:
                on_delta(content)
            record.mark_finalize(StopReason.NATURAL)
            yield {"type": "delta", "text": content}
            yield {"type": "done", "loop_plan": record.to_loop_plan()}
            return

        yield {"type": "error", "message": "empty LLM response"}
        return

    record.mark_finalize(StopReason.MAX_STEPS)
    yield {"type": "error", "message": f"max tool iterations ({max_iterations})"}
    yield {"type": "done", "loop_plan": record.to_loop_plan()}
