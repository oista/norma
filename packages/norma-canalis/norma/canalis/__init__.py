"""norma.canalis — connector contract for external systems.

Library, not a service. Products import and call drivers in-process.
Async is a non-goal for v0.1.
"""

from __future__ import annotations

from norma.canalis.audit import AuditEvent, AuditHook, CollectingAuditHook, NullAuditHook
from norma.canalis.capability import (
    GIT_REPO,
    GRAPH_SPARQL,
    HTTP_REST,
    KNOWN_CAPABILITIES,
    SQL_CATALOG,
    TRACKER_JIRA,
    is_known,
    validate_capability,
)
from norma.canalis.connector import Connector, ConnectorSpec
from norma.canalis.errors import (
    AuthError,
    CanalisError,
    ConnectError,
    DriverUnavailable,
    NotFoundError,
    PermanentError,
    RateLimited,
    TransientError,
)
from norma.canalis.paging import iterate
from norma.canalis.primitives import BlobRequest, DocumentRequest, BlobSource, DocumentSource, RowSource, SqlQuery
from norma.canalis.records import Page, PageRequest, Record
from norma.canalis.registry import clear_registry, open_connector, register_driver, unregister_driver
from norma.canalis.retry import RetryPolicy, retry_call
from norma.canalis.secrets import (
    ChainResolver,
    EnvSecretResolver,
    MappingSecretResolver,
    Secret,
    SecretRef,
    SecretResolver,
)

__all__ = [
    "AuditEvent",
    "AuditHook",
    "AuthError",
    "BlobRequest",
    "BlobSource",
    "CanalisError",
    "ChainResolver",
    "CollectingAuditHook",
    "ConnectError",
    "Connector",
    "ConnectorSpec",
    "DocumentRequest",
    "DocumentSource",
    "DriverUnavailable",
    "EnvSecretResolver",
    "GIT_REPO",
    "GRAPH_SPARQL",
    "HTTP_REST",
    "KNOWN_CAPABILITIES",
    "MappingSecretResolver",
    "NotFoundError",
    "NullAuditHook",
    "Page",
    "PageRequest",
    "PermanentError",
    "RateLimited",
    "Record",
    "RetryPolicy",
    "RowSource",
    "SQL_CATALOG",
    "Secret",
    "SecretRef",
    "SecretResolver",
    "SqlQuery",
    "TRACKER_JIRA",
    "TransientError",
    "clear_registry",
    "is_known",
    "iterate",
    "open_connector",
    "register_driver",
    "retry_call",
    "unregister_driver",
    "validate_capability",
]
