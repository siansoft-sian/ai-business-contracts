"""Evidence-integrity tests (``TEST_PLAN.md`` Layer G).

Evidence is the one artifact a milestone verdict rests on entirely, and it was
the last one in this repository with no checker. EP-00 finding 9 recorded an
evidence file silently reverting to its ``NOT RUN`` template in the working
tree; nothing would have caught that.

As everywhere else here, the control test comes first and the injection tests
carry the weight: asserting that today's evidence happens to be well-formed
proves little about a checker that might accept anything.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))

import check_evidence  # noqa: E402


@pytest.fixture
def evidence_clone(tmp_path: Path) -> Path:
    """A real clone, because the checks resolve commits against git history."""
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(REPO_ROOT), str(clone)],
        check=True,
        capture_output=True,
    )
    # Carry over any evidence not yet committed, so the fixture reflects the
    # tree under test rather than the last commit.
    for name in check_evidence.REQUIRED_REPORTS:
        source = REPO_ROOT / "evidence" / name
        if source.is_file():
            shutil.copy(source, clone / "evidence" / name)
    for name in ("DELIVERY_REPORT.md", "evidence/EVIDENCE_INDEX.md"):
        source = REPO_ROOT / name
        if source.is_file():
            shutil.copy(source, clone / name)
    return clone


def _patterns(root: Path) -> set[str]:
    violations, _ = check_evidence.scan(root)
    return {violation.pattern for violation in violations}


# --- the repository's own evidence ----------------------------------------


def test_repository_evidence_is_complete() -> None:
    """The control. Every injection test below is meaningless without it."""
    violations, _ = check_evidence.scan(REPO_ROOT)
    assert violations == [], "\n".join(v.render() for v in violations)


def test_every_required_report_exists() -> None:
    for name in check_evidence.REQUIRED_REPORTS:
        assert (REPO_ROOT / "evidence" / name).is_file(), f"{name} is missing"


# --- a report that was never run ------------------------------------------


def test_a_report_reverted_to_its_template_is_rejected(evidence_clone: Path) -> None:
    """EP-00 finding 9, made into a gate."""
    (evidence_clone / "evidence" / "04-compatibility.md").write_text(
        "# Evidence — Compatibility Validation\n\nStatus: **NOT RUN**\n",
        encoding="utf-8",
    )
    assert "not-run" in _patterns(evidence_clone)


def test_a_missing_report_is_rejected(evidence_clone: Path) -> None:
    (evidence_clone / "evidence" / "03-contract-validation.md").unlink()
    assert "missing-report" in _patterns(evidence_clone)


def test_remaining_template_placeholders_are_rejected(evidence_clone: Path) -> None:
    path = evidence_clone / "evidence" / "02-boundary.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n- Commit SHA: `<sha>`\n", encoding="utf-8")
    assert "placeholder" in _patterns(evidence_clone)


# --- claims that cannot be checked out ------------------------------------


def test_an_unreachable_commit_is_rejected(evidence_clone: Path) -> None:
    """Evidence must describe a state someone can actually check out.

    A well-formed but fabricated SHA is the easiest way to write evidence that
    reads as rigorous and verifies nothing.
    """
    path = evidence_clone / "evidence" / "02-boundary.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n- Also audited: `" + "0" * 40 + "`\n",
        encoding="utf-8",
    )
    assert "unreachable-commit" in _patterns(evidence_clone)


@pytest.mark.parametrize(
    ("stripped", "pattern"),
    [
        ("commit", "no-commit"),
        ("timestamp", "no-timestamp"),
        ("commands", "no-commands"),
        ("exit", "no-exit-codes"),
    ],
)
def test_a_report_missing_a_required_element_is_rejected(
    evidence_clone: Path, stripped: str, pattern: str
) -> None:
    """HARNESS.md section 7 requires all four for every blocking gate."""
    minimal = {
        "commit": "Status: **PASS**\n\n2026-08-08T00:00:00Z\n\n```\ncmd\n```\n\nexit 0\n",
        "timestamp": "Status: **PASS**\n\n`" + "a" * 40 + "`\n\n```\ncmd\n```\n\nexit 0\n",
        "commands": "Status: **PASS**\n\n`" + "a" * 40 + "`\n\n2026-08-08T00:00:00Z\n\nexit 0\n",
        "exit": "Status: **PASS**\n\n`" + "a" * 40 + "`\n\n2026-08-08T00:00:00Z\n\n```\ncmd\n```\n",
    }[stripped]
    # Use the real HEAD so the commit check does not fire for the wrong reason.
    head = check_evidence.head_sha(evidence_clone)
    (evidence_clone / "evidence" / "07-cross-repo-readiness.md").write_text(
        minimal.replace("a" * 40, head), encoding="utf-8"
    )
    assert pattern in _patterns(evidence_clone)


# --- recorded digests -----------------------------------------------------


def test_a_falsified_artifact_digest_is_rejected(evidence_clone: Path) -> None:
    """Only re-checkable at the recorded commit, so the report must name HEAD."""
    head = check_evidence.head_sha(evidence_clone)
    (evidence_clone / "evidence" / "06-release-artifacts.md").write_text(
        f"""Status: **PASS**

