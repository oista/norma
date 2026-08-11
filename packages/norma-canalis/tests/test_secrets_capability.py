"""Tests for secrets and capability validation."""

from __future__ import annotations

import pytest

from norma.canalis.capability import HTTP_REST, is_known, validate_capability
from norma.canalis.errors import AuthError, PermanentError
from norma.canalis.secrets import (
    ChainResolver,
    EnvSecretResolver,
    MappingSecretResolver,
    Secret,
    SecretRef,
)


def test_secret_repr_redacted() -> None:
    s = Secret("super-secret", name="token")
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s)
    assert s.get() == "super-secret"


def test_env_secret_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "abc")
    resolver = EnvSecretResolver()
    secret = resolver.resolve(SecretRef(name="token", env="MY_TOKEN"))
    assert secret.get() == "abc"


def test_env_secret_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_X", raising=False)
    with pytest.raises(AuthError):
        EnvSecretResolver().resolve(SecretRef(name="x", env="MISSING_X"))


def test_mapping_and_chain() -> None:
    a = MappingSecretResolver({"a": "1"})
    b = MappingSecretResolver({"b": "2"})
    chain = ChainResolver(a, b)
    assert chain.resolve(SecretRef(name="b")).get() == "2"
    with pytest.raises(AuthError):
        chain.resolve(SecretRef(name="c"))


def test_validate_capability() -> None:
    assert validate_capability(HTTP_REST) == HTTP_REST
    assert is_known("sql.catalog")
    assert validate_capability("custom.thing") == "custom.thing"
    assert not is_known("custom.thing")
    with pytest.raises(PermanentError):
        validate_capability("Bad.Slug")
    with pytest.raises(PermanentError):
        validate_capability("nosub")
