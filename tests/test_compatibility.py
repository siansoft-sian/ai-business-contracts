"""Compatibility engine: classification, approval, and result shape.

Maps to ``M0-CON-024``–``M0-CON-029`` and ``TEST_PLAN.md`` Layer D.

Every fixture under ``compatibility/fixtures/`` is a curated baseline/candidate
pair whose expected class is its parent directory. The tests assert not just
the verdict but the specific change class, so a fixture cannot pass by failing
for an unrelated reason.

``test_every_mandatory_layer_d_case_has_a_fixture`` is the guard that matters
most: it fails when a case named in ``TEST_PLAN.md`` has no fixture, so
coverage cannot quietly regress by deleting a directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import check_compatibility
from _contracts import build_registry, load_schemas, validator_for
from conftest import REPO_ROOT

FIXTURE_ROOT = REPO_ROOT / "compatibility" / "fixtures"
RESULT_SCHEMA = REPO_ROOT / "contracts/schemas/common/compatibility-result.v1.schema.json"
STAMP = "2026-08-07T19:00:00Z"

#: Every mandatory case in TEST_PLAN.md Layer D, mapped to its fixture and the
#: change class the engine must report. Deleting a fixture fails the coverage
#: test rather than silently reducing what is proven.
MANDATORY_CASES = {
    # Compatible
    "compatible/add-optional-property": "field-added-optional",
    "compatible/add-optional-response-metadata": "field-added-optional",
    "compatible/documentation-only": "documentation-only",
    "compatible/add-new-contract-id": "contract-added",
    # Breaking
    "breaking/remove-field": "field-removed",
    "breaking/rename-field": "field-renamed",
    "breaking/type-change-string-to-integer": "type-changed",
    "breaking/optional-input-becomes-required": "optional-became-required",
    "breaking/remove-enum-value": "enum-value-removed",
    "breaking/tighten-regex": "pattern-changed",
    "breaking/narrow-numeric-range": "range-narrowed",
    "breaking/unresolvable-reference": "unresolvable-reference",
    "breaking/duplicate-contract-version": "duplicate-contract-version",
    "breaking/extensible-becomes-closed": "extensible-became-closed",
    "breaking/released-version-content-changed": "released-version-content-changed",
    "breaking/removal-approved-by-major-bump": "field-removed",
    # Review required
    "review-required/enum-expansion": "enum-value-added",
    "review-required/new-variant-for-exhaustive-matchers": "enum-value-added",
    "review-required/regex-changed-without-witness": "pattern-changed",
}

#: Fixtures whose verdict differs from their directory, and why.
VERDICT_OVERRIDES = {
    # A breaking change declared by a MAJOR bump passes: it was announced,
    # not hidden. The finding is still listed.
    "breaking/removal-approved-by-major-bump": "pass",
}


def _run(case: str) -> dict[str, Any]:
    directory = FIXTURE_ROOT / case
    result = check_compatibility.compare(directory / "baseline", directory / "candidate")
    return result.as_document(STAMP)


def _classes(document: dict[str, Any], bucket: str) -> set[str]:
    return {finding["change"] for finding in document[bucket]}


def _expected_verdict(case: str) -> str:
    if case in VERDICT_OVERRIDES:
        return VERDICT_OVERRIDES[case]
    return {"compatible": "pass", "breaking": "fail", "review-required": "review_required"}[
        case.split("/")[0]
    ]


def _expected_bucket(case: str) -> str:
    return {
        "compatible": "compatible",
        "breaking": "breaking",
        "review-required": "review_required",
    }[case.split("/")[0]]


# --- coverage -------------------------------------------------------------


def test_every_mandatory_layer_d_case_has_a_fixture() -> None:
    """A missing mandatory case must fail, not silently reduce coverage."""
    for case in MANDATORY_CASES:
        directory = FIXTURE_ROOT / case
        assert (directory / "baseline").is_dir(), f"{case}: no baseline"
        assert (directory / "candidate").is_dir(), f"{case}: no candidate"
        assert (directory / "README.md").is_file(), f"{case}: undocumented fixture"


def test_no_undeclared_fixtures() -> None:
    """Every fixture on disk is declared, so none goes untested."""
    on_disk = {
        f"{case.parent.name}/{case.name}"
        for case in FIXTURE_ROOT.glob("*/*")
        if case.is_dir()
    }
    assert on_disk == set(MANDATORY_CASES), f"undeclared: {on_disk - set(MANDATORY_CASES)}"


def test_all_three_classes_are_represented() -> None:
    classes = {case.split("/")[0] for case in MANDATORY_CASES}
    assert classes == {"compatible", "breaking", "review-required"}


# --- classification -------------------------------------------------------


@pytest.mark.parametrize("case", sorted(MANDATORY_CASES), ids=lambda c: c.replace("/", "::"))
def test_fixture_is_classified_correctly(case: str) -> None:
    """Verdict and change class both match what the fixture is for."""
    document = _run(case)

    assert document["result"] == _expected_verdict(case), (
        f"{case}: expected {_expected_verdict(case)}, got {document['result']}"
    )

    bucket = _expected_bucket(case)
    assert MANDATORY_CASES[case] in _classes(document, bucket), (
        f"{case}: expected change {MANDATORY_CASES[case]!r} in {bucket}, "
        f"got {_classes(document, bucket)}"
    )


@pytest.mark.parametrize(
    "case", sorted(c for c in MANDATORY_CASES if c.startswith("compatible/"))
)
def test_compatible_fixtures_report_nothing_breaking(case: str) -> None:
    """A compatible change must not produce a breaking or review finding."""
    document = _run(case)
    assert document["breaking"] == []
    assert document["review_required"] == []


@pytest.mark.parametrize(
    "case", sorted(c for c in MANDATORY_CASES if c.startswith("review-required/"))
)
def test_review_required_fixtures_are_not_called_compatible(case: str) -> None:
    """Additive is not automatically safe (HARNESS.md section 6)."""
    document = _run(case)
    assert document["breaking"] == []
    assert document["review_required"], f"{case}: escalation was expected"
    assert document["result"] == "review_required"


# --- the interesting individual behaviours --------------------------------


def test_tightened_regex_is_proven_by_a_witness() -> None:
    """An undecidable change earns 'breaking' only with a counter-example.

    ``ref_zz99`` is declared valid by the baseline's own examples and is
    rejected by the candidate's pattern, which is what makes the verdict a
    demonstration rather than a guess.
    """
    document = _run("breaking/tighten-regex")

    finding = next(f for f in document["breaking"] if f["change"] == "pattern-changed")
    assert finding["witness"] == "ref_zz99"
    assert "ref_zz99" not in "^ref_[a-z0-9]{8,32}$"


def test_regex_change_without_a_witness_is_escalated_not_cleared() -> None:
    """No counter-example means undecidable, which is never 'compatible'."""
    document = _run("review-required/regex-changed-without-witness")

    finding = next(
        f for f in document["review_required"] if f["change"] == "pattern-changed"
    )
    assert "witness" not in finding
    assert document["compatible"] == []


def test_major_version_bump_approves_but_still_lists_breaking_changes() -> None:
    """``CONTRACT_STANDARD.md`` section 8: declared, not hidden."""
    document = _run("breaking/removal-approved-by-major-bump")

    assert document["result"] == "pass"
    assert document["approved_major_transition"] is True
    assert document["breaking"], "an approved breaking change must still be reported"


def test_same_change_without_a_major_bump_fails() -> None:
    """The identical removal, shipped as MINOR, is not approved."""
    approved = _run("breaking/removal-approved-by-major-bump")
    unapproved = _run("breaking/remove-field")

    assert _classes(approved, "breaking") == _classes(unapproved, "breaking")
    assert approved["result"] == "pass"
    assert unapproved["result"] == "fail"
    assert unapproved["approved_major_transition"] is False


def test_rename_is_reported_once_as_breaking_not_as_a_compatible_addition() -> None:
    """A rename must not be split into a removal plus a harmless addition."""
    document = _run("breaking/rename-field")

    assert _classes(document, "breaking") == {"field-renamed"}
    assert document["compatible"] == []


def test_immutability_violation_is_detected() -> None:
    """``M0-CON-022``: a released version's content can never change."""
    document = _run("breaking/released-version-content-changed")

    assert "released-version-content-changed" in _classes(document, "breaking")
    assert document["result"] == "fail"


