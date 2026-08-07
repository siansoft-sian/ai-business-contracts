"""Committed examples validate; invalid fixtures fail for the intended reason.

Maps to ``M0-CON-017`` and ``TEST_PLAN.md`` Layer B.

The invalid fixtures are driven by ``tests/fixtures/invalid/manifest.yaml``,
which declares for each one the schema, the JSON pointer where the error must
surface, and a substring the message must contain. Asserting the *reason* — not
merely that validation failed — is what stops a fixture from silently drifting
onto a different rule than the one it claims to cover.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import validate_examples
from _contracts import build_registry, example_paths, load_json, load_schemas, validator_for
from conftest import REPO_ROOT

INVALID_DIR = REPO_ROOT / "tests" / "fixtures" / "invalid"
MANIFEST = INVALID_DIR / "manifest.yaml"


def _manifest_entries() -> list[dict[str, str]]:
    document = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return list(document["fixtures"])


def _validate(instance: Any, schema_relative: str) -> list[tuple[str, str]]:
    """Return ``(pointer, message)`` for each validation error."""
    schemas = load_schemas(REPO_ROOT)
    schema = schemas[REPO_ROOT / schema_relative]
    validator = validator_for(schema, build_registry(schemas))
    errors = []
    for error in validator.iter_errors(instance):
        pointer = "/".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append((pointer, error.message))
    return errors


def test_committed_examples_validate() -> None:
    assert validate_examples.main([]) == 0


def test_examples_exist_for_every_contract() -> None:
    """Every foundation schema ships at least one worked example."""
    covered = {p.name.split(".")[0] for p in example_paths(REPO_ROOT)}
    assert covered == {
        "error-envelope",
        "request-metadata",
        "contract-metadata",
        "event-envelope",
        "compatibility-result",
        "consumer-lock",
        "release-manifest",
        "platform-matrix",
    }


def test_examples_contain_no_realistic_personal_data() -> None:
    """``TEST_PLAN.md`` section 4: synthetic identifiers and example domains only."""
    for path in example_paths(REPO_ROOT):
        text = path.read_text(encoding="utf-8").lower()
        assert "@" not in text or "example.com" in text, f"{path.name} may contain a real address"
        for term in ("password", "secret", "token=", "bearer ", "api_key", "postgresql://"):
            assert term not in text, f"{path.name} contains {term!r}"


# --- negative: every invalid fixture fails, for its declared reason ------


def test_manifest_covers_every_invalid_fixture() -> None:
    """No fixture may sit on disk untested."""
    on_disk = {p.relative_to(INVALID_DIR).as_posix() for p in INVALID_DIR.rglob("*.json")}
    declared = {entry["file"] for entry in _manifest_entries()}
    assert on_disk == declared, f"undeclared: {on_disk - declared}; missing: {declared - on_disk}"


@pytest.mark.parametrize("entry", _manifest_entries(), ids=lambda e: e["file"].replace("/", "::"))
def test_invalid_fixture_fails_for_its_declared_reason(entry: dict[str, str]) -> None:
    instance = load_json(INVALID_DIR / entry["file"])

    errors = _validate(instance, entry["schema"])

    assert errors, f"{entry['file']} was accepted, but must fail: {entry['reason']}"

    at, expect = entry["at"], entry["expect"]
    matched = [
        (pointer, message)
        for pointer, message in errors
        if pointer == at and expect.lower() in message.lower()
    ]
    assert matched, (
        f"{entry['file']} failed, but not for the declared reason.\n"
        f"  expected at {at!r} containing {expect!r}\n"
        f"  actual: {errors}"
    )


def test_invalid_fixtures_are_outside_the_release_surface() -> None:
    """An invalid example must never ship as a contract example."""
    from _scope import is_in_scope

    for path in INVALID_DIR.rglob("*"):
        if path.is_file():
            assert not is_in_scope(path, REPO_ROOT), f"{path} is on the release surface"


def test_example_validator_rejects_a_bad_example(tmp_path: Path) -> None:
    """The validator itself fails when an example stops matching its contract."""
    for relative in (
        "contracts/schemas/common/error-envelope.v1.schema.json",
        "contracts/schemas/common/request-metadata.v1.schema.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO_ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")

    example = tmp_path / "contracts/examples/common/error-envelope.v1.broken.example.json"
    example.parent.mkdir(parents=True, exist_ok=True)
    example.write_text('{"success": false, "error": {"code": "lower_case"}}', encoding="utf-8")

    violations = validate_examples.scan(tmp_path)

    assert any(v.pattern == "example-invalid" for v in violations)
    assert validate_examples.main(["--root", str(tmp_path)]) == 1


def test_example_naming_convention_is_enforced(tmp_path: Path) -> None:
    """A misnamed example cannot silently skip validation."""
    schema_rel = "contracts/schemas/common/error-envelope.v1.schema.json"
    target = tmp_path / schema_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((REPO_ROOT / schema_rel).read_text(encoding="utf-8"), encoding="utf-8")

    example = tmp_path / "contracts/examples/common/whatever.example.json"
    example.parent.mkdir(parents=True, exist_ok=True)
    example.write_text("{}", encoding="utf-8")

    violations = validate_examples.scan(tmp_path)

    assert any(v.pattern in {"example-naming", "unknown-contract"} for v in violations)


def test_missing_examples_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "contracts" / "examples").mkdir(parents=True)
    violations = validate_examples.scan(tmp_path)
    assert any(v.pattern == "no-examples" for v in violations)
