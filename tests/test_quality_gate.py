"""Tests for the single quality-gate entry point, CI parity, and the M0 summary.

The load-bearing test here is ``test_ci_does_not_reimplement_the_checks``.
``HARNESS.md`` section 8 requires CI and the local gate to invoke the same
commands, and the failure mode is silent: a check added to one list and not the
other produces a green CI over a red local gate, or the reverse, and neither
result then means anything. Asserting that the workflows *call the gate* is not
enough -- a workflow could call it and then run extra checks, or call it and
have the real checks live inline. So the workflows are also asserted not to
mention the individual tools at all.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))

import write_evidence_summary  # noqa: E402
from write_evidence_summary import CRITERION_EVIDENCE  # noqa: E402

GATE = REPO_ROOT / "scripts" / "quality_gate.sh"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI = WORKFLOWS / "ci.yml"
RELEASE = WORKFLOWS / "release.yml"

#: Every check TEST_PLAN.md section 3 requires the gate to orchestrate, mapped
#: to the token that must appear in the gate script.
REQUIRED_GATE_CHECKS: dict[str, str] = {
    "format": "ruff format",
    "lint": "ruff check",
    "static typing": "mypy",
    "tests": "pytest",
    "schema validation": "validate_contracts.py",
    "reference validation": "check_references.py",
    "example validation": "validate_examples.py",
    "catalog validation": "validate_catalog.py",
    "compatibility validation": "check_compatibility.py",
    "multi-tenancy negative scan": "check_no_multitenancy.py",
    "implementation-boundary scan": "check_no_implementation_code.py",
    "secret scan": "detect-secrets-hook",
    "dependency vulnerability audit": "pip-audit",
    "bundle/manifest validation": "verify_bundle.py",
}

#: Tool invocations that must never appear in a workflow file. If CI ran any of
#: these directly it would have its own list of checks to drift from.
FORBIDDEN_IN_WORKFLOWS: tuple[str, ...] = (
    "ruff",
    "mypy",
    "pytest",
    "detect-secrets",
    "pip-audit",
    "validate_contracts.py",
    "validate_catalog.py",
    "check_compatibility.py",
    "check_no_multitenancy.py",
    "build_bundle.py",
)


def _gate_source() -> str:
    return GATE.read_text(encoding="utf-8")


def _workflow_run_steps(path: Path) -> list[str]:
    """Return the shell body of every ``run:`` step in a workflow."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps: list[str] = []
    for job in document.get("jobs", {}).values():
        for step in job.get("steps", []):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                steps.append(step["run"])
    return steps


# --- the gate covers what the test plan requires --------------------------


def test_gate_exists_and_is_executable() -> None:
    assert GATE.is_file()
    assert GATE.stat().st_mode & 0o111, "the gate must be directly executable"


@pytest.mark.parametrize(("description", "token"), sorted(REQUIRED_GATE_CHECKS.items()))
def test_gate_orchestrates_every_required_check(description: str, token: str) -> None:
    assert token in _gate_source(), f"the gate does not run {description} ({token})"


def test_gate_runs_every_check_rather_than_stopping_at_the_first_failure() -> None:
    """``set -e`` here would truncate the evidence to the first failure."""
    source = _gate_source()
    assert "set -e" not in source.replace("set -euo", "").replace("set -uo", "")


def test_gate_records_a_check_for_every_criterion_it_claims_to_evidence() -> None:
    """A criterion mapped to a check the gate never runs would be underivable.

    This catches the mapping and the gate drifting apart, which would otherwise
    surface as a silently permanent ``not_run`` in the summary.
    """
    source = _gate_source()
    referenced = {name for names in CRITERION_EVIDENCE.values() for name in names}
    for name in sorted(referenced):
        assert f"run {name} " in source or f'"{name}"' in source, (
            f"{name} is mapped to a criterion but the gate never records it"
        )


# --- CI parity -------------------------------------------------------------


@pytest.mark.parametrize("workflow", [CI, RELEASE], ids=["ci", "release"])
def test_workflow_calls_the_gate(workflow: Path) -> None:
    steps = _workflow_run_steps(workflow)
    assert any("scripts/quality_gate.sh" in step for step in steps), (
        f"{workflow.name} does not run the quality gate"
    )


@pytest.mark.parametrize("workflow", [CI, RELEASE], ids=["ci", "release"])
def test_ci_does_not_reimplement_the_checks(workflow: Path) -> None:
    """CI must call the gate, not restate it."""
    for step in _workflow_run_steps(workflow):
        if "quality_gate.sh" in step:
            continue
        for tool in FORBIDDEN_IN_WORKFLOWS:
            assert tool not in step, (
                f"{workflow.name} invokes {tool!r} directly; the gate is the only place "
                "checks are declared, or the two lists will drift"
            )


