"""Prove the multi-tenancy gate detects injected tenant constructs.

Maps to ``M0-CON-003`` and ``TEST_PLAN.md`` Layer A mutation test 1.

EP-00 observed that no tenant construct exists anywhere in the repository, and
explicitly refused to mark ``M0-CON-003`` as passing on that basis: an empty
set trivially contains no violation, which is not the same as detection. These
tests supply the missing half.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import check_no_multitenancy
from _scope import CONTRACT_BEARING_PATHS, is_in_scope, iter_scoped_files
from conftest import REPO_ROOT, inject_into_repo, inject_into_temp_tree

# (fixture file, directory to inject into, pattern label expected)
TENANT_INJECTIONS = [
    ("tenant-field.json.fixture", "contracts/schemas/common", "tenant-identifier"),
    ("tenant-field.json.fixture", "contracts/examples/common", "tenant-identifier"),
    ("tenant-header.yaml.fixture", "contracts/openapi", "tenant-header"),
    ("tenant-header.yaml.fixture", "catalog", "tenant-header"),
    ("tenant-field.json.fixture", "templates", "tenant-identifier"),
    ("tenant-field.json.fixture", "compatibility/fixtures/compatible", "tenant-identifier"),
]


def test_clean_repository_passes() -> None:
    """The real repository contains no prohibited tenant construct."""
    assert check_no_multitenancy.main([]) == 0


def test_clean_release_surface_passes(release_surface: Path) -> None:
    """An empty release surface is clean."""
    assert check_no_multitenancy.main(["--root", str(release_surface)]) == 0


@pytest.mark.parametrize(("fixture_name", "target_dir", "expected_label"), TENANT_INJECTIONS)
def test_injected_tenant_construct_fails_gate(
    release_surface: Path, fixture_name: str, target_dir: str, expected_label: str
) -> None:
    """Injecting a tenant construct into any release-surface directory fails the gate."""
    inject_into_temp_tree(release_surface, fixture_name, target_dir)

    violations = check_no_multitenancy.scan(release_surface)

    assert violations, f"gate did not detect {fixture_name} injected into {target_dir}/"
    assert check_no_multitenancy.main(["--root", str(release_surface)]) == 1
    assert any(v.pattern == expected_label for v in violations), (
        f"expected a {expected_label!r} violation, got {[v.pattern for v in violations]}"
    )
    assert all(target_dir in v.path for v in violations)


def test_injected_tenant_construct_fails_in_real_guarded_path() -> None:
    """The default invocation guards the real repository, not just a replica."""
    assert check_no_multitenancy.main([]) == 0

    with inject_into_repo("tenant-field.json.fixture", "contracts/schemas/common") as injected:
        assert injected.is_file()
        assert check_no_multitenancy.main([]) == 1, (
            "gate passed while a tenant field sat in contracts/schemas/common/"
        )

    assert not injected.exists(), "mutation test leaked a prohibited file"
    assert check_no_multitenancy.main([]) == 0


def test_negative_fixtures_are_outside_scanner_scope() -> None:
    """Test-only fixtures can never be scanned as contract source.

    This is the property that lets the fixtures exist on disk at all, and the
    reason no scanner ignore-list is needed.
    """
    fixtures_dir = REPO_ROOT / "tests" / "fixtures" / "negative"
    assert fixtures_dir.is_dir()

    for fixture in fixtures_dir.iterdir():
        assert not is_in_scope(fixture, REPO_ROOT), f"{fixture.name} is on the release surface"

    scoped = {p.resolve() for p in iter_scoped_files(REPO_ROOT)}
    assert not any(p.resolve() in scoped for p in fixtures_dir.iterdir())


def test_evidence_and_governance_are_outside_scanner_scope() -> None:
    """Documents that must name prohibited constructs stay out of scope.

    EP-00 measured the tenant-pattern match count rising 30 -> 36 -> 42 across
    its runs purely from evidence quoting its own scanner patterns. Positive
    scoping is what stops that from becoming a gate failure.
    """
    for relative in ("evidence", "execution-prompts", "governance", "scripts", "tests"):
        assert relative not in CONTRACT_BEARING_PATHS
        directory = REPO_ROOT / relative
        if directory.is_dir():
            assert not is_in_scope(directory / "any-file.md", REPO_ROOT)

    for document in ("PROMPT.md", "HARNESS.md", "TEST_PLAN.md", "CONTRACT_STANDARD.md"):
        assert not is_in_scope(REPO_ROOT / document, REPO_ROOT)


def test_no_neutralised_fixture_leaked_onto_release_surface() -> None:
    """No ``.fixture`` file has been moved into a contract-bearing path."""
    leaked = [p for p in iter_scoped_files(REPO_ROOT) if p.name.endswith(".fixture")]
    assert not leaked, f"negative fixtures leaked onto the release surface: {leaked}"
