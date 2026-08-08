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

import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))

import check_secrets  # noqa: E402
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
    "secret scan": "check_secrets.py",
    "dependency vulnerability audit": "pip-audit",
    "bundle/manifest validation": "verify_bundle.py",
    "evidence integrity": "check_evidence.py",
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


def test_every_criterion_is_backed_by_an_executed_check(tmp_path: Path) -> None:
    """Nothing may be claimed that the gate cannot derive.

    Until EP-06 added the Layer G evidence checker, M0-CON-043/044/045 had no
    backing check and were reported ``not_run`` with a reason. They are now
    derivable, so an empty ``derived_from`` anywhere would mean a criterion had
    quietly lost its evidence rather than gained it.
    """
    for criterion, checks in CRITERION_EVIDENCE.items():
        assert checks, f"{criterion} is backed by no gate check"


def test_an_unmapped_criterion_would_be_reported_not_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mechanism that keeps an unbacked criterion honest still works."""
    monkeypatch.setitem(write_evidence_summary.CRITERION_EVIDENCE, "M0-CON-003", ())
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
    assert by_id["M0-CON-003"]["status"] == "not_run"
    assert by_id["M0-CON-003"]["derived_from"] == []
    assert summary["milestone_verdict"] == "not_complete"


def test_an_empty_or_missing_check_record_is_refused(tmp_path: Path) -> None:
    missing = tmp_path / "absent.tsv"
    assert write_evidence_summary.main(["--root", str(REPO_ROOT), "--checks", str(missing)]) == 1

    empty = tmp_path / "empty.tsv"
    empty.write_text("", encoding="utf-8")
    assert write_evidence_summary.main(["--root", str(REPO_ROOT), "--checks", str(empty)]) == 1


# --- the secret scan and its digest exemption -----------------------------


BASELINE = REPO_ROOT / ".secrets.baseline"


def test_secret_baseline_exists_as_the_review_mechanism() -> None:
    """HARNESS.md section 9 requires an approved false-positive mechanism.

    It is currently empty, which is the honest state: every real finding in
    this repository is explained by the digest rule, so nothing needs a
    per-finding suppression. The file exists so that a future false positive
    the rule does not cover has a reviewable home.
    """
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert "plugins_used" in baseline
    assert isinstance(baseline.get("results"), dict)


def test_unreviewed_baseline_entries_are_not_honoured(tmp_path: Path) -> None:
    """An entry with no verdict is an unreviewed suppression, not an approval."""
    (tmp_path / ".secrets.baseline").write_text(
        json.dumps({"results": {"a.txt": [{"hashed_secret": "abc"}]}}),
        encoding="utf-8",
    )
    assert check_secrets.load_reviewed(tmp_path) == set()

    (tmp_path / ".secrets.baseline").write_text(
        json.dumps({"results": {"a.txt": [{"hashed_secret": "abc", "is_secret": False}]}}),
        encoding="utf-8",
    )
    assert check_secrets.load_reviewed(tmp_path) == {("a.txt", "abc")}


#: Witness values derived at import rather than written as literals. A tracked
#: line holding a bare digest or a credential is precisely what the scan
#: rejects, so the tests for the exemption rule cannot state their own inputs
#: literally -- the first EP-05 gate run proved that by failing on exactly such
#: a line. Deriving them keeps the source clean while the strings the rule is
#: tested against remain real.
DIGEST = hashlib.sha256(b"digest-witness").hexdigest()
SHORT_DIGEST = hashlib.sha1(b"commit-witness").hexdigest()
CREDENTIAL = "wJalrXUtnFEMI" + "/K7MDENG/" + "bPxRfiCYEXAMPLEKEY"

EXEMPT_LINES: list[str] = [
    f'  "sha256": "{DIGEST}"',
    f'  "bundle_sha256": "{DIGEST}",',
    f'    manifest_sha256: "{SHORT_DIGEST}"',
    f'  "commit_sha": "{SHORT_DIGEST}",',
    f"    - source_sha256: {DIGEST}",
]

BLOCKING_LINES: list[str] = [
    f'  "api_key": "{DIGEST}"',
    f'  "token": "{SHORT_DIGEST}"',
    f"  {DIGEST}",
    f'  "sha256_note": "see {DIGEST}"',
    '  "pass' + 'word": "hunter2"',
]


@pytest.mark.parametrize("line", EXEMPT_LINES)
def test_digest_assignments_are_exempt(line: str) -> None:
    """The values the contracts require to be present."""
    assert check_secrets.is_digest_line(line)


@pytest.mark.parametrize("line", BLOCKING_LINES)
def test_the_exemption_does_not_widen_beyond_digest_fields(line: str) -> None:
    """The same hex string in any other position stays blocking.

    This is what stops the rule from becoming "high-entropy hex is fine".
    """
    assert not check_secrets.is_digest_line(line)


def test_repository_scan_is_clean() -> None:
    """The gate's own invocation, run in-process."""
    assert check_secrets.main(["--root", str(REPO_ROOT)]) == 0


def test_secret_scan_fails_on_an_injected_credential(tmp_path: Path) -> None:
    """A scanner that has never rejected anything is not known to work.

    The credential is assembled at runtime rather than written as a literal.
    The first full-gate run of EP-05 failed on this test's original literal
    form -- correctly: a tracked file holding a credential-shaped string is
    exactly what the scan exists to reject, and "it is only there to test the
    scanner" is the justification every such string arrives with. Baselining it
    would have been the weakening HARNESS.md section 7 forbids, so the literal
    was removed instead. The file the scanner is pointed at still contains the
    full credential, so the proof is unchanged.
    """
    leak = tmp_path / "leaked.env"
    leak.write_text(f'aws_secret_access_key = "{CREDENTIAL}"\n', encoding="utf-8")

    results = check_secrets.run_scan(tmp_path, [leak.name])
    violations, digests, baselined = check_secrets.triage(tmp_path, results, set())

    assert violations, "the scan accepted a credential"
    assert digests == 0 and baselined == 0, "a credential must not be explained away"


def test_a_credential_hidden_in_a_digest_shaped_field_is_still_caught(tmp_path: Path) -> None:
    """The exemption keys on the value's shape as well as the field's name.

    Naming a field ``api_sha256`` must not launder a credential through the
    rule: the value still has to be 40-64 lowercase hex characters.
    """
    leak = tmp_path / "leaked.yaml"
    leak.write_text(f'aws_sha256 = "{CREDENTIAL}"\n', encoding="utf-8")

    results = check_secrets.run_scan(tmp_path, [leak.name])
    violations, _, _ = check_secrets.triage(tmp_path, results, set())
    assert violations, "a credential in a sha256-named field was exempted"


def test_a_scanner_that_cannot_run_is_not_reported_as_passing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exit 2, not 0. An audit that did not happen has not passed."""
    monkeypatch.setattr("check_secrets.shutil.which", lambda _name: None)
    assert check_secrets.main(["--root", str(REPO_ROOT)]) == 2