def test_version_only_change_is_not_reported_as_documentation() -> None:
    """Bumping a version without touching prose is not a doc change."""
    document = _run("compatible/add-new-contract-id")
    assert "documentation-only" not in _classes(document, "compatible")


# --- baseline declaration -------------------------------------------------


def test_no_baseline_is_reported_explicitly_not_as_a_pass() -> None:
    """EP-03 instruction 7, and the fail-closed rule in CROSS_REPO_COMPATIBILITY.

    With no release published there is nothing to compare. Reporting 'pass'
    would read as "compared and found compatible", which would be false.
    """
    declaration = check_compatibility.load_baseline_declaration(REPO_ROOT)

    assert declaration["baseline_release"] is None
    assert declaration["first_published_baseline"] == "0.1.0"

    result = check_compatibility.Result(baseline=None, candidate="0.1.0", no_baseline=True)
    document = result.as_document(STAMP)

    assert document["result"] == "no-baseline"
    assert document["result"] != "pass"
    assert check_compatibility.main(["--checked-at", STAMP]) == 0


# --- result document shape ------------------------------------------------


@pytest.mark.parametrize("case", sorted(MANDATORY_CASES), ids=lambda c: c.replace("/", "::"))
def test_emitted_document_validates_against_its_contract(case: str) -> None:
    """The engine cannot drift from CONTRACT_STANDARD.md section 8.

    The result document is itself a governed contract, so the platform gate
    validates what it consumes instead of trusting our output shape.
    """
    schemas = load_schemas(REPO_ROOT)
    schema = schemas[RESULT_SCHEMA]
    validator = validator_for(schema, build_registry(schemas))

    errors = list(validator.iter_errors(_run(case)))

    assert not errors, f"{case}: {[e.message for e in errors]}"


