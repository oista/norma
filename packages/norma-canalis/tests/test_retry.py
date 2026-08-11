"""Tests for retry_call and RetryPolicy."""

from __future__ import annotations

import random

import pytest

from norma.canalis.errors import PermanentError, RateLimited, TransientError
from norma.canalis.retry import RetryPolicy, retry_call


def test_retry_succeeds_after_transient() -> None:
    sleeps: list[float] = []
    state = {"n": 0}

    def flaky() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise TransientError("boom")
        return "ok"

    result = retry_call(
        flaky,
        policy=RetryPolicy(max_attempts=3, initial_backoff=0.1, jitter=0),
        sleep=sleeps.append,
        rng=random.Random(0),
    )
    assert result == "ok"
    assert len(sleeps) == 2
    assert sleeps[0] == pytest.approx(0.1)
    assert sleeps[1] == pytest.approx(0.2)


def test_retry_respects_rate_limited_retry_after() -> None:
    sleeps: list[float] = []
    state = {"n": 0}

    def flaky() -> int:
        state["n"] += 1
        if state["n"] == 1:
            raise RateLimited("slow down", retry_after=1.5)
        return 42

    assert (
        retry_call(
            flaky,
            policy=RetryPolicy(max_attempts=3, max_backoff=10.0, jitter=0),
            sleep=sleeps.append,
            rng=random.Random(0),
        )
        == 42
    )
    assert sleeps == [1.5]


def test_retry_does_not_retry_permanent() -> None:
    calls = {"n": 0}

    def boom() -> None:
        calls["n"] += 1
        raise PermanentError("nope")

    with pytest.raises(PermanentError):
        retry_call(boom, policy=RetryPolicy(max_attempts=5), sleep=lambda _: None)
    assert calls["n"] == 1


def test_retry_exhausted_raises_last() -> None:
    with pytest.raises(TransientError, match="always"):
        retry_call(
            lambda: (_ for _ in ()).throw(TransientError("always")),
            policy=RetryPolicy(max_attempts=2, jitter=0),
            sleep=lambda _: None,
            rng=random.Random(0),
        )