@pytest.mark.parametrize("workflow", [CI, RELEASE], ids=["ci", "release"])
def test_workflow_installs_a_locked_toolchain(workflow: Path) -> None:
    """An unlocked sync would test a different dependency set than the audit."""
    steps = _workflow_run_steps(workflow)
    sync = [step for step in steps if "uv sync" in step]
    assert sync, f"{workflow.name} does not install the toolchain"
    assert all("--locked" in step for step in sync)


def test_no_workflow_other_than_the_two_declared_ones() -> None:
    found = {path.name for path in WORKFLOWS.glob("*.yml")} | {path.name for path in WORKFLOWS.glob("*.yaml")}
    assert found == {"ci.yml", "release.yml"}


# --- the M0 evidence summary ----------------------------------------------


def _checks_file(tmp_path: Path, records: list[tuple[str, int]]) -> Path:
    path = tmp_path / "gate-checks.tsv"
    path.write_text(
        "".join(f"{name}\t{code}\tcommand for {name}\n" for name, code in records),
        encoding="utf-8",
    )
    return path


ALL_CHECKS = sorted({name for names in CRITERION_EVIDENCE.values() for name in names})


def test_summary_validates_against_its_schema(tmp_path: Path) -> None:
    checks = _checks_file(tmp_path, [(name, 0) for name in ALL_CHECKS])
    output = tmp_path / "m0-summary.json"
    code = write_evidence_summary.main(
        [
            "--root",
            str(REPO_ROOT),
            "--dist",
            str(tmp_path),
            "--checks",
            str(checks),
            "--output",
            str(output),
            "--generated-at",
            "2026-08-07T00:00:00Z",
        ]
    )
    assert code == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["repository"] == "ai-business-contracts"
    assert summary["milestone"] == "M0"
    errors = write_evidence_summary.validate_summary(REPO_ROOT, summary)
    assert errors == []


def test_a_failing_check_fails_every_criterion_that_depends_on_it(tmp_path: Path) -> None:
    records = [(name, 1 if name == "check_no_multitenancy" else 0) for name in ALL_CHECKS]
    checks = _checks_file(tmp_path, records)
    output = tmp_path / "m0-summary.json"
    assert (
        write_evidence_summary.main(
            [
                "--root",
                str(REPO_ROOT),
                "--dist",
                str(tmp_path),
                "--checks",
                str(checks),
                "--output",
                str(output),
                "--generated-at",
                "2026-08-07T00:00:00Z",
            ]
        )
        == 0
    )
    summary = json.loads(output.read_text(encoding="utf-8"))
    status = {entry["id"]: entry["status"] for entry in summary["criteria"]}
    assert status["M0-CON-003"] == "fail"
    assert summary["quality_gate"]["result"] == "fail"
    assert summary["milestone_verdict"] == "not_complete"


def test_a_skipped_check_yields_not_run_not_a_pass(tmp_path: Path) -> None:
    """A reduced run must never look like a complete one."""
    records = [(name, 0) for name in ALL_CHECKS if name != "verify_bundle"]
    checks = _checks_file(tmp_path, records)
    output = tmp_path / "m0-summary.json"
    assert (
        write_evidence_summary.main(
            [
                "--root",
                str(REPO_ROOT),
                "--dist",
                str(tmp_path),
                "--checks",
                str(checks),
                "--skipped",
                "verify_bundle",
                "--output",
                str(output),
                "--generated-at",
                "2026-08-07T00:00:00Z",
            ]
        )
        == 0
    )
    summary = json.loads(output.read_text(encoding="utf-8"))
    status = {entry["id"]: entry["status"] for entry in summary["criteria"]}
    assert status["M0-CON-037"] == "not_run"
    assert summary["milestone_verdict"] == "not_complete"


def test_criteria_cover_every_acceptance_criterion(tmp_path: Path) -> None:
    """The map must not silently omit a criterion.

    An omitted criterion would not appear in the summary at all, which reads as
    "not applicable" rather than "not checked".
    """
    text = (REPO_ROOT / "ACCEPTANCE_CRITERIA.md").read_text(encoding="utf-8")
    declared = {line.split("|")[1].strip() for line in text.splitlines() if line.startswith("| M0-CON-")}
    assert declared, "no criteria parsed from ACCEPTANCE_CRITERIA.md"
    assert declared == set(CRITERION_EVIDENCE), (
        f"missing from the map: {sorted(declared - set(CRITERION_EVIDENCE))}; "
        f"unknown in the map: {sorted(set(CRITERION_EVIDENCE) - declared)}"
    )


