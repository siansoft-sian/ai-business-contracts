"""Shared loading, reference resolution, and catalog access for the validators.

Contract schemas identify themselves by URN (``CONTRACT_STANDARD.md`` section
2), not by a resolvable URL. Nothing may be fetched from the network during
validation: every reference must resolve from a clean checkout
(``HARNESS.md`` section 4). So references are resolved through a
``referencing`` registry built from the ``$id`` of each local schema, and a
``$ref`` to a URN that no local schema declares is an error rather than a
lookup attempt.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012

SCHEMA_ROOT = "contracts/schemas"
EXAMPLE_ROOT = "contracts/examples"
CATALOG_PATH = "catalog/contract-catalog.yaml"

#: Suffix identifying a contract schema source file.
SCHEMA_SUFFIX = ".schema.json"

#: Suffix identifying a committed example.
EXAMPLE_SUFFIX = ".example.json"

#: The eight frozen platform repositories. Duplicated from
#: contract-metadata.v1's ``repository`` enum on purpose: the catalog
#: validator cross-checks the two, so a silent divergence between the schema
#: and the tooling is caught rather than assumed impossible.
FROZEN_REPOSITORIES: frozenset[str] = frozenset(
    {
        "ai-business-contracts",
        "ai-business-database",
        "ai-business-auth",
        "ai-business-api",
        "ai-business-agent-runtime",
        "ai-business-channel-gateway",
        "ai-business-admin-web",
        "ai-business-infrastructure",
    }
)


class ContractLoadError(Exception):
    """A contract source file could not be read or parsed."""


def schema_paths(root: Path) -> list[Path]:
    """Return every contract schema source file, sorted."""
    return sorted((root / SCHEMA_ROOT).rglob(f"*{SCHEMA_SUFFIX}"))


def example_paths(root: Path) -> list[Path]:
    """Return every committed example, sorted."""
    return sorted((root / EXAMPLE_ROOT).rglob(f"*{EXAMPLE_SUFFIX}"))


def relative_schema_name(path: Path) -> tuple[str, str]:
    """Split a schema filename into ``(name, major)``.

    ``error-envelope.v1.schema.json`` -> ``("error-envelope", "1")``.
    Raises ``ContractLoadError`` if the filename does not follow
    ``CONTRACT_STANDARD.md`` section 3.
    """
    if not path.name.endswith(SCHEMA_SUFFIX):
        raise ContractLoadError(f"{path}: not a contract schema filename")
    stem = path.name[: -len(SCHEMA_SUFFIX)]
    name, _, major = stem.rpartition(".")
    if not name or not major.startswith("v") or not major[1:].isdigit():
        raise ContractLoadError(f"{path}: expected '<name>.v<major>{SCHEMA_SUFFIX}'")
    return name, major[1:]


def load_json(path: Path) -> Any:
    """Parse a JSON file, raising ``ContractLoadError`` with the location."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractLoadError(f"{path}: invalid JSON at line {exc.lineno}: {exc.msg}") from exc
    except OSError as exc:
        raise ContractLoadError(f"{path}: unreadable: {exc}") from exc


def load_yaml(path: Path) -> Any:
    """Parse a YAML file, raising ``ContractLoadError`` with the location."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractLoadError(f"{path}: invalid YAML: {exc}") from exc
    except OSError as exc:
        raise ContractLoadError(f"{path}: unreadable: {exc}") from exc


def load_schemas(root: Path) -> dict[Path, dict[str, Any]]:
    """Load every contract schema, keyed by source path."""
    schemas: dict[Path, dict[str, Any]] = {}
    for path in schema_paths(root):
        document = load_json(path)
        if not isinstance(document, dict):
            raise ContractLoadError(f"{path}: schema root must be a JSON object")
        schemas[path] = document
    return schemas


def build_registry(schemas: dict[Path, dict[str, Any]]) -> Registry:
    """Build a reference registry from the ``$id`` of each local schema.

    Schemas without an ``$id`` are skipped here; ``validate_contracts.py``
    reports the missing identifier as its own violation rather than letting
    this fail obscurely.
    """
    contents: list[tuple[str, dict[str, Any]]] = []
    for document in schemas.values():
        schema_id = document.get("$id")
        if isinstance(schema_id, str) and schema_id:
            contents.append((schema_id, document))
    return Registry().with_contents(contents, default_specification=DRAFT202012)


def validator_for(schema: dict[str, Any], registry: Registry) -> Draft202012Validator:
    """Return a Draft 2020-12 validator bound to the local registry."""
    return Draft202012Validator(schema, registry=registry)


def schema_by_id(schemas: dict[Path, dict[str, Any]]) -> dict[str, tuple[Path, dict[str, Any]]]:
    """Index loaded schemas by ``$id``."""
    index: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path, document in schemas.items():
        schema_id = document.get("$id")
        if isinstance(schema_id, str) and schema_id:
            index[schema_id] = (path, document)
    return index


def example_schema_path(example: Path, root: Path) -> Path:
    """Map an example to the schema it must validate against.

    The mapping is by filename convention, so an example can never silently
    drift onto the wrong contract:

        contracts/examples/<family>/<name>.v<major>.<case>.example.json
            validates against
        contracts/schemas/<family>/<name>.v<major>.schema.json
    """
    stem = example.name[: -len(EXAMPLE_SUFFIX)]
    parts = stem.split(".")
    if len(parts) < 3 or not parts[1].startswith("v"):
        raise ContractLoadError(f"{example}: example name must be '<name>.v<major>.<case>{EXAMPLE_SUFFIX}'")
    name, major = parts[0], parts[1]
    family = example.parent.name
    return root / SCHEMA_ROOT / family / f"{name}.{major}{SCHEMA_SUFFIX}"


def load_catalog(root: Path) -> dict[str, Any]:
    """Load the contract catalog document."""
    path = root / CATALOG_PATH
    if not path.is_file():
        raise ContractLoadError(f"{CATALOG_PATH}: catalog not found")
    document = load_yaml(path)
    if not isinstance(document, dict):
        raise ContractLoadError(f"{CATALOG_PATH}: catalog root must be a mapping")
    return document
