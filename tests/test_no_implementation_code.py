"""Prove the implementation-boundary gate detects injected foreign code.

Maps to ``M0-CON-004`` / ``M0-CON-005`` and ``TEST_PLAN.md`` Layer A mutation
test 2 ("insert a FastAPI/LangGraph/database implementation file into a
guarded path -> gate must fail").

Each of the seven other frozen repositories is represented, so the gate is
proven against every ownership boundary it is supposed to defend rather than
against a single representative case.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import check_no_implementation_code
from _scope import is_in_scope
from conftest import REPO_ROOT, inject_into_repo, inject_into_temp_tree

# (fixture file, directory to inject into, expected pattern label)
# File-family violations are detected anywhere; content violations only on the
# release surface.
FILE_FAMILY_INJECTIONS = [
    ("migration.sql.fixture", "contracts/schemas/common", "sql-source"),
    ("migration.sql.fixture", "governance", "sql-source"),
    ("pgbouncer.ini.fixture", "contracts/schemas/common", "pgbouncer-config"),
    ("terraform-main.tf.fixture", "catalog", "terraform"),
    ("react-component.tsx.fixture", "templates", "react-component"),
    ("fastapi-router.py.fixture", "contracts/schemas/common", "python-on-release-surface"),
]

CONTENT_INJECTIONS = [
    ("asyncpg-pool.json.fixture", "contracts/schemas/common", "database-driver"),
    ("asyncpg-pool.json.fixture", "catalog", "database-driver"),
    ("tenant-header.yaml.fixture", "contracts/openapi", None),
]


def test_clean_repository_passes() -> None:
    """The real repository contains no prohibited implementation."""
    assert check_no_implementation_code.main([]) == 0


def test_clean_release_surface_passes(release_surface: Path) -> None:
    assert check_no_implementation_code.main(["--root", str(release_surface)]) == 0


@pytest.mark.parametrize(("fixture_name", "target_dir", "expected_label"), FILE_FAMILY_INJECTIONS)
def test_injected_file_family_fails_gate(
    release_surface: Path, fixture_name: str, target_dir: str, expected_label: str
) -> None:
    """A prohibited file family fails the gate."""
    inject_into_temp_tree(release_surface, fixture_name, target_dir)

    violations = check_no_implementation_code.scan(release_surface)

    assert violations, f"gate did not detect {fixture_name} in {target_dir}/"
    assert check_no_implementation_code.main(["--root", str(release_surface)]) == 1
    assert any(v.pattern == expected_label for v in violations), (
        f"expected {expected_label!r}, got {[v.pattern for v in violations]}"
    )


@pytest.mark.parametrize(("fixture_name", "target_dir", "expected_label"), CONTENT_INJECTIONS)
def test_injected_content_pattern_fails_gate(
    release_surface: Path, fixture_name: str, target_dir: str, expected_label: str | None
) -> None:
    """Implementation *content* on the release surface fails the gate."""
    inject_into_temp_tree(release_surface, fixture_name, target_dir)

    violations = check_no_implementation_code.scan(release_surface)

    if expected_label is None:
        # tenant-header.yaml carries no implementation construct; it is the
        # other scanner's business. Proves the checks are not interchangeable.
        assert not violations
        return

    assert violations, f"gate did not detect {fixture_name} in {target_dir}/"
    assert check_no_implementation_code.main(["--root", str(release_surface)]) == 1
    assert any(v.pattern == expected_label for v in violations)


def test_sql_is_rejected_anywhere_not_only_on_release_surface(release_surface: Path) -> None:
    """``M0-CON-005``: database source has no legitimate home in this repository."""
    inject_into_temp_tree(release_surface, "migration.sql.fixture", "governance")

    violations = check_no_implementation_code.scan(release_surface)

    assert any(v.pattern == "sql-source" for v in violations)
    assert any("governance" in v.path for v in violations), (
        "SQL outside the release surface must still fail; ai-business-database owns it"
    )


def test_content_patterns_do_not_fire_outside_release_surface(release_surface: Path) -> None:
    """Prose naming a prohibited construct is legal off the release surface.

    This is the false-positive class EP-00 identified: the governing documents
    must be able to say "no FastAPI routers" without failing their own gate.
    """
    (release_surface / "governance" / "OWNERSHIP.md").write_text(
        "ai-business-api owns FastAPI routers and use cases. "
        "ai-business-agent-runtime owns langgraph StateGraph nodes. "
        "ai-business-database owns asyncpg pooling through pgbouncer.\n",
        encoding="utf-8",
    )

    assert check_no_implementation_code.scan(release_surface) == []
    assert check_no_implementation_code.main(["--root", str(release_surface)]) == 0


@pytest.mark.parametrize(
    ("fixture_name", "expected_label"),
    [
        ("fastapi-router.py.fixture", "python-on-release-surface"),
        ("langgraph-node.py.fixture", "python-on-release-surface"),
        ("migration.sql.fixture", "sql-source"),
    ],
)
def test_injected_implementation_fails_in_real_guarded_path(
    fixture_name: str, expected_label: str
) -> None:
    """The default invocation guards the real ``contracts/`` directory."""
    assert check_no_implementation_code.main([]) == 0

    with inject_into_repo(fixture_name, "contracts/schemas/common") as injected:
        assert injected.is_file()
        violations = check_no_implementation_code.scan(REPO_ROOT)
        assert check_no_implementation_code.main([]) == 1, (
            f"gate passed while {fixture_name} sat in contracts/schemas/common/"
        )
        assert any(v.pattern == expected_label for v in violations)

    assert not injected.exists(), "mutation test leaked a prohibited file"
    assert check_no_implementation_code.main([]) == 0


def test_repository_tooling_is_not_flagged() -> None:
    """The scanners' own Python must not trip the Python-on-surface rule."""
    for script in (REPO_ROOT / "scripts").glob("*.py"):
        assert not is_in_scope(script, REPO_ROOT)
    for test in (REPO_ROOT / "tests").glob("*.py"):
        assert not is_in_scope(test, REPO_ROOT)

    assert check_no_implementation_code.main([]) == 0
