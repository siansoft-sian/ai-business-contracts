"""Reference resolution from a clean checkout.

Maps to ``M0-CON-016`` and ``M0-CON-029`` (unresolvable references fail
validation).

The cross-schema references are the point: the error and event envelopes
``$ref`` identifier definitions owned by ``request-metadata.v1``. If those did
not resolve, a consumer cloning a release could not interpret the contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import check_references
from _contracts import build_registry, load_schemas
from conftest import REPO_ROOT

DIALECT = "https://json-schema.org/draft/2020-12/schema"

BASE: dict[str, Any] = {
    "$schema": DIALECT,
    "$id": "urn:ai-business:contracts:common:base:v1",
    "title": "Base",
    "x-contract-version": "0.1.0",
    "type": "object",
    "additionalProperties": False,
    "$defs": {"token": {"type": "string", "pattern": "^t_[a-z0-9]+$"}},
}


def _write(root: Path, family: str, filename: str, document: dict[str, Any]) -> None:
    path = root / "contracts" / "schemas" / family / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")


def test_repository_references_resolve() -> None:
    assert check_references.main([]) == 0


def test_cross_schema_references_are_real() -> None:
    """The envelopes genuinely depend on request-metadata, not on copies."""
    for relative in (
        "contracts/schemas/common/error-envelope.v1.schema.json",
        "contracts/schemas/events/event-envelope.v1.schema.json",
    ):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "urn:ai-business:contracts:common:request-metadata:v1#/$defs/request_id" in text
        assert "urn:ai-business:contracts:common:request-metadata:v1#/$defs/correlation_id" in text


def test_registry_resolves_every_declared_id() -> None:
    schemas = load_schemas(REPO_ROOT)
    registry = build_registry(schemas)
    for document in schemas.values():
        resolved = registry.resolver().lookup(document["$id"])
        assert resolved.contents["$id"] == document["$id"]


def test_no_network_reference_is_used() -> None:
    """Every ``$ref`` target is a local URN, never an http(s) URL."""
    for path, document in load_schemas(REPO_ROOT).items():
        for _, ref in check_references._iter_refs(document):
            target = ref.partition("#")[0]
            assert not target.startswith(("http://", "https://")), f"{path.name}: network ref {ref!r}"


# --- negative -------------------------------------------------------------


def test_valid_pair_resolves(tmp_path: Path) -> None:
    _write(tmp_path, "common", "base.v1.schema.json", BASE)
    _write(
        tmp_path,
        "common",
        "user.v1.schema.json",
        {
            **BASE,
            "$id": "urn:ai-business:contracts:common:user:v1",
            "$defs": {},
            "properties": {"token": {"$ref": "urn:ai-business:contracts:common:base:v1#/$defs/token"}},
        },
    )
    assert check_references.scan(tmp_path) == []


def test_unresolvable_urn_is_rejected(tmp_path: Path) -> None:
    """A ``$ref`` to a URN no local schema declares fails (``M0-CON-029``)."""
    _write(
        tmp_path,
        "common",
        "user.v1.schema.json",
        {
            **BASE,
            "$id": "urn:ai-business:contracts:common:user:v1",
            "$defs": {},
            "properties": {"token": {"$ref": "urn:ai-business:contracts:common:absent:v1#/$defs/token"}},
        },
    )

    violations = check_references.scan(tmp_path)

    assert any(v.pattern == "unresolvable-ref" for v in violations)
    assert check_references.main(["--root", str(tmp_path)]) == 1


def test_dangling_cross_schema_pointer_is_rejected(tmp_path: Path) -> None:
    """The URN resolves but the fragment does not exist."""
    _write(tmp_path, "common", "base.v1.schema.json", BASE)
    _write(
        tmp_path,
        "common",
        "user.v1.schema.json",
        {
            **BASE,
            "$id": "urn:ai-business:contracts:common:user:v1",
            "$defs": {},
            "properties": {"token": {"$ref": "urn:ai-business:contracts:common:base:v1#/$defs/absent"}},
        },
    )

    violations = check_references.scan(tmp_path)

    assert any(v.pattern == "dangling-cross-ref" for v in violations)
    assert check_references.main(["--root", str(tmp_path)]) == 1


def test_dangling_local_pointer_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "common",
        "base.v1.schema.json",
        {**BASE, "properties": {"token": {"$ref": "#/$defs/absent"}}},
    )

    violations = check_references.scan(tmp_path)

    assert any(v.pattern == "dangling-local-ref" for v in violations)
    assert check_references.main(["--root", str(tmp_path)]) == 1


@pytest.mark.parametrize("fragment", ["#/$defs/token", "#/properties/token", "#"])
def test_pointer_resolution_accepts_valid_fragments(fragment: str) -> None:
    document = {**BASE, "properties": {"token": {"type": "string"}}}
    assert check_references._resolve_pointer(document, fragment.lstrip("#"))
