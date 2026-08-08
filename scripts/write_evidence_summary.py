#!/usr/bin/env python3
"""Write the machine-readable M0 evidence summary from an executed gate run.

The summary is **derived, never authored**. Every check record comes from a
gate execution that actually happened, every artifact digest is recomputed from
the file on disk, and every criterion status is a mechanical consequence of
exit codes.

That constrains what the document may claim. ``CRITERION_EVIDENCE`` below maps
each acceptance criterion to the gate checks that constitute its evidence, and
a criterion is ``pass`` only when every mapped check ran and exited ``0``. A
criterion with no mapped check is ``not_run`` -- including criteria that earlier
evidence files record as passing, because a status this document cannot derive
is a status it must not assert. ``ACCEPTANCE_CRITERIA.md`` treats ``NOT RUN``
as ``FAIL`` for milestone completion, so the verdict stays ``not_complete``
until every criterion is derivable and green.

The mapping itself is a declared judgement, not a discovery. It is stated here,
in one place, so it can be reviewed and disagreed with.

Exit codes:
    0 - the summary was written and validates against its schema
    1 - the summary could not be produced or does not validate
    2 - usage error
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from _contracts import ContractLoadError, load_json
from _release import (
    CHECKSUMS_NAME,
    COMPATIBILITY_SUMMARY_NAME,
    DIST_DIR,
    EXAMPLE_LOCK_NAME,
    MANIFEST_NAME,
    ReleaseError,
    bundle_name,
    commit_sha,
    release_version,
    sha256_file,
    working_tree_is_dirty,
)
from _scope import repo_root

CHECK_NAME = "write_evidence_summary"

SUMMARY_SCHEMA_PATH = "evidence/m0-summary.schema.json"
SUMMARY_OUTPUT_PATH = "evidence/m0-summary.json"

#: Which executed gate checks constitute the evidence for each criterion.
#:
#: Read this as: "if all of these exited 0, the criterion's stated evidence was
#: produced." An empty tuple means no gate check evidences the criterion, so it
#: cannot be derived here and is reported not_run with the reason in
#: CRITERION_NOTES.
CRITERION_EVIDENCE: dict[str, tuple[str, ...]] = {
    # Foundation and boundary.
    "M0-CON-001": ("check_no_implementation_code", "pytest"),
    "M0-CON-002": ("validate_matrix", "pytest"),
    "M0-CON-003": ("check_no_multitenancy", "pytest"),
    "M0-CON-004": ("check_no_implementation_code", "pytest"),
    "M0-CON-005": ("check_no_implementation_code", "pytest"),
    # Contract model.
    "M0-CON-010": ("pytest",),
    "M0-CON-011": ("validate_contracts", "validate_examples", "pytest"),
    "M0-CON-012": ("validate_contracts", "validate_examples", "pytest"),
    "M0-CON-013": ("validate_contracts", "validate_examples", "pytest"),
    "M0-CON-014": ("validate_contracts", "validate_catalog", "pytest"),
    "M0-CON-015": ("validate_catalog", "pytest"),
    "M0-CON-016": ("check_references", "pytest"),
    "M0-CON-017": ("validate_examples", "pytest"),
    # Governance and compatibility.
    "M0-CON-020": ("pytest",),
    "M0-CON-021": ("pytest",),
    "M0-CON-022": ("pytest",),
    "M0-CON-023": ("validate_contracts", "pytest"),
    "M0-CON-024": ("check_compatibility", "pytest"),
    "M0-CON-025": ("check_compatibility", "pytest"),
    "M0-CON-026": ("check_compatibility", "pytest"),
    "M0-CON-027": ("check_compatibility", "pytest"),
    "M0-CON-028": ("check_compatibility", "pytest"),
    "M0-CON-029": ("check_compatibility", "pytest"),
    # Build, CI, security, release.
    "M0-CON-030": ("quality_gate",),
    "M0-CON-031": ("pytest",),
    "M0-CON-032": ("ruff_format", "ruff_lint", "mypy"),
    "M0-CON-033": ("pytest",),
    "M0-CON-034": ("secret_scan",),
    "M0-CON-035": ("dependency_audit", "pytest"),
    "M0-CON-036": ("build_bundle", "verify_bundle", "pytest"),
    "M0-CON-037": ("verify_bundle", "pytest"),
    "M0-CON-038": ("verify_bundle",),
    # Cross-repository readiness and evidence.
    "M0-CON-040": ("validate_matrix", "pytest"),
    "M0-CON-041": ("build_bundle", "verify_consumer_lock"),
    "M0-CON-042": ("verify_consumer_lock", "pytest"),
    "M0-CON-043": ("check_evidence", "pytest"),
    "M0-CON-044": ("check_evidence",),
    "M0-CON-045": ("check_evidence",),
}

#: Standing notes on how a criterion is established, where the mechanism is
#: not obvious from the check name alone.
CRITERION_NOTES: dict[str, str] = {
    "M0-CON-044": (
        "check_evidence verifies the recorded verdict structurally -- that a completed audit "
        "for a reachable commit exists, returns PASS, and covers every criterion. It does not "
        "decide that the audit passed; that is the auditor's judgement, and a gate asserting it "
        "would be the circular evidence AUDITOR.md section 7 rejects."
    ),
    "M0-CON-045": (
        "check_evidence verifies the delivery verdict is derivable: the report may not claim "
        "PASS while any criterion it reports reads FAIL or NOT RUN."
    ),
}


def read_checks(path: Path) -> list[dict[str, Any]]:
    """Read the gate's tab-separated check record.

    Format is ``name<TAB>exit_code<TAB>command``, one line per executed check,
    appended by ``quality_gate.sh`` as each check finishes.
    """
    if not path.is_file():
        raise ReleaseError(f"{path}: no gate check record; run scripts/quality_gate.sh")

    checks: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 3:
            raise ReleaseError(f"{path}:{number}: expected 'name<TAB>exit<TAB>command', got {line!r}")
        name, exit_code, command = fields
        try:
            code = int(exit_code)
        except ValueError as exc:
            raise ReleaseError(f"{path}:{number}: unparseable exit code {exit_code!r}") from exc
        checks.append(
            {
                "name": name,
                "command": command,
                "exit_code": code,
                "status": "pass" if code == 0 else "fail",
            }
        )
    if not checks:
        raise ReleaseError(f"{path}: gate check record is empty")
    return checks


def collect_artifacts(root: Path, dist: Path) -> list[dict[str, str]]:
    """Hash whichever release artifacts are actually present."""
    names = [MANIFEST_NAME, CHECKSUMS_NAME, COMPATIBILITY_SUMMARY_NAME, EXAMPLE_LOCK_NAME]
    # An unreadable version only means the archive cannot be named; the other
    # artifacts are still hashed and reported.
    with contextlib.suppress(ReleaseError):
        names.insert(0, bundle_name(release_version(root)))
    artifacts = []
    for name in names:
        path = dist / name
        if path.is_file():
            artifacts.append({"path": f"{dist.name}/{name}", "sha256": sha256_file(path)})
    return artifacts


def derive_criteria(
    checks: list[dict[str, Any]],
    skipped: list[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Derive each criterion's status from the executed checks."""
    outcome = {check["name"]: check["status"] for check in checks}
    skipped_set = set(skipped)

    criteria: list[dict[str, Any]] = []
    counts = {"pass": 0, "fail": 0, "not_run": 0}

    for criterion in sorted(CRITERION_EVIDENCE):
        required = CRITERION_EVIDENCE[criterion]
        note = CRITERION_NOTES.get(criterion)

        if not required:
            status = "not_run"
        elif absent := [n for n in required if n in skipped_set or n not in outcome]:
            status = "not_run"
            note = f"not derivable: {', '.join(absent)} did not execute in this run"
        elif failed := [n for n in required if outcome[n] == "fail"]:
            status = "fail"
            note = f"{', '.join(failed)} exited non-zero"
        else:
            status = "pass"

        entry: dict[str, Any] = {"id": criterion, "status": status, "derived_from": list(required)}
        if note:
            entry["note"] = note
        counts[status] += 1
        criteria.append(entry)

    counts["total"] = len(criteria)
    return criteria, counts


