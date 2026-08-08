#!/usr/bin/env python3
"""Scan tracked files for committed secrets, exempting provable digests.

``detect-secrets`` does the detecting. This wrapper exists for the triage step,
because the raw scan flags something this repository is *required* to contain:
SHA-256 checksums and git commit SHAs. Contract examples carry them, the
release manifest is built from them, and consumer locks are meaningless
without them. They are high-entropy hex strings, so an entropy detector cannot
tell them from a credential -- and it should not try.

The obvious remedy is a ``.secrets.baseline`` entry per finding. That works
once and then rots. Baseline entries are keyed by file *and line number*, and
``evidence/m0-summary.json`` is regenerated on every gate run with digests
that move as the document changes. A baseline covering it would need
regenerating each run, which is auto-suppression wearing a baseline's clothes.

So the exemption is stated as a rule and re-checked every run instead: a
finding is discarded only if the line it sits on is an assignment to a field
whose name ends in ``sha256`` or is ``commit_sha``, with a hex value of digest
length. Anything else is blocking. The claim "this is a digest, not a
credential" is therefore verified continuously rather than asserted once, and
the exemption cannot silently widen -- a credential assigned to a differently
named field, or a bare high-entropy string, still fails.

``.secrets.baseline`` remains supported for genuine one-off false positives
the rule does not cover. Entries are matched by ``(filename, hashed_secret)``
rather than by line number, so reflowing a file does not resurrect a reviewed
finding, and each must carry an explicit ``is_secret: false`` verdict.

Exit codes:
    0 - no unexplained finding
    1 - at least one finding (blocking)
    2 - the scanner could not be run, so nothing was checked
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from _scope import Violation, build_parser, report

CHECK_NAME = "check_secrets"

BASELINE_PATH = ".secrets.baseline"

#: A line assigning a checksum or commit SHA. The field name carries the
#: meaning: ``bundle_sha256``, ``source_sha256``, ``manifest_sha256``,
#: ``sha256``, ``commit_sha``. Matching covers JSON, YAML, and YAML list items.
DIGEST_ASSIGNMENT = re.compile(
    r'^\s*[-"]?\s*"?(?P<field>[A-Za-z_]*(?:sha256|commit_sha))"?\s*[:=]\s*'
    r'"?(?P<value>[0-9a-f]{40,64})"?,?\s*$'
)


class ScannerUnavailable(Exception):
    """detect-secrets could not be run, so no scan was performed."""


def tracked_files(root: Path) -> list[str]:
    """Return every git-tracked path, which is the scan surface.

    Tracked rather than on-disk: a secret that is not committed is not a
    committed secret, and scanning ``.venv/`` would drown the signal.
    """
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScannerUnavailable(f"git ls-files failed: {exc}") from exc

    # The baseline itself is excluded, as detect-secrets excludes its own
    # baseline: it stores SHA-1 *hashes* of findings, never the findings. A
    # hash of a secret is not a secret -- storing the hash is the whole point
    # of the format. Scanning it would flag the record of a reviewed finding
    # and make the review mechanism unusable the moment it was used.
    return [name for name in completed.stdout.split("\0") if name and name != BASELINE_PATH]


def run_scan(root: Path, files: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Run detect-secrets over ``files`` and return its findings by path."""
    executable = shutil.which("detect-secrets")
    if executable is None:
        raise ScannerUnavailable(
            "detect-secrets is not on PATH; install the dev dependency group. "
            "A scan that did not run has not passed"
        )
    try:
        completed = subprocess.run(
            [executable, "scan", *files],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScannerUnavailable(f"detect-secrets scan failed: {exc}") from exc
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ScannerUnavailable(f"detect-secrets produced unparseable output: {exc}") from exc
    results = document.get("results", {})
    return results if isinstance(results, dict) else {}


def load_reviewed(root: Path) -> set[tuple[str, str]]:
    """Return ``(filename, hashed_secret)`` pairs reviewed as not-a-secret.

    An entry without an explicit ``is_secret`` verdict is an unreviewed
    suppression and is deliberately not honoured.
    """
    path = root / BASELINE_PATH
    if not path.is_file():
        return set()
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    reviewed: set[tuple[str, str]] = set()
    for filename, findings in baseline.get("results", {}).items():
        for finding in findings:
            if finding.get("is_secret") is False and finding.get("hashed_secret"):
                reviewed.add((filename, str(finding["hashed_secret"])))
    return reviewed


def is_digest_line(line: str) -> bool:
    """Return whether ``line`` assigns a checksum or commit SHA."""
    return DIGEST_ASSIGNMENT.match(line) is not None


def triage(
    root: Path,
    results: dict[str, list[dict[str, Any]]],
    reviewed: set[tuple[str, str]],
) -> tuple[list[Violation], int, int]:
    """Split findings into blocking violations and explained ones."""
    violations: list[Violation] = []
    digests = 0
    baselined = 0

    for filename in sorted(results):
        path = root / filename
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            lines = []

        for finding in results[filename]:
            number = int(finding.get("line_number", 0))
            line = lines[number - 1] if 0 < number <= len(lines) else ""

            if is_digest_line(line):
                digests += 1
                continue
            if (filename, str(finding.get("hashed_secret"))) in reviewed:
                baselined += 1
                continue

            violations.append(
                Violation(
                    path=filename,
                    line=number,
                    pattern=str(finding.get("type", "unknown")),
                    detail=(
                        "potential secret in a tracked file. If this is a checksum, assign it "
                        "to a field named '<something>sha256' or 'commit_sha'; otherwise remove "
                        f"it. Reviewed false positives go in {BASELINE_PATH} with an explicit "
                        "is_secret: false verdict"
                    ),
                )
            )

    return violations, digests, baselined


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    root: Path = args.root

    try:
        files = tracked_files(root)
        results = run_scan(root, files)
    except ScannerUnavailable as exc:
        # Not reported as a pass. A scan that did not happen has not passed,
        # and reporting it green is the failure HARNESS.md section 7 forbids.
        print(f"{CHECK_NAME}: NOT RUN - {exc}", file=sys.stderr)
        return 2

    violations, digests, baselined = triage(root, results, load_reviewed(root))

    explained = f"{digests} verified checksum/commit-SHA field(s)"
    if baselined:
        explained += f", {baselined} reviewed baseline entr(ies)"
    return report(
        CHECK_NAME,
        root,
        violations,
        args.as_json,
        pass_message=f"{len(files)} tracked files scanned; no unexplained finding ({explained})",
        fail_noun="potential secret",
    )


if __name__ == "__main__":
    sys.exit(main())
