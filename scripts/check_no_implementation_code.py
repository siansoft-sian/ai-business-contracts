#!/usr/bin/env python3
"""Fail if implementation code owned by another repository appears here.

``ai-business-contracts`` is the shared language of the platform: contract
source, governance, validation tooling, and tests. It is never the home of
runtime implementation. ``PROMPT.md`` section G and ``HARNESS.md`` section 3.1
list what that excludes -- FastAPI routers, database drivers and migrations,
auth/JWT verification, Casbin policies, LangGraph nodes, channel adapters,
React application code, deployment/IaC resources, and runtime observability
SDK initialisation.

The check runs in two families, deliberately scoped differently:

1. **Content patterns** are matched only on the release surface
   (``_scope.CONTRACT_BEARING_PATHS``). Prose *naming* a prohibited construct
   is legitimate in governance and evidence -- indeed the governing documents
   must name what they forbid -- so a root-wide content scan would flag the
   documents mandating this scan. See ``_scope.py``.

2. **File families** are matched repository-wide, because a ``.sql`` or
   ``.tf`` file has no legitimate home anywhere in a contracts repository
   regardless of directory. Generated and ephemeral trees (``.git``,
   ``.venv``, caches, ``dist``) are not traversed: they are build output, not
   source. Release-artifact contents are validated separately by EP-05
   (``M0-CON-037``).

``.py`` is handled by family 2 but scoped to the release surface: validation
scripts and tests are explicitly permitted by ``PROMPT.md`` section G, so
Python is legal in ``scripts/`` and ``tests/`` and illegal in ``contracts/``,
``catalog/``, ``compatibility/``, and ``templates/``.

Exit codes:
    0 - no prohibited implementation found
    1 - at least one prohibited implementation found (blocking)
"""

from __future__ import annotations

import fnmatch
import re
import sys
from pathlib import Path

from _scope import (
    CONTRACT_BEARING_PATHS,
    Violation,
    build_parser,
    is_in_scope,
    iter_scoped_files,
    read_text,
    relative_to,
    report,
)

CHECK_NAME = "check_no_implementation_code"

#: Directories never traversed by the repository-wide file-family scan.
#: These hold build output, dependencies, or VCS internals -- not source.
_NON_SOURCE_DIRS = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist"}
)

#: (label, glob, owning repository, why prohibited) matched repository-wide.
FORBIDDEN_FILE_FAMILIES: tuple[tuple[str, str, str, str], ...] = (
    ("sql-source", "*.sql", "ai-business-database", "SQL/DDL or migration source"),
    ("sqitch-plan", "sqitch.plan", "ai-business-database", "Sqitch migration plan"),
    ("sqitch-conf", "sqitch.conf", "ai-business-database", "Sqitch configuration"),
    ("pgbouncer-config", "pgbouncer.ini", "ai-business-database", "PgBouncer configuration"),
    ("pgbouncer-userlist", "userlist.txt", "ai-business-database", "PgBouncer credential list"),
    ("terraform", "*.tf", "ai-business-infrastructure", "Terraform IaC resource"),
    ("terraform-vars", "*.tfvars", "ai-business-infrastructure", "Terraform variables"),
    ("container-build", "Dockerfile", "ai-business-infrastructure", "container build definition"),
    ("compose", "docker-compose.y*ml", "ai-business-infrastructure", "deployment composition"),
    ("react-component", "*.tsx", "ai-business-admin-web", "React component source"),
    ("react-component-js", "*.jsx", "ai-business-admin-web", "React component source"),
)

#: (label, glob, owning repository, why prohibited) matched on the release
#: surface only. Python is permitted in ``scripts/`` and ``tests/``.
FORBIDDEN_IN_SCOPE_FILES: tuple[tuple[str, str, str, str], ...] = (
    (
        "python-on-release-surface",
        "*.py",
        "ai-business-contracts",
        "executable code on the release surface (validation tooling belongs in scripts/)",
    ),
)

