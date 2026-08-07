#!/usr/bin/env python3
"""Fail if a prohibited multi-tenant construct appears on the release surface.

The platform is **not multi-tenant**. ``PROMPT.md`` forbids tenant
identifiers, tenant request headers, tenant context objects, tenant-scoped
authorization, tenant routing, tenant-scoped persistence, tenant-scoped
rate-limit or idempotency keys, and tenant fields in logs, traces, metrics,
errors, events, or examples.

Scope is the release surface only -- see ``_scope.py`` for why that boundary
is drawn positively rather than as a root-wide scan plus an ignore-list.

Exit codes:
    0 - no prohibited construct found
    1 - at least one prohibited construct found (blocking)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _scope import Violation, build_parser, iter_scoped_files, read_text, relative_to, report

CHECK_NAME = "check_no_multitenancy"

#: Each entry is (label, compiled pattern, why it is prohibited).
#:
#: Patterns are deliberately broad -- a contract has no legitimate reason to
#: contain the word "tenant" at all, so matching the bare stem is correct and
#: keeps the gate simple to reason about.
#:
#: **Order matters.** Only the first match on a line is reported, so entries
#: run most-specific first. Every ordering catches the same violations and
#: produces the same exit code; the order only decides how precisely the
#: failure is labelled, and "tenant-header" tells a contract author more than
#: the catch-all "tenant-identifier" would.
PROHIBITED_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "tenant-header",
        re.compile(r"\bx[_\-]tenant[_\-][a-z]+\b", re.IGNORECASE),
        "tenant-specific request header",
    ),
    (
        "tenant-context",
        re.compile(r"\btenant[_\-]?(context|scope|scoped|routing|store|storage)\b", re.IGNORECASE),
        "tenant context, routing, or tenant-scoped storage semantics",
    ),
    (
        "multi-tenant",
        re.compile(r"\bmulti[_\-\s]?tenan(t|cy)\b", re.IGNORECASE),
        "multi-tenancy semantics",
    ),
    (
        "tenant-identifier",
        re.compile(r"\btenants?\b|\btenant[_\-]?ids?\b|\btenantId\b", re.IGNORECASE),
        "tenant identifier or tenant-scoped field",
    ),
)


def scan(root: Path) -> list[Violation]:
    """Return every prohibited multi-tenant construct on the release surface."""
    violations: list[Violation] = []
    for path in iter_scoped_files(root):
        content = read_text(path)
        if content is None:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            for label, pattern, detail in PROHIBITED_PATTERNS:
                match = pattern.search(line)
                if match:
                    violations.append(
                        Violation(
                            path=relative_to(path, root),
                            line=lineno,
                            pattern=label,
                            detail=f"{detail} (matched {match.group(0)!r})",
                        )
                    )
                    break
    return violations


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    return report(CHECK_NAME, args.root, scan(args.root), args.as_json)


if __name__ == "__main__":
    sys.exit(main())
