"""Capability slug vocabulary and validation.

Known slugs align with Clavis harvester.toml ``[connector] capability`` values.
Unknown but well-formed slugs are allowed (extensibility without a Norma release).
"""

from __future__ import annotations

import re

from norma.canalis.errors import PermanentError

CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9]*\.[a-z][a-z0-9_]*$")

GIT_REPO = "git.repo"
SQL_CATALOG = "sql.catalog"
HTTP_REST = "http.rest"
TRACKER_JIRA = "tracker.jira"
GRAPH_SPARQL = "graph.sparql"

KNOWN_CAPABILITIES: frozenset[str] = frozenset(
    {
        GIT_REPO,
        SQL_CATALOG,
        HTTP_REST,
        TRACKER_JIRA,
        GRAPH_SPARQL,
    }
)


def validate_capability(slug: str) -> str:
    """Return *slug* if well-formed; raise PermanentError otherwise."""
    if not CAPABILITY_RE.fullmatch(slug):
        raise PermanentError(
            f"invalid capability slug {slug!r}: "
            f"expected pattern {CAPABILITY_RE.pattern}"
        )
    return slug


def is_known(slug: str) -> bool:
    """True if *slug* is in the built-in vocabulary."""
    return slug in KNOWN_CAPABILITIES