def test_criteria_without_a_gate_check_are_reported_not_run(tmp_path: Path) -> None:
    """Nothing may be claimed that the gate cannot derive."""
    checks = _checks_file(tmp_path, [(name, 0) for name in ALL_CHECKS])
    output = tmp_path / "m0-summary.json"
    write_evidence_summary.main(
        [
            "--root",
            str(REPO_ROOT),
            "--dist",
            str(tmp_path),
            "--checks",
            str(checks),
            "--output",
            str(output),
            "--generated-at",
            "2026-08-07T00:00:00Z",
        ]
    )
    summary = json.loads(output.read_text(encoding="utf-8"))
    by_id = {entry["id"]: entry for entry in summary["criteria"]}
    for criterion in ("M0-CON-043", "M0-CON-044", "M0-CON-045"):
        assert by_id[criterion]["status"] == "not_run"
        assert by_id[criterion]["derived_from"] == []
        assert by_id[criterion].get("note"), "an underivable criterion must say why"


def test_an_empty_or_missing_check_record_is_refused(tmp_path: Path) -> None:
    missing = tmp_path / "absent.tsv"
    assert write_evidence_summary.main(["--root", str(REPO_ROOT), "--checks", str(missing)]) == 1

    empty = tmp_path / "empty.tsv"
    empty.write_text("", encoding="utf-8")
    assert write_evidence_summary.main(["--root", str(REPO_ROOT), "--checks", str(empty)]) == 1


# --- the secret-scan baseline ---------------------------------------------


BASELINE = REPO_ROOT / ".secrets.baseline"


def test_secret_baseline_exists() -> None:
    assert BASELINE.is_file(), "the approved baseline mechanism must exist to be usable"


def test_every_suppressed_finding_is_provably_a_digest_not_a_secret() -> None:
    """The baseline's "not a secret" claim is verified, not taken on trust.

    A baseline is the standard way to record verified false positives, and also
    the standard way to bury a real one. Every entry marked ``is_secret: false``
    must sit on a line that assigns a checksum or a commit SHA -- a field whose
    value is a digest by contract. Anything else stays blocking.
    """
    import re

    digest_line = re.compile(
        r'^\s*[-"]?\s*"?(?P<key>[A-Za-z_]*(?:sha256|commit_sha))"?\s*[:=]\s*"?[0-9a-f]{40,64}"?,?\s*$'
    )
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    suppressed = 0
    for filename, findings in baseline["results"].items():
        lines = (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines()
        for finding in findings:
            if finding.get("is_secret") is not False:
                continue
            suppressed += 1
            line = lines[finding["line_number"] - 1]
            assert digest_line.match(line), (
                f"{filename}:{finding['line_number']} is marked not-a-secret but is not a "
                f"checksum or commit-SHA assignment: {line.strip()!r}"
            )
    assert suppressed > 0, "no suppressions to verify; drop this test if the baseline is empty"


def test_no_finding_is_left_unaudited() -> None:
    """An unaudited entry is an unreviewed suppression."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    for filename, findings in baseline["results"].items():
        for finding in findings:
            assert "is_secret" in finding, (
                f"{filename}:{finding['line_number']} is in the baseline but was never audited"
            )


def test_secret_scan_fails_on_an_injected_credential(tmp_path: Path) -> None:
    """A scanner that has never rejected anything is not known to work.

    The credential is assembled at runtime rather than written as a literal.
    The first full-gate run of EP-05 found this test's original literal form
    and failed on it -- correctly: a tracked file containing a credential-shaped
    string is exactly what the scan exists to reject, and "it is only there to
    test the scanner" is the argument every such string comes with. Suppressing
    it in the baseline would have been the weakening HARNESS.md section 7
    forbids, so the literal was removed instead. The file the scanner is
    actually pointed at still contains the full credential, which is what the
    test needs to prove.
    """
    leak = tmp_path / "leaked.env"
    credential = "wJalrXUtnFEMI" + "/K7MDENG/" + "bPxRfiCYEXAMPLEKEY"
    leak.write_text(f'aws_secret_access_key = "{credential}"\n', encoding="utf-8")
    completed = subprocess.run(
        ["uv", "run", "detect-secrets-hook", "--baseline", ".secrets.baseline", str(leak)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1, (
        f"the secret scan accepted a credential: {completed.stdout}{completed.stderr}"
    )
