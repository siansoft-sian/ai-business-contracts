"""Shared fixtures and helpers for the boundary-scanner tests.

Two injection strategies are used, because they prove different things:

``inject_into_temp_tree``
    Builds a replica of the release surface under ``tmp_path`` and injects a
    violation there. Safe, parallelisable, and covers the full matrix of
    violation types without ever writing a prohibited construct into the real
    repository.

``inject_into_repo``
    Writes one violation into the *real* guarded path, runs the scanner with
    its default root, and removes the file in a ``finally`` block. This is the
    literal reading of ``TEST_PLAN.md`` Layer A ("insert ... into a fixture ->
    gate must fail") and is the only way to prove the default invocation
    guards the real directory rather than a replica of it.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "negative"

# The scanners import ``_scope`` as a top-level module.
sys.path.insert(0, str(SCRIPTS_DIR))


def fixture_source(name: str) -> str:
    """Return the text of a negative fixture, by its ``.fixture`` filename."""
    path = FIXTURES_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"missing negative fixture: {path}")
    return path.read_text(encoding="utf-8")


def real_name(fixture_name: str) -> str:
    """Strip the neutralising ``.fixture`` suffix: ``a.sql.fixture`` -> ``a.sql``."""
    if not fixture_name.endswith(".fixture"):
        raise ValueError(f"not a neutralised fixture name: {fixture_name}")
    return fixture_name[: -len(".fixture")]


@pytest.fixture
def release_surface(tmp_path: Path) -> Path:
    """A minimal replica of the release surface under ``tmp_path``."""
    for relative in (
        "contracts/schemas/common",
        "contracts/schemas/events",
        "contracts/examples/common",
        "contracts/openapi",
        "contracts/asyncapi",
        "catalog",
        "compatibility/fixtures/compatible",
        "templates",
        # Deliberately included: these must remain OUT of scanner scope.
        "governance",
        "evidence",
        "scripts",
        "tests/fixtures/negative",
    ):
        (tmp_path / relative).mkdir(parents=True, exist_ok=True)
    return tmp_path


def inject_into_temp_tree(root: Path, fixture_name: str, relative_dir: str) -> Path:
    """Copy a negative fixture into ``root/relative_dir`` under its real name."""
    target = root / relative_dir / real_name(fixture_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(fixture_source(fixture_name), encoding="utf-8")
    return target


@contextmanager
def inject_into_repo(fixture_name: str, relative_dir: str) -> Iterator[Path]:
    """Inject a negative fixture into the real repository, then always remove it.

    The target name is prefixed so a leaked file is unmistakably test debris
    rather than something that could be mistaken for real contract source.
    """
    target_dir = REPO_ROOT / relative_dir
    target = target_dir / f"__mutation_test__{real_name(fixture_name)}"
    created_dir = not target_dir.exists()
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(fixture_source(fixture_name), encoding="utf-8")
        yield target
    finally:
        target.unlink(missing_ok=True)
        if created_dir and target_dir.exists() and not any(target_dir.iterdir()):
            shutil.rmtree(target_dir, ignore_errors=True)
