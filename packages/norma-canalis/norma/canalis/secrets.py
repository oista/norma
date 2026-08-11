"""Secret references and resolvers.

Env names are product-owned (see Norma config-contract). Canalis does not
hard-code product prefixes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from norma.canalis.errors import AuthError, PermanentError


@dataclass(frozen=True)
class SecretRef:
    """Named reference to a secret; *env* is the environment variable to read."""

    name: str
    env: str | None = None


class Secret:
    """Opaque secret value; ``repr`` never leaks the payload."""

    __slots__ = ("_value", "_name")

    def __init__(self, value: str, *, name: str = "secret") -> None:
        self._value = value
        self._name = name

    def get(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Secret(name={self._name!r}, value=***)"

    def __str__(self) -> str:
        return "***"


@runtime_checkable
class SecretResolver(Protocol):
    def resolve(self, ref: SecretRef) -> Secret:
        """Resolve *ref* to a Secret; raise AuthError if missing."""
        ...


class EnvSecretResolver:
    """Resolve secrets from process environment variables."""

    def resolve(self, ref: SecretRef) -> Secret:
        env_name = ref.env or ref.name
        value = os.environ.get(env_name)
        if value is None or value == "":
            raise AuthError(f"secret {ref.name!r}: env {env_name!r} is unset")
        return Secret(value, name=ref.name)


class MappingSecretResolver:
    """Resolve secrets from an in-memory mapping (tests / injection)."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = dict(values)

    def resolve(self, ref: SecretRef) -> Secret:
        key = ref.env or ref.name
        if key not in self._values and ref.name not in self._values:
            raise AuthError(f"secret {ref.name!r}: key {key!r} missing in mapping")
        value = self._values.get(key, self._values.get(ref.name, ""))
        if value == "":
            raise AuthError(f"secret {ref.name!r}: empty value")
        return Secret(value, name=ref.name)


class ChainResolver:
    """Try resolvers in order; first success wins."""

    def __init__(self, *resolvers: SecretResolver) -> None:
        if not resolvers:
            raise PermanentError("ChainResolver requires at least one resolver")
        self._resolvers = resolvers

    def resolve(self, ref: SecretRef) -> Secret:
        errors: list[str] = []
        for resolver in self._resolvers:
            try:
                return resolver.resolve(ref)
            except AuthError as exc:
                errors.append(str(exc))
        raise AuthError(
            "secret {!r}: all resolvers failed ({})".format(
                ref.name, "; ".join(errors)
            )
        )
