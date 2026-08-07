"""Consumer pinning and the platform matrix.

Maps to ``M0-CON-002``, ``M0-CON-023``, ``M0-CON-040``–``M0-CON-042`` and
``TEST_PLAN.md`` Layer F.

EP-04 instruction 4 names four negative cases: version mismatch, checksum
mismatch, unknown required contract ID, and incorrect authority declaration.
Each has a test below that asserts the *specific* mismatch is reported, not
merely that verification failed.

The framing throughout is **fail closed**. A gate that resolved a version
mismatch by taking the newer artifact, or that accepted a lock it could not
parse, would report success while verifying nothing.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

import validate_matrix
import verify_consumer_lock
from _contracts import FROZEN_REPOSITORIES, load_schemas, load_yaml
from conftest import REPO_ROOT

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "cross-repo"
MANIFEST = FIXTURES / "manifest-0.1.0.json"
MATRIX_PATH = REPO_ROOT / "compatibility" / "platform-m0-matrix.yaml"
LOCK_TEMPLATE = REPO_ROOT / "templates" / "consumer-contract-lock.yaml"


def _verify(lock_name: str) -> list[Any]:
    lock = yaml.safe_load((FIXTURES / f"{lock_name}.yaml").read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return verify_consumer_lock.verify(lock, manifest)


def _cli(lock_name: str) -> int:
    return verify_consumer_lock.main(
        ["--lock", str(FIXTURES / f"{lock_name}.yaml"), "--manifest", str(MANIFEST)]
    )


# --- the lock template (M0-CON-023) --------------------------------------


def test_lock_template_exists_and_is_data_not_code() -> None:
    """EP-04 instruction 5: no consumer runtime SDK.

    The check is on the template's *data*, not its prose. The commentary
    legitimately mentions SDKs and imports in order to say there are none, so
    searching the whole file for those words would flag the very sentence that
    states the rule.
    """
    assert LOCK_TEMPLATE.is_file()
    text = LOCK_TEMPLATE.read_text(encoding="utf-8")

    document = yaml.safe_load(text)
    assert set(document) <= {"consumer", "dependencies"}, "the lock carries data only"
    assert set(document["dependencies"]) == {"ai-business-contracts"}
    assert document["dependencies"]["ai-business-contracts"]["source"] == "release"

    # No installation or import directive anywhere, in data or commentary.
    for directive in ("pip install", "npm install", "require(", "import ", "$ "):
        assert directive not in text, f"template contains an installation directive: {directive!r}"


def test_lock_template_placeholders_are_obvious() -> None:
    """A template committed unedited must not look like a valid lock."""
    text = LOCK_TEMPLATE.read_text(encoding="utf-8")
    assert "<" in text and ">" in text

    document = yaml.safe_load(text)
    schemas = load_schemas(REPO_ROOT)
    from _contracts import build_registry, validator_for

    schema = next(
        doc
        for doc in schemas.values()
        if doc.get("$id") == "urn:ai-business:contracts:common:consumer-lock:v1"
    )
    errors = list(validator_for(schema, build_registry(schemas)).iter_errors(document))
    assert errors, "the unedited template must fail validation, or a placeholder could ship"


def test_valid_lock_verifies() -> None:
    """Control case: every negative differs from this in exactly one field."""
    assert _verify("lock-valid") == []
    assert _cli("lock-valid") == 0


# --- EP-04 instruction 4: the four required negatives ---------------------


def test_version_mismatch_fails_closed() -> None:
    findings = _verify("lock-version-mismatch")

    assert any(f.pattern == "version-mismatch" for f in findings)
    assert _cli("lock-version-mismatch") == 1


def test_checksum_mismatch_fails_closed() -> None:
    """Right version, wrong bytes. The version agreeing is not enough."""
    findings = _verify("lock-checksum-mismatch")

    assert any(f.pattern == "bundle-checksum-mismatch" for f in findings)
    assert _cli("lock-checksum-mismatch") == 1


def test_unknown_required_contract_fails_closed() -> None:
    findings = _verify("lock-unknown-required-contract")

    assert any(f.pattern == "unknown-required-contract" for f in findings)
    assert _cli("lock-unknown-required-contract") == 1


def test_incorrect_authority_declaration_fails_closed(tmp_path: Path) -> None:
    """The fourth required negative: an authority claim that is not frozen."""
    shutil.copytree(REPO_ROOT / "contracts", tmp_path / "contracts")
    (tmp_path / "compatibility").mkdir()
    matrix = load_yaml(MATRIX_PATH)

    # ai-business-admin-web claims business authority, which belongs to the API.
    for entry in matrix["repositories"]:
        if entry["repository"] == "ai-business-admin-web":
            entry["authority"] = ["business-authority"]

    (tmp_path / "compatibility" / "platform-m0-matrix.yaml").write_text(
        yaml.safe_dump(matrix, sort_keys=False), encoding="utf-8"
    )

    violations = validate_matrix.scan(tmp_path)

    assert any(v.pattern in {"shared-authority", "wrong-authority"} for v in violations)
    assert any(v.pattern == "unowned-authority" for v in violations), (
        "admin-presentation is now unclaimed and that must also be reported"
    )
    assert validate_matrix.main(["--root", str(tmp_path)]) == 1


# --- further pinning negatives -------------------------------------------


def test_mutable_source_is_rejected() -> None:
    """``M0-CON-023``: a mutable branch may not be a production dependency."""
    assert _cli("lock-mutable-source") == 1


def test_floating_range_is_rejected() -> None:
    """A range lets the dependency move without the lock moving."""
    assert _cli("lock-floating-range") == 1


def test_manifest_digest_can_be_verified_against_the_file() -> None:
    """manifest_sha256 is checked against the manifest's real bytes."""
    lock = yaml.safe_load((FIXTURES / "lock-valid.yaml").read_text(encoding="utf-8"))
    pin = lock["dependencies"]["ai-business-contracts"]

    findings = verify_consumer_lock.verify_manifest_checksum(MANIFEST, pin)

    # The fixture carries a synthetic digest, so this must be reported.
    assert any(f.pattern == "manifest-checksum-mismatch" for f in findings)

    pin["manifest_sha256"] = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert verify_consumer_lock.verify_manifest_checksum(MANIFEST, pin) == []


