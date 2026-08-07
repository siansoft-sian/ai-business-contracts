"""Schema validity, identity, and extensibility policy.

Maps to ``M0-CON-011``–``M0-CON-014`` and ``TEST_PLAN.md`` Layer B.

The positive tests assert the four foundation schemas are well-formed. The
negative tests matter more: they inject a defective schema into a temp tree and
assert ``validate_contracts.py`` rejects it. Without those, a validator that
returned "pass" unconditionally would look identical from the outside.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

import validate_contracts
from _contracts import load_schemas, schema_paths
from conftest import REPO_ROOT

_URN = "urn:ai-business:contracts"

#: source path -> the $id it must declare.
#:
#: The four EP-02 primitives plus compatibility-result, added by EP-03 so the
#: platform gate validates the summary it consumes rather than trusting the
#: shape our tooling happens to emit.
FOUNDATION_SCHEMAS = {
    f"contracts/schemas/common/{name}.v1.schema.json": f"{_URN}:common:{name}:v1"
    for name in ("error-envelope", "request-metadata", "contract-metadata", "compatibility-result")
} | {
    "contracts/schemas/events/event-envelope.v1.schema.json": f"{_URN}:events:event-envelope:v1",
}

DIALECT = "https://json-schema.org/draft/2020-12/schema"

VALID_SCHEMA: dict[str, Any] = {
    "$schema": DIALECT,
    "$id": "urn:ai-business:contracts:common:probe:v1",
    "title": "Probe",
    "x-contract-version": "0.1.0",
    "type": "object",
    "properties": {"a": {"type": "string"}},
    "additionalProperties": False,
}


def _write_schema(root: Path, relative: str, document: dict[str, Any]) -> Path:
    path = root / "contracts" / "schemas" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def test_repository_schemas_are_valid() -> None:
    assert validate_contracts.main([]) == 0


def test_all_foundation_schemas_exist() -> None:
    """The declared contract set and the tree agree exactly."""
    present = {p.relative_to(REPO_ROOT).as_posix() for p in schema_paths(REPO_ROOT)}
    assert present == set(FOUNDATION_SCHEMAS)


@pytest.mark.parametrize(("relative", "expected_id"), sorted(FOUNDATION_SCHEMAS.items()))
def test_schema_identity(relative: str, expected_id: str) -> None:
    """Dialect, $id, title, and version metadata are present and stable."""
    document = json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))
    assert document["$schema"] == DIALECT
    assert document["$id"] == expected_id
    assert document["title"]
    assert document["x-contract-version"] == "0.1.0"


def test_schema_ids_are_unique() -> None:
    ids = [doc["$id"] for doc in load_schemas(REPO_ROOT).values()]
    assert len(ids) == len(set(ids))


def test_additional_properties_policy_is_explicit_and_intentional() -> None:
    """Envelopes are extensible; the control-plane schema is closed.

    This is the decision that sets the compatibility ceiling: an open envelope
    can gain a field in a MINOR release, while a closed catalog rejects a
    misspelled key instead of silently ignoring it.
    """
    schemas = {
        path.relative_to(REPO_ROOT).as_posix(): doc for path, doc in load_schemas(REPO_ROOT).items()
    }
    for relative in FOUNDATION_SCHEMAS:
        assert "additionalProperties" in schemas[relative], f"{relative} leaves the policy implicit"

    def policy(relative: str) -> object:
        return schemas[relative]["additionalProperties"]

    assert policy("contracts/schemas/common/error-envelope.v1.schema.json") is True
    assert policy("contracts/schemas/common/request-metadata.v1.schema.json") is True
    assert policy("contracts/schemas/events/event-envelope.v1.schema.json") is True
    assert policy("contracts/schemas/common/compatibility-result.v1.schema.json") is True
    assert policy("contracts/schemas/common/contract-metadata.v1.schema.json") is False


def test_contract_metadata_entry_is_closed() -> None:
    """A catalog entry rejects unknown keys, not just the catalog root."""
    document = json.loads(
        (REPO_ROOT / "contracts/schemas/common/contract-metadata.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert document["$defs"]["contract_entry"]["additionalProperties"] is False


#: Structural keywords whose values are dictated by the JSON Schema spec or by
#: CONTRACT_STANDARD.md. Their contents (the dialect URL, URN identifiers,
#: regexes) are not authored prose and must not be searched for vocabulary.
_STRUCTURAL_KEYWORDS = frozenset({"$schema", "$id", "$ref", "pattern", "format"})


def _authored_text(node: Any) -> list[str]:
    """Collect human-authored text: titles, descriptions, names, enum values."""
    collected: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _STRUCTURAL_KEYWORDS:
                continue
            collected.append(key)
            collected.extend(_authored_text(value))
    elif isinstance(node, list):
        for item in node:
            collected.extend(_authored_text(item))
    elif isinstance(node, str):
        collected.append(node)
    return collected


def test_no_business_rules_or_implementation_technology() -> None:
    """Primitives stay transport-neutral and free of business semantics.

    ``PROMPT.md`` section B: the foundation primitives "must not encode
    business rules". A field naming a concrete business entity or a specific
    technology would make every business change a contracts-repo change.

    Only authored text is searched. The dialect URL is ``https://...`` by
    specification, and URNs and regexes are structural, so scanning the raw
    JSON would flag the very identifiers the standard mandates.
    """
    forbidden = (
        "invoice", "customer", "order", "payment", "booking", "price", "tariff",
        "postgres", "kafka", "rabbitmq", "redis", "grpc", "graphql", "websocket",
    )
    for path, document in load_schemas(REPO_ROOT).items():
        haystack = " ".join(_authored_text(document)).lower()
        for term in forbidden:
            assert re.search(rf"\b{re.escape(term)}\b", haystack) is None, (
                f"{path.name} mentions {term!r} in authored text"
            )


# --- negative: the validator must reject defective schemas ---------------


def test_valid_probe_schema_passes(tmp_path: Path) -> None:
    """Baseline, so each negative below isolates one defect."""
    _write_schema(tmp_path, "common/probe.v1.schema.json", VALID_SCHEMA)
    assert validate_contracts.scan(tmp_path) == []


@pytest.mark.parametrize(
    ("mutation", "expected_pattern"),
    [
        ({"$schema": "http://json-schema.org/draft-07/schema#"}, "dialect"),
        ({"$id": None}, "missing-id"),
        ({"$id": "error-envelope-v1"}, "id-format"),
        ({"$id": "urn:ai-business:contracts:common:probe:v2"}, "id-filename-mismatch"),
        ({"title": None}, "missing-title"),
        ({"x-contract-version": "0.1"}, "version-metadata"),
        ({"x-contract-version": None}, "version-metadata"),
        ({"additionalProperties": None}, "implicit-additional-properties"),
        ({"type": {"not": "a type"}}, "meta-validation"),
    ],
)
def test_defective_schema_is_rejected(
    tmp_path: Path, mutation: dict[str, Any], expected_pattern: str
) -> None:
    """Each single defect is caught, and reported as the right defect."""
    document = dict(VALID_SCHEMA)
    for key, value in mutation.items():
        if value is None:
            document.pop(key, None)
        else:
            document[key] = value
    _write_schema(tmp_path, "common/probe.v1.schema.json", document)

    violations = validate_contracts.scan(tmp_path)

    assert violations, f"mutation {mutation} was not detected"
    assert any(v.pattern == expected_pattern for v in violations), (
        f"expected {expected_pattern!r}, got {[v.pattern for v in violations]}"
    )
    assert validate_contracts.main(["--root", str(tmp_path)]) == 1


def test_duplicate_schema_id_is_rejected(tmp_path: Path) -> None:
    """Two schemas cannot claim the same identity (``M0-CON-029``)."""
    _write_schema(tmp_path, "common/probe.v1.schema.json", VALID_SCHEMA)
    duplicate = dict(VALID_SCHEMA)
    _write_schema(tmp_path, "events/probe.v1.schema.json", duplicate)

    violations = validate_contracts.scan(tmp_path)

    assert any(v.pattern == "duplicate-id" for v in violations)
    assert validate_contracts.main(["--root", str(tmp_path)]) == 1


def test_malformed_filename_is_rejected(tmp_path: Path) -> None:
    _write_schema(tmp_path, "common/ErrorEnvelope.schema.json", VALID_SCHEMA)
    violations = validate_contracts.scan(tmp_path)
    assert any(v.pattern == "filename" for v in violations)


def test_unparseable_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "contracts" / "schemas" / "common" / "broken.v1.schema.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"$id": "urn:x", ', encoding="utf-8")

    violations = validate_contracts.scan(tmp_path)

    assert any(v.pattern == "parse-error" for v in violations)
    assert validate_contracts.main(["--root", str(tmp_path)]) == 1


def test_empty_schema_tree_is_rejected(tmp_path: Path) -> None:
    """An empty contracts/schemas/ is a failure, not a vacuous pass."""
    (tmp_path / "contracts" / "schemas").mkdir(parents=True)
    violations = validate_contracts.scan(tmp_path)
    assert any(v.pattern == "no-schemas" for v in violations)
