"""Shared path scoping for the ai-business-contracts boundary scanners.

This module exists to answer one question consistently: *which files does a
boundary gate look at?*

The answer is defined **positively**. `CONTRACT_BEARING_PATHS` enumerates the
release surface — the directories whose contents are published as contract
artifacts and consumed by other repositories. Everything else in the
repository (root governing documents, ``governance/``, ``evidence/``,
``execution-prompts/``, ``scripts/``, ``tests/``, ``dist/``, ``.github/``) is
outside the scanned scope by construction.

Why positive scoping rather than a root-wide scan plus an ignore-list:
EP-00 established across three runs that the governing documents and the
evidence files necessarily *quote* the constructs they forbid. ``PROMPT.md``
lists "tenant identifiers in payloads or schemas" as a prohibition;
``CONTRACT_STANDARD.md`` lists "asyncpg pool objects" as prohibited coupling.
A root-wide scan flags those documents — the very documents mandating the
scan. Worse, the count grows on every evidence write (EP-00 measured the
tenant-pattern match count rising 30 -> 36 -> 42 across its three runs, with
later runs matching earlier runs' own result tables).

An ignore-list would therefore need a new exception each time evidence is
written: a gate that weakens monotonically as the milestone progresses.
``HARNESS.md`` section 7 and EP-05 both forbid obtaining a green gate by
weakening it. Positive scoping is a correctly drawn boundary instead, and it
does not reduce enforcement strength over the paths that actually carry
contracts.

Consequence for authors: prose discussing prohibited constructs belongs in
``governance/`` or the root documents, never inside the release surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

#: Directories that make up the release surface. A file is in scope for the
#: boundary scanners if and only if it lives under one of these, relative to
#: the repository root. Adding a directory here widens enforcement; removing
#: one narrows it and requires governance review.
CONTRACT_BEARING_PATHS: tuple[str, ...] = (
    "contracts",
    "catalog",
    "compatibility",
    "templates",
)

#: Files that carry no scannable text content.
_SKIP_NAMES = frozenset({".gitkeep", ".DS_Store"})


def repo_root() -> Path:
    """Return the repository root (the parent of ``scripts/``)."""
    return Path(__file__).resolve().parent.parent


def in_scope_roots(root: Path) -> list[Path]:
    """Return the existing release-surface directories under ``root``."""
    return [d for d in (root / name for name in CONTRACT_BEARING_PATHS) if d.is_dir()]


def iter_scoped_files(root: Path) -> list[Path]:
    """Yield every scannable file on the release surface under ``root``.

    Sorted for deterministic reporting. No extension filter is applied: a
    prohibited construct hidden in a Markdown file inside ``contracts/`` is
    still a prohibited construct on the release surface.
    """
    files: list[Path] = []
    for scope_dir in in_scope_roots(root):
        for path in scope_dir.rglob("*"):
            if path.is_file() and path.name not in _SKIP_NAMES:
                files.append(path)
    return sorted(files)


def is_in_scope(path: Path, root: Path) -> bool:
    """Return whether ``path`` lies on the release surface of ``root``."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    if not relative.parts:
        return False
    return relative.parts[0] in CONTRACT_BEARING_PATHS


def read_text(path: Path) -> str | None:
    """Read ``path`` as UTF-8 text, or return ``None`` if it is binary."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def relative_to(path: Path, root: Path) -> str:
    """Render ``path`` relative to ``root`` with forward slashes."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


@dataclass(frozen=True)
class Violation:
    """A single prohibited construct found by a boundary scanner."""

    path: str
    line: int
    pattern: str
    detail: str

    def render(self) -> str:
        location = f"{self.path}:{self.line}" if self.line else self.path
        return f"{location}: [{self.pattern}] {self.detail}"


def build_parser(description: str) -> argparse.ArgumentParser:
    """Build the CLI parser shared by every boundary scanner."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--root",
        type=Path,
        default=repo_root(),
        help="repository root to scan (default: this repository)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit machine-readable JSON instead of text",
    )
    return parser


def report(check: str, root: Path, violations: list[Violation], as_json: bool) -> int:
    """Print results and return the process exit code.

    Returns ``0`` when no violation was found and ``1`` otherwise. The exit
    code is the contract: CI and the local quality gate branch on it.
    """
    if as_json:
        payload = {
            "check": check,
            "root": str(root),
            "scope": list(CONTRACT_BEARING_PATHS),
            "result": "fail" if violations else "pass",
            "violation_count": len(violations),
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif violations:
        print(f"{check}: FAIL - {len(violations)} prohibited construct(s) found", file=sys.stderr)
        for violation in violations:
            print(f"  {violation.render()}", file=sys.stderr)
    else:
        scanned = ", ".join(CONTRACT_BEARING_PATHS)
        print(f"{check}: PASS - no prohibited constructs in scope ({scanned})")
    return 1 if violations else 0