def test_result_document_has_the_standard_keys() -> None:
    document = _run("compatible/add-optional-property")
    assert set(document) >= {
        "baseline",
        "candidate",
        "result",
        "breaking",
        "review_required",
        "compatible",
        "checked_at_utc",
    }


def test_cli_exit_codes_follow_the_verdict(tmp_path: Path) -> None:
    """Exit code is the contract CI branches on."""
    for case, expected_exit in (
        ("compatible/add-optional-property", 0),
        ("review-required/enum-expansion", 0),
        ("breaking/remove-field", 1),
        ("breaking/removal-approved-by-major-bump", 0),
    ):
        directory = FIXTURE_ROOT / case
        output = tmp_path / f"{case.replace('/', '_')}.json"
        code = check_compatibility.main(
            [
                "--baseline", str(directory / "baseline"),
                "--candidate", str(directory / "candidate"),
                "--checked-at", STAMP,
                "--output", str(output),
            ]
        )
        assert code == expected_exit, f"{case}: expected exit {expected_exit}, got {code}"
        assert json.loads(output.read_text())["checked_at_utc"] == STAMP


def test_output_is_deterministic_for_a_fixed_timestamp(tmp_path: Path) -> None:
    """Same inputs and stamp produce byte-identical output.

    EP-05 needs this: a release artifact that changes between builds cannot be
    checksummed meaningfully.
    """
    directory = FIXTURE_ROOT / "breaking/remove-field"
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    for output in (first, second):
        check_compatibility.main(
            [
                "--baseline", str(directory / "baseline"),
                "--candidate", str(directory / "candidate"),
                "--checked-at", STAMP,
                "--output", str(output),
            ]
        )
    assert first.read_text() == second.read_text()


def test_mismatched_arguments_are_rejected() -> None:
    """--baseline without --candidate is a usage error, not a silent pass."""
    assert check_compatibility.main(["--baseline", str(FIXTURE_ROOT)]) == 2
