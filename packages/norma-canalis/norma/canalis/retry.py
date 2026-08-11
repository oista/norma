"""Retry policy with injectable sleep/rng for deterministic tests."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from norma.canalis.errors import RateLimited, TransientError

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff: float = 0.1
    multiplier: float = 2.0
    max_backoff: float = 5.0
    jitter: float = 0.1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_backoff < 0:
            raise ValueError("initial_backoff must be >= 0")
        if self.multiplier < 1.0:
            raise ValueError("multiplier must be >= 1.0")
        if self.max_backoff < 0:
            raise ValueError("max_backoff must be >= 0")
        if self.jitter < 0:
            raise ValueError("jitter must be >= 0")


def _backoff_seconds(
    policy: RetryPolicy,
    attempt: int,
    *,
    retry_after: float | None,
    rng: random.Random,
) -> float:
    if retry_after is not None:
        return min(float(retry_after), policy.max_backoff)
    base = policy.initial_backoff * (policy.multiplier ** (attempt - 1))
    capped = min(base, policy.max_backoff)
    if policy.jitter <= 0:
        return capped
    return max(0.0, capped + rng.uniform(-policy.jitter, policy.jitter))


def retry_call(
    fn: Callable[[], T],
    *,
    policy: RetryPolicy | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> T:
    """Call *fn*, retrying TransientError / RateLimited per *policy*."""
    policy = policy or RetryPolicy()
    rng = rng or random.Random()
    last_exc: BaseException | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except RateLimited as exc:
            last_exc = exc
            if attempt >= policy.max_attempts:
                raise
            delay = _backoff_seconds(
                policy, attempt, retry_after=exc.retry_after, rng=rng
            )
            sleep(delay)
        except TransientError as exc:
            last_exc = exc
            if attempt >= policy.max_attempts:
                raise
            delay = _backoff_seconds(policy, attempt, retry_after=None, rng=rng)
            sleep(delay)
    assert last_exc is not None
    raise last_exc