#: (label, compiled pattern, owning repository) matched on the release surface.
FORBIDDEN_CONTENT: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "fastapi-runtime",
        re.compile(r"\b(fastapi|APIRouter|uvicorn|starlette)\b|@app\.(get|post|put|patch|delete)\b"),
        "ai-business-api",
    ),
    (
        "database-driver",
        re.compile(r"\b(asyncpg|psycopg2?|sqlalchemy|alembic|pgbouncer|sqitch)\b", re.IGNORECASE),
        "ai-business-database",
    ),
    (
        "sql-ddl",
        re.compile(
            r"\bcreate\s+(or\s+replace\s+)?(table|function|procedure|index|schema|trigger)\b"
            r"|\balter\s+table\b|\bdrop\s+table\b",
            re.IGNORECASE,
        ),
        "ai-business-database",
    ),
    (
        "auth-implementation",
        re.compile(
            r"\b(casbin|pyjwt|jwks|oauth2|passlib|bcrypt|argon2)\b|\bjwt\.(decode|encode)\b",
            re.IGNORECASE,
        ),
        "ai-business-auth",
    ),
    (
        "agent-runtime",
        re.compile(r"\b(langgraph|langchain|StateGraph|CompiledGraph)\b", re.IGNORECASE),
        "ai-business-agent-runtime",
    ),
    (
        "channel-adapter",
        re.compile(r"\b(twilio|slack_sdk|whatsapp_business|X-Hub-Signature)\b", re.IGNORECASE),
        "ai-business-channel-gateway",
    ),
    (
        "frontend-runtime",
        re.compile(r"\b(ReactDOM|useState|useEffect)\b|from\s+['\"]react['\"]"),
        "ai-business-admin-web",
    ),
    (
        "deployment-iac",
        re.compile(r"\b(terraform|kubectl|helm\s+chart)\b|\bapiVersion:\s*apps/", re.IGNORECASE),
        "ai-business-infrastructure",
    ),
    (
        "observability-sdk-init",
        re.compile(r"\b(TracerProvider|set_tracer_provider|OTLPSpanExporter|instrument_app)\b"),
        "each runtime service",
    ),
)


def _iter_source_files(root: Path) -> list[Path]:
    """Yield every source file under ``root``, skipping non-source trees."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in _NON_SOURCE_DIRS for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def _scan_file_families(root: Path) -> list[Violation]:
    """Match prohibited file families repository-wide and in-scope-only."""
    violations: list[Violation] = []
    for path in _iter_source_files(root):
        for label, glob, owner, detail in FORBIDDEN_FILE_FAMILIES:
            if fnmatch.fnmatch(path.name, glob):
                violations.append(
                    Violation(
                        path=relative_to(path, root),
                        line=0,
                        pattern=label,
                        detail=f"{detail}; owned by {owner}",
                    )
                )
        if is_in_scope(path, root):
            for label, glob, owner, detail in FORBIDDEN_IN_SCOPE_FILES:
                if fnmatch.fnmatch(path.name, glob):
                    violations.append(
                        Violation(
                            path=relative_to(path, root),
                            line=0,
                            pattern=label,
                            detail=f"{detail}; owned by {owner}",
                        )
                    )
    return violations


def _scan_content(root: Path) -> list[Violation]:
    """Match prohibited implementation patterns on the release surface."""
    violations: list[Violation] = []
    for path in iter_scoped_files(root):
        content = read_text(path)
        if content is None:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            for label, pattern, owner in FORBIDDEN_CONTENT:
                match = pattern.search(line)
                if match:
                    violations.append(
                        Violation(
                            path=relative_to(path, root),
                            line=lineno,
                            pattern=label,
                            detail=f"implementation owned by {owner} (matched {match.group(0)!r})",
                        )
                    )
                    break
    return violations


def scan(root: Path) -> list[Violation]:
    """Return every prohibited implementation artifact under ``root``."""
    return _scan_file_families(root) + _scan_content(root)


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations = scan(args.root)
    if not args.as_json and not violations:
        print(
            f"{CHECK_NAME}: PASS - no prohibited implementation "
            f"(file families repository-wide; content in {', '.join(CONTRACT_BEARING_PATHS)})"
        )
        return 0
    return report(CHECK_NAME, args.root, violations, args.as_json)


if __name__ == "__main__":
    sys.exit(main())