def test_all_findings_are_reported_not_just_the_first() -> None:
    """A consumer fixing a stale lock should see everything wrong at once."""
    lock = yaml.safe_load((FIXTURES / "lock-version-mismatch.yaml").read_text(encoding="utf-8"))
    lock["dependencies"]["ai-business-contracts"]["bundle_sha256"] = "0" * 64
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    findings = verify_consumer_lock.verify(lock, manifest)

    patterns = {f.pattern for f in findings}
    assert {"version-mismatch", "bundle-checksum-mismatch"} <= patterns


# --- the platform matrix (M0-CON-040) ------------------------------------


def test_repository_matrix_is_valid() -> None:
    assert validate_matrix.main([]) == 0


def test_matrix_lists_all_eight_repositories_exactly_once() -> None:
    entries = load_yaml(MATRIX_PATH)["repositories"]
    listed = [entry["repository"] for entry in entries]

    assert len(listed) == 8
    assert set(listed) == FROZEN_REPOSITORIES
    assert len(set(listed)) == len(listed)


@pytest.mark.parametrize(
    ("role", "expected_owner"),
    sorted(validate_matrix.EXCLUSIVE_ROLES.items()),
)
def test_each_authority_role_is_held_by_its_frozen_owner(role: str, expected_owner: str) -> None:
    """EP-04 instruction 3, one assertion per frozen authority note."""
    entries = load_yaml(MATRIX_PATH)["repositories"]
    holders = [e["repository"] for e in entries if role in e.get("authority", [])]

    assert holders == [expected_owner], f"{role} is held by {holders}, expected [{expected_owner}]"


def test_database_contract_authority_is_not_absorbed_here() -> None:
    """``M0-CON-005`` at the matrix level: this repository never owns DB contracts."""
    entries = {e["repository"]: e for e in load_yaml(MATRIX_PATH)["repositories"]}

    assert "database-contracts" not in entries["ai-business-contracts"]["authority"]
    assert entries["ai-business-database"]["authority"] == ["database-contracts"]