- Commit SHA: `{head}`
- Timestamp UTC: `2026-08-08T00:00:00Z`

```
./scripts/quality_gate.sh
```

Exit code: `0`

| Artifact | SHA-256 |
|---|---|
| `README.md` | `{"0" * 64}` |
""",
        encoding="utf-8",
    )
    assert "hash-mismatch" in _patterns(evidence_clone)


def test_a_digest_recorded_at_an_older_commit_is_not_falsely_rejected(
    evidence_clone: Path,
) -> None:
    """A hash recorded earlier describes a different artifact, not a lie.

    Re-checking it against today's file would manufacture failures; ignoring
    the distinction entirely would verify nothing. Only HEAD-recorded digests
    are re-verified.
    """
    _, parent = check_evidence._git(evidence_clone, "rev-parse", "HEAD~1")
    (evidence_clone / "evidence" / "06-release-artifacts.md").write_text(
        f"""Status: **PASS**

- Commit SHA: `{parent}`
- Timestamp UTC: `2026-08-08T00:00:00Z`

```
./scripts/quality_gate.sh
```

Exit code: `0`

| Artifact | SHA-256 |
|---|---|
| `README.md` | `{"0" * 64}` |
""",
        encoding="utf-8",
    )
    assert "hash-mismatch" not in _patterns(evidence_clone)


# --- the audit verdict ----------------------------------------------------


def test_a_failing_audit_verdict_is_not_absorbed(evidence_clone: Path) -> None:
    path = evidence_clone / "evidence" / "08-audit-verdict.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Verdict: PASS", "Verdict: FAIL"), encoding="utf-8"
    )
    assert "audit-failed" in _patterns(evidence_clone)


def test_an_audit_that_skips_a_criterion_is_rejected(evidence_clone: Path) -> None:
    """A criterion omitted from an audit reads as audited-and-fine."""
    path = evidence_clone / "evidence" / "08-audit-verdict.md"
    path.write_text(path.read_text(encoding="utf-8").replace("M0-CON-042", "M0-CON-0XX"), encoding="utf-8")
    assert "criterion-not-audited" in _patterns(evidence_clone)


def test_a_missing_audit_verdict_is_rejected(evidence_clone: Path) -> None:
    (evidence_clone / "evidence" / "08-audit-verdict.md").unlink()
    assert {"missing-report", "missing-audit"} & _patterns(evidence_clone)


# --- the delivery report --------------------------------------------------


def test_a_delivery_verdict_that_does_not_follow_is_rejected(evidence_clone: Path) -> None:
    """``TEST_PLAN.md`` Layer G: the verdict must be *derivable*.

    An overall PASS printed above a table containing a FAIL is the single most
    likely way for a milestone to be delivered green while being red.
    """
    path = evidence_clone / "DELIVERY_REPORT.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text + "\n| M0-CON-003 | FAIL | boundary scan regressed |\n", encoding="utf-8")
    assert "underivable-verdict" in _patterns(evidence_clone)


def test_a_delivery_summary_that_does_not_add_up_is_rejected(evidence_clone: Path) -> None:
    """Arithmetic that does not add up is how criteria go missing unnoticed.

    A summary claiming 5 passed in a range holding 8 reads as complete and is
    not; nothing else in the report would reveal the shortfall.
    """
    path = evidence_clone / "DELIVERY_REPORT.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "| M0-CON-010..017 | 8 | 0 | 0 |", "| M0-CON-010..017 | 5 | 0 | 0 |"
        ),
        encoding="utf-8",
    )
    assert "summary-does-not-add-up" in _patterns(evidence_clone)


def test_the_index_may_not_still_advertise_a_report_as_not_run(evidence_clone: Path) -> None:
    path = evidence_clone / "evidence" / "EVIDENCE_INDEX.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n| `09-extra.md` | something | NOT RUN |\n",
        encoding="utf-8",
    )
    assert "index-not-run" in _patterns(evidence_clone)


def test_index_rows_mentioning_a_not_run_criterion_are_not_flagged(evidence_clone: Path) -> None:
    """Only the status column decides.

    Rows legitimately record which criteria were NOT RUN at the EP they
    describe; reading that as a report status would flag accurate history.
    """
    path = evidence_clone / "evidence" / "EVIDENCE_INDEX.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n| `09-extra.md` | M0-CON-999 was NOT RUN at that EP | COMPLETE |\n",
        encoding="utf-8",
    )
    assert "index-not-run" not in _patterns(evidence_clone)
