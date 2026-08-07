"""Structural assertions for criteria whose evidence was previously prose only.

Several acceptance criteria are satisfied by documents rather than by code:
the canonical directory layout, the README's statement of purpose, the
versioning and change-process policies, the dependency-audit blocking rule.
Through EP-04 those were verified by reading and recorded in evidence files.

That is weaker than it looks. EP-00 finding 9 established that only committed
evidence is evidence -- a document can be reverted, truncated, or replaced by a
skeleton, and no gate would notice. These tests make the structural half of
those claims machine-checked, so a regression fails the build instead of
quietly invalidating an evidence file written weeks earlier.

They assert *structure and required content*, not wording. A test that pinned
prose would fail on every edit and teach people to edit the test.
"""

from __future__ import annotations

import pytest

from conftest import REPO_ROOT

#: The canonical layout from TARGET_REPOSITORY_TREE.md.
CANONICAL_DIRECTORIES: tuple[str, ...] = (
    "contracts/openapi",
    "contracts/asyncapi",
    "contracts/schemas/common",
    "contracts/schemas/events",
    "contracts/examples/common",
    "contracts/examples/events",
    "catalog",
    "compatibility",
    "compatibility/fixtures/compatible",
    "compatibility/fixtures/breaking",
    "governance",
    "templates",
    "scripts",
    "tests",
    "dist",
    "evidence",
    ".github/workflows",
)

GOVERNANCE_DOCUMENTS: tuple[str, ...] = (
    "governance/CONTRACT_POLICY.md",
    "governance/VERSIONING.md",
    "governance/CHANGE_PROCESS.md",
    "governance/DEPRECATION.md",
    "governance/OWNERSHIP.md",
    "governance/RELEASES.md",
)

FROZEN_REPOSITORIES: tuple[str, ...] = (
    "ai-business-contracts",
    "ai-business-database",
    "ai-business-auth",
    "ai-business-api",
    "ai-business-agent-runtime",
    "ai-business-channel-gateway",
    "ai-business-admin-web",
    "ai-business-infrastructure",
)


def _text(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _prose(relative: str) -> str:
    """Return the document with whitespace collapsed, lowercased.

    Phrase assertions must survive rewrapping and block-quoting. Matching raw
    text would make these tests fail when a paragraph is reflowed, which
    teaches people to edit the test rather than to keep the claim true.
    """
    lines = [line.lstrip("> ") for line in _text(relative).splitlines()]
    return " ".join(" ".join(lines).split()).lower()


# --- M0-CON-010: canonical directories ------------------------------------


@pytest.mark.parametrize("relative", CANONICAL_DIRECTORIES)
def test_canonical_directory_exists(relative: str) -> None:
    assert (REPO_ROOT / relative).is_dir(), f"{relative} is required by TARGET_REPOSITORY_TREE.md"


# --- M0-CON-001: stated purpose -------------------------------------------


def test_readme_states_the_repository_is_contracts_only() -> None:
    readme = _prose("README.md")
    assert "contracts and governance only" in readme
    assert "no shared business implementation" in readme


def test_readme_states_the_platform_has_no_multi_tenancy() -> None:
    assert "multi-tenant" in _prose("README.md")


# --- M0-CON-002: ownership without collapsed responsibilities -------------


@pytest.mark.parametrize("repository", FROZEN_REPOSITORIES)
def test_ownership_document_names_every_frozen_repository(repository: str) -> None:
    assert repository in _text("governance/OWNERSHIP.md")


def test_database_contract_authority_is_not_absorbed_into_this_repository() -> None:
    """The boundary HARNESS.md section 3.4 forbids relocating."""
    ownership = _text("governance/OWNERSHIP.md")
    assert "ai-business-database" in ownership
    assert "stored-function" in ownership or "stored function" in ownership


# --- M0-CON-020 / 021: versioning and change process ----------------------


@pytest.mark.parametrize("relative", GOVERNANCE_DOCUMENTS)
def test_governance_document_is_complete_not_a_skeleton(relative: str) -> None:
    text = _text(relative)
    assert len(text.splitlines()) > 20, f"{relative} looks like a skeleton"
    assert "<placeholder" not in text.lower()
    assert "tbd" not in text.lower()


@pytest.mark.parametrize("term", ["MAJOR", "MINOR", "PATCH"])
def test_versioning_policy_defines_each_semver_class(term: str) -> None:
    assert term in _text("governance/VERSIONING.md")


@pytest.mark.parametrize(
    "stage",
    ["proposal", "review", "compatibility", "consumer impact", "release", "deprecation", "retirement"],
)
def test_change_process_covers_every_required_stage(stage: str) -> None:
    """M0-CON-021 enumerates the stages; each must actually be addressed."""
    process = _text("governance/CHANGE_PROCESS.md").lower()
    deprecation = _text("governance/DEPRECATION.md").lower()
    assert stage in process or stage in deprecation, f"{stage} is not covered by the change process"


# --- M0-CON-035: documented dependency-audit blocking policy --------------


def test_security_policy_documents_the_dependency_audit_blocking_rule() -> None:
    security = _prose("SECURITY.md")
    assert "pip-audit" in security
    assert "blocking" in security
    assert "no fix available" in security or "fixed version available" in security, (
        "the policy must say what happens when a fix is and is not available"
    )


def test_security_policy_documents_the_secret_baseline_mechanism() -> None:
    security = _prose("SECURITY.md")
    assert ".secrets.baseline" in security
    assert "false-positive" in security or "false positive" in security