def test_admin_web_and_agent_runtime_have_no_direct_datastore_path() -> None:
    """Frozen boundary: neither reaches business data directly."""
    entries = {e["repository"]: e for e in load_yaml(MATRIX_PATH)["repositories"]}

    assert entries["ai-business-admin-web"]["direct_datastore_access"] == "forbidden"
    assert entries["ai-business-agent-runtime"]["direct_datastore_access"] == "forbidden"
    assert entries["ai-business-admin-web"]["contract_provider"] is False


def test_authority_is_expressed_as_roles_not_technologies() -> None:
    """The matrix sits on the scanned release surface (EP-01 finding 6).

    The technology-level frozen notes belong in governance/OWNERSHIP.md; naming
    them here would trip the boundary gate and blur the ownership line the
    matrix exists to draw.
    """
    text = MATRIX_PATH.read_text(encoding="utf-8").lower()
    for technology in ("asyncpg", "pgbouncer", "sqitch", "langgraph", "fastapi", "react", "terraform"):
        assert technology not in text, f"matrix names {technology!r}; put it in governance/OWNERSHIP.md"

    ownership = (REPO_ROOT / "governance" / "OWNERSHIP.md").read_text(encoding="utf-8").lower()
    for technology in ("asyncpg", "pgbouncer", "sqitch", "langgraph"):
        assert technology in ownership, f"{technology!r} must still be recorded off-surface"


# --- matrix negatives -----------------------------------------------------


@pytest.fixture
def matrix_copy(tmp_path: Path) -> Path:
    shutil.copytree(REPO_ROOT / "contracts", tmp_path / "contracts")
    shutil.copytree(REPO_ROOT / "compatibility", tmp_path / "compatibility")
    return tmp_path


def _write_matrix(root: Path, document: dict[str, Any]) -> None:
    (root / "compatibility" / "platform-m0-matrix.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )


def test_unmutated_matrix_copy_is_valid(matrix_copy: Path) -> None:
    assert validate_matrix.scan(matrix_copy) == []


def test_missing_repository_is_rejected(matrix_copy: Path) -> None:
    matrix = load_yaml(MATRIX_PATH)
    matrix["repositories"] = [e for e in matrix["repositories"] if e["repository"] != "ai-business-auth"]
    _write_matrix(matrix_copy, matrix)

    violations = validate_matrix.scan(matrix_copy)

    assert any(v.pattern == "missing-repository" for v in violations)
    assert validate_matrix.main(["--root", str(matrix_copy)]) == 1


def test_duplicate_repository_is_rejected(matrix_copy: Path) -> None:
    matrix = load_yaml(MATRIX_PATH)
    matrix["repositories"].append(dict(matrix["repositories"][0]))
    _write_matrix(matrix_copy, matrix)

    violations = validate_matrix.scan(matrix_copy)

    assert any(v.pattern in {"duplicate-repository", "schema-invalid"} for v in violations)


def test_shared_authority_is_rejected(matrix_copy: Path) -> None:
    """Two claimants for one role is a boundary collapse."""
    matrix = load_yaml(MATRIX_PATH)
    for entry in matrix["repositories"]:
        if entry["repository"] == "ai-business-auth":
            entry["authority"] = ["authentication", "business-authority"]
    _write_matrix(matrix_copy, matrix)

    violations = validate_matrix.scan(matrix_copy)

    assert any(v.pattern == "shared-authority" for v in violations)


def test_datastore_boundary_violation_is_rejected(matrix_copy: Path) -> None:
    matrix = load_yaml(MATRIX_PATH)
    for entry in matrix["repositories"]:
        if entry["repository"] == "ai-business-admin-web":
            entry["direct_datastore_access"] = "permitted"
    _write_matrix(matrix_copy, matrix)

    violations = validate_matrix.scan(matrix_copy)

    assert any(v.pattern == "datastore-boundary" for v in violations)
    assert validate_matrix.main(["--root", str(matrix_copy)]) == 1


def test_unknown_repository_is_rejected(matrix_copy: Path) -> None:
    matrix = load_yaml(MATRIX_PATH)
    matrix["repositories"][0]["repository"] = "ai-business-billing"
    _write_matrix(matrix_copy, matrix)

    violations = validate_matrix.scan(matrix_copy)

    assert any(v.pattern in {"unknown-repository", "schema-invalid"} for v in violations)
