"""Catalog integrity: ownership, uniqueness, and agreement with the tree.

Maps to ``M0-CON-014``, ``M0-CON-015``, ``M0-CON-029`` and ``TEST_PLAN.md``
Layer C.

The negative cases run against a copy of the real repository in ``tmp_path``,
mutating the catalog there. That keeps the real catalog untouched while still
exercising the validator against a realistic tree rather than a toy one.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

import validate_catalog
from _contracts import FROZEN_REPOSITORIES, load_catalog, schema_paths
from conftest import REPO_ROOT

EXPECTED_CONTRACT_IDS = {
    "urn:ai-business:contracts:common:error-envelope:v1",
    "urn:ai-business:contracts:common:request-metadata:v1",
    "urn:ai-business:contracts:common:contract-metadata:v1",
    "urn:ai-business:contracts:events:event-envelope:v1",
    "urn:ai-business:contracts:common:compatibility-result:v1",
    "urn:ai-business:contracts:common:consumer-lock:v1",
    "urn:ai-business:contracts:common:release-manifest:v1",
    "urn:ai-business:contracts:common:platform-matrix:v1",
}


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    """A copy of the release surface plus catalog, safe to mutate."""
    for relative in ("contracts", "catalog"):
        shutil.copytree(REPO_ROOT / relative, tmp_path / relative)
    return tmp_path


def _write_catalog(root: Path, document: dict[str, Any]) -> None:
    (root / "catalog" / "contract-catalog.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )


def test_repository_catalog_is_valid() -> None:
    assert validate_catalog.main([]) == 0


def test_every_foundation_contract_is_registered() -> None:
    entries = load_catalog(REPO_ROOT)["contracts"]
    assert {entry["contract_id"] for entry in entries} == EXPECTED_CONTRACT_IDS


def test_every_entry_has_exactly_one_owner() -> None:
    for entry in load_catalog(REPO_ROOT)["contracts"]:
        owner = entry["owner"]
        assert isinstance(owner, str), "owner must be a single repository, not a list"
        assert owner in FROZEN_REPOSITORIES


def test_contract_id_and_version_tuples_are_unique() -> None:
    entries = load_catalog(REPO_ROOT)["contracts"]
    tuples = [(entry["contract_id"], entry["version"]) for entry in entries]
    assert len(tuples) == len(set(tuples))


def test_consumers_are_frozen_repositories() -> None:
    for entry in load_catalog(REPO_ROOT)["contracts"]:
        assert set(entry["consumers"]) <= FROZEN_REPOSITORIES


def test_source_paths_exist_and_checksums_are_computable() -> None:
    """``M0-CON-038`` depends on this being true before the manifest is built."""
    for entry in load_catalog(REPO_ROOT)["contracts"]:
        source = REPO_ROOT / entry["source"]
        assert source.is_file(), f"{entry['contract_id']}: {entry['source']} missing"
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        assert len(digest) == 64


def test_catalog_and_tree_agree() -> None:
    """Every schema on disk is registered, and every registration is real."""
    registered = {(REPO_ROOT / e["source"]).resolve() for e in load_catalog(REPO_ROOT)["contracts"]}
    on_disk = {p.resolve() for p in schema_paths(REPO_ROOT)}
    assert registered == on_disk


def test_catalog_versions_are_the_m0_baseline() -> None:
    """``HARNESS.md`` section 5: the initial foundation release is 0.1.0."""
    catalog = load_catalog(REPO_ROOT)
    assert catalog["catalog_version"] == "0.1.0"
    for entry in catalog["contracts"]:
        assert entry["version"] == "0.1.0"
        assert entry["lifecycle"] == "active"
        assert entry["compatibility"] == "backward"


# --- negative -------------------------------------------------------------


def test_unmutated_copy_is_valid(repo_copy: Path) -> None:
    """Baseline, so each negative below isolates one defect."""
    assert validate_catalog.scan(repo_copy) == []


def test_duplicate_contract_id_and_version_is_rejected(repo_copy: Path) -> None:
    """``M0-CON-029``: duplicate (contract_id, version) fails validation."""
    catalog = load_catalog(repo_copy)
    catalog["contracts"].append(dict(catalog["contracts"][0]))
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "duplicate-entry" for v in violations)
    assert validate_catalog.main(["--root", str(repo_copy)]) == 1


def test_unknown_owner_is_rejected(repo_copy: Path) -> None:
    catalog = load_catalog(repo_copy)
    catalog["contracts"][0]["owner"] = "ai-business-billing"
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern in {"owner", "schema-invalid"} for v in violations)
    assert validate_catalog.main(["--root", str(repo_copy)]) == 1


def test_missing_source_file_is_rejected(repo_copy: Path) -> None:
    catalog = load_catalog(repo_copy)
    catalog["contracts"][0]["source"] = "contracts/schemas/common/absent.v1.schema.json"
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "missing-source" for v in violations)
    assert validate_catalog.main(["--root", str(repo_copy)]) == 1


def test_uncatalogued_contract_is_rejected(repo_copy: Path) -> None:
    """A contract added to the tree but never registered must fail.

    This is the drift a schema alone cannot catch: the file would ship in a
    bundle with no owner and no declared consumers.
    """
    source = REPO_ROOT / "contracts/schemas/common/error-envelope.v1.schema.json"
    target = repo_copy / "contracts/schemas/common/orphan.v1.schema.json"
    document = source.read_text(encoding="utf-8").replace("common:error-envelope:v1", "common:orphan:v1")
    target.write_text(document, encoding="utf-8")

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "uncatalogued-contract" for v in violations)
    assert validate_catalog.main(["--root", str(repo_copy)]) == 1


def test_catalog_id_must_match_source_id(repo_copy: Path) -> None:
    """A catalog entry cannot claim an identity its source does not declare."""
    catalog = load_catalog(repo_copy)
    catalog["contracts"][0]["contract_id"] = "urn:ai-business:contracts:common:mislabelled:v1"
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "id-mismatch" for v in violations)


def test_source_version_must_match_catalog_version(repo_copy: Path) -> None:
    """Closes the divergence flagged at EP-02 and escalated at EP-03.

    check_compatibility.py reads x-contract-version from the SOURCE to decide
    whether a breaking change is covered by a major bump. If the source and the
    catalog disagreed, a breaking change could appear approved while the
    catalog still advertised the old version.
    """
    import json

    schema_path = repo_copy / "contracts/schemas/common/error-envelope.v1.schema.json"
    document = json.loads(schema_path.read_text(encoding="utf-8"))
    document["x-contract-version"] = "0.2.0"
    schema_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "version-mismatch" for v in violations)
    assert validate_catalog.main(["--root", str(repo_copy)]) == 1


def test_unknown_key_is_rejected(repo_copy: Path) -> None:
    """The closed control-plane schema rejects a misspelled key."""
    catalog = load_catalog(repo_copy)
    entry = catalog["contracts"][0]
    entry["complatibility"] = entry.pop("compatibility")
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "schema-invalid" for v in violations)
    assert validate_catalog.main(["--root", str(repo_copy)]) == 1


def test_deprecated_entry_requires_deprecation_metadata(repo_copy: Path) -> None:
    catalog = load_catalog(repo_copy)
    catalog["contracts"][0]["lifecycle"] = "deprecated"
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "deprecation-metadata" for v in violations)


def test_active_entry_rejects_deprecation_metadata(repo_copy: Path) -> None:
    """Deprecation metadata on an active contract is a contradiction."""
    catalog = load_catalog(repo_copy)
    catalog["contracts"][0]["deprecation"] = {"deprecated_at": "2026-08-01"}
    _write_catalog(repo_copy, catalog)

    violations = validate_catalog.scan(repo_copy)

    assert any(v.pattern == "deprecation-metadata" for v in violations)


def test_missing_catalog_is_rejected(tmp_path: Path) -> None:
    violations = validate_catalog.scan(tmp_path)
    assert any(v.pattern == "load-error" for v in violations)