def build_summary(
    root: Path,
    dist: Path,
    checks: list[dict[str, Any]],
    skipped: list[str],
    generated_at: str,
) -> dict[str, Any]:
    """Assemble the summary document from executed facts."""
    criteria, counts = derive_criteria(checks, skipped)
    gate_result = "pass" if all(c["status"] == "pass" for c in checks) else "fail"

    return {
        "repository": "ai-business-contracts",
        "milestone": "M0",
        "commit_sha": commit_sha(root),
        "generated_at_utc": generated_at,
        "working_tree_clean": not working_tree_is_dirty(root),
        "quality_gate": {
            "result": gate_result,
            "checks": checks,
            "skipped": sorted(skipped),
        },
        "artifacts": collect_artifacts(root, dist),
        "criteria": criteria,
        "criteria_summary": counts,
        "milestone_verdict": "pass" if counts["fail"] == 0 and counts["not_run"] == 0 else "not_complete",
    }


def validate_summary(root: Path, summary: dict[str, Any]) -> list[str]:
    """Validate the summary against its own schema."""
    try:
        schema = load_json(root / SUMMARY_SCHEMA_PATH)
    except ContractLoadError as exc:
        return [str(exc)]
    validator = Draft202012Validator(schema)
    return [
        f"at {'/'.join(str(p) for p in error.absolute_path) or '(root)'}: {error.message}"
        for error in sorted(validator.iter_errors(summary), key=lambda e: list(e.absolute_path))
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=repo_root(), help="repository root")
    parser.add_argument(
        "--dist", type=Path, default=None, help=f"artifact directory (default: <root>/{DIST_DIR})"
    )
    parser.add_argument("--checks", type=Path, required=True, help="tab-separated gate check record")
    parser.add_argument("--skipped", default="", help="comma-separated names of checks the gate did not run")
    parser.add_argument(
        "--output", type=Path, default=None, help=f"output path (default: <root>/{SUMMARY_OUTPUT_PATH})"
    )
    parser.add_argument("--generated-at", default=None, help="UTC timestamp to stamp (default: now)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root: Path = args.root
    dist: Path = args.dist or (root / DIST_DIR)
    output: Path = args.output or (root / SUMMARY_OUTPUT_PATH)
    generated_at = args.generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    skipped = [name for name in args.skipped.split(",") if name]

    try:
        checks = read_checks(args.checks)
        summary = build_summary(root, dist, checks, skipped, generated_at)
    except ReleaseError as exc:
        print(f"{CHECK_NAME}: FAIL - {exc}", file=sys.stderr)
        return 1

    errors = validate_summary(root, summary)
    if errors:
        print(
            f"{CHECK_NAME}: FAIL - the summary does not validate against {SUMMARY_SCHEMA_PATH}",
            file=sys.stderr,
        )
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    counts = summary["criteria_summary"]
    print(
        f"{CHECK_NAME}: PASS - {output.relative_to(root) if output.is_relative_to(root) else output} "
        f"({len(checks)} checks, gate {summary['quality_gate']['result']}; criteria "
        f"{counts['pass']} pass / {counts['fail']} fail / {counts['not_run']} not_run; "
        f"milestone {summary['milestone_verdict']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
