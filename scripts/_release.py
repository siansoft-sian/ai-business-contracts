"""Shared release-artifact vocabulary: paths, hashing, and version resolution.

This module holds only what the *producer* side of a release needs.
``verify_bundle.py`` deliberately does not import the inclusion rule from here:
a verifier that reuses the builder's definition of "what belongs in a bundle"
can only ever confirm the builder agreed with itself. The two state the rule
independently -- positively here, negatively there -- so a mistake in either
one is caught rather than mirrored.
"""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

#: Directories published in a release bundle. This is the release surface from
#: ``_scope.py`` plus ``governance/``: a consumer that receives contracts
#: without the rules governing their change has received a snapshot, not a
#: contract.
BUNDLE_DIRECTORIES: tuple[str, ...] = (
    "contracts",
    "catalog",
    "compatibility",
    "governance",
    "templates",
)

#: Root files published alongside them. ``README.md`` describes what the
#: artifact is; nothing else at the root is an output of this repository
#: rather than an input to it.
BUNDLE_ROOT_FILES: tuple[str, ...] = ("README.md",)

#: Excluded from the bundle even though they live under a bundled directory.
#: The compatibility fixtures are curated *proofs of the engine*, not published
#: contracts, and several of them deliberately contain invalid or breaking
#: contract source. Shipping them would put artifacts into the release that the
#: repository's own validators are built to reject.
BUNDLE_EXCLUDED_PREFIXES: tuple[str, ...] = ("compatibility/fixtures",)

#: Never carried, wherever they appear.
BUNDLE_EXCLUDED_NAMES: frozenset[str] = frozenset({".DS_Store"})

DIST_DIR = "dist"
MANIFEST_NAME = "contract-manifest.json"
CHECKSUMS_NAME = "SHA256SUMS"
COMPATIBILITY_SUMMARY_NAME = "compatibility-summary.json"
EXAMPLE_LOCK_NAME = "example-consumer-lock.yaml"

#: Which generation of the governance rules a release is produced under.
#: Bumped when a governance rule changes in a way that alters how a release
#: must be interpreted, so a gate can tell whether an artifact predates it.
GOVERNANCE_VERSION = "1"


class ReleaseError(Exception):
    """A release artifact could not be produced from the current tree."""


def sha256_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_version(root: Path) -> str:
    """Read the release version from ``pyproject.toml``.

    One declared version, read rather than passed, so the manifest cannot
    describe a version the repository does not claim.
    """
    path = root / "pyproject.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ReleaseError(f"pyproject.toml: {exc}") from exc
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ReleaseError("pyproject.toml: [project].version is missing")
    return version


def _git(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReleaseError(f"git {' '.join(args)} failed: {exc}") from exc
    return completed.stdout.strip()


def commit_sha(root: Path) -> str:
    """Return the full SHA of ``HEAD``."""
    return _git(root, "rev-parse", "HEAD")


#: Excluded from the dirty-tree check. ``evidence/`` and ``DELIVERY_REPORT.md``
#: are *outputs* of the gate and of the milestone, never inputs to a build. The
#: gate writes the M0 summary at the end of every run, and the delivery report
#: is completed from evidence after it; nothing in the bundle or the manifest
#: is derived from either. Counting them would make each run dirty the tree for
#: the next one, so a second gate run could not build -- a false failure, and
#: one that would push people toward --skip-release. Everything a build
#: actually reads (contract source, catalog, governance, templates, the build
#: scripts, pyproject) is still checked, so the manifest's claim "this bundle
#: came from commit X" remains exactly as strong.
DIRTY_CHECK_EXCLUSIONS: tuple[str, ...] = ("evidence", "DELIVERY_REPORT.md")


def working_tree_is_dirty(root: Path) -> bool:
    """Return whether any tracked *build input* differs from ``HEAD``.

    Untracked files are ignored on purpose: the bundle is assembled from
    tracked source, so an untracked scratch file cannot change what is built.
    """
    pathspec = [f":(exclude){name}" for name in DIRTY_CHECK_EXCLUSIONS]
    return bool(_git(root, "status", "--porcelain", "--untracked-files=no", "--", ".", *pathspec))


def commit_timestamp_utc(root: Path) -> str:
    """Return HEAD's commit time as an RFC 3339 UTC instant.

    The build timestamp is derived from the commit rather than from the wall
    clock so that rebuilding the same commit reproduces the same manifest
    bytes. A timestamp that changed per run would make the manifest
    unreproducible for no gain -- what a consumer needs to know is which source
    produced the artifact, and that is a property of the commit.
    """
    epoch = _git(root, "log", "-1", "--format=%ct")
    try:
        seconds = int(epoch)
    except ValueError as exc:
        raise ReleaseError(f"unparseable commit timestamp: {epoch!r}") from exc
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def commit_epoch(root: Path) -> int:
    """Return HEAD's commit time as a Unix epoch, for archive member mtimes."""
    return int(_git(root, "log", "-1", "--format=%ct"))


def bundle_name(version: str) -> str:
    """Return the release archive filename for ``version``."""
    return f"ai-business-contracts-{version}.tar.gz"


def bundle_members(root: Path) -> list[tuple[Path, str]]:
    """Return ``(source_path, archive_relative_path)`` for every bundled file.

    Sorted by archive path so the member order is a property of the content,
    not of filesystem iteration order.
    """
    members: list[tuple[Path, str]] = []

    for name in BUNDLE_ROOT_FILES:
        path = root / name
        if path.is_file():
            members.append((path, name))

    for directory in BUNDLE_DIRECTORIES:
        base = root / directory
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.name in BUNDLE_EXCLUDED_NAMES:
                continue
            relative = path.relative_to(root).as_posix()
            if any(relative.startswith(f"{p}/") or relative == p for p in BUNDLE_EXCLUDED_PREFIXES):
                continue
            members.append((path, relative))

    return sorted(members, key=lambda pair: pair[1])
