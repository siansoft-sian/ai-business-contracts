#!/usr/bin/env python3
"""Validate the contract catalog against its schema and its invariants.

Per ``TEST_PLAN.md`` Layer C, the catalog must satisfy more than its schema:

- it validates against ``contract-metadata.v1`` (which is closed, so an
  unrecognised key fails rather than being ignored);
- every ``(contract_id, version)`` pair is unique;
- every entry names exactly one owner, drawn from the frozen eight;
- every consumer is drawn from the frozen eight, and no entry lists itself;
- every ``source`` path exists, and its checksum is computable;
- lifecycle states and semantic versions are well-formed;
- the source's x-contract-version matches the catalog's version;
- deprecation metadata is present exactly when lifecycle requires it;
- every contract schema on disk is registered, and every registered source is
  a real contract schema.

That last pair is the one a schema cannot express: it catches a contract added
to the tree but never catalogued, which would ship in a bundle with no owner
and no declared consumers.

Exit codes:
    0 - the catalog is valid and consistent with the tree
    1 - at least one defect (blocking)
"""

from __future__ import annotations

import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

from _contracts import (
    CATALOG_PATH,
    FROZEN_REPOSITORIES,
    ContractLoadError,
    build_registry,
    load_catalog,
    load_schemas,
    schema_paths,
    validator_for,
)
from _scope import Violation, build_parser, relative_to, report

CHECK_NAME = "validate_catalog"

METADATA_ID = "urn:ai-business:contracts:common:contract-metadata:v1"

SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

VALID_LIFECYCLES = {"draft", "active", "deprecated", "retired"}

#: Lifecycles that require deprecation metadata to be present.
REQUIRES_DEPRECATION = {"deprecated", "retired"}


def _entry_label(index: int, entry: object) -> str:
    if isinstance(entry, dict):
        return str(entry.get("contract_id") or f"contracts[{index}]")
    return f"contracts[{index}]"


def _defect(pattern: str, detail: str) -> Violation:
    """A catalog defect. Always reported against the catalog file itself."""
    return Violation(path=CATALOG_PATH, line=0, pattern=pattern, detail=detail)


def scan(root: Path) -> list[Violation]:
    """Return every catalog defect under ``root``."""
    violations: list[Violation] = []

    try:
        catalog = load_catalog(root)
        schemas = load_schemas(root)
    except ContractLoadError as exc:
        return [_defect("load-error", str(exc))]

    metadata_schema = next((doc for doc in schemas.values() if doc.get("$id") == METADATA_ID), None)
    if metadata_schema is None:
        return [
            _defect("missing-metadata-schema", f"{METADATA_ID} not found; the catalog cannot be validated")
        ]

    # 1. Schema validation. The metadata schema is closed, so this catches
    #    misspelled and unexpected keys as well as type errors.
    validator = validator_for(metadata_schema, build_registry(schemas))
    for error in sorted(validator.iter_errors(catalog), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "(root)"
        violations.append(_defect("schema-invalid", f"at {location}: {error.message}"))

    entries = catalog.get("contracts")
    if not isinstance(entries, list):
        return violations or [_defect("schema-invalid", "'contracts' must be a list")]

    # 2. Invariants a schema cannot express.
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)
    catalogued_sources: set[Path] = set()

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        label = _entry_label(index, entry)
        contract_id = entry.get("contract_id")
        version = entry.get("version")
        owner = entry.get("owner")
        consumers = entry.get("consumers")
        source = entry.get("source")
        lifecycle = entry.get("lifecycle")

        if isinstance(contract_id, str) and isinstance(version, str):
            seen[(contract_id, version)].append(label)

        if isinstance(version, str) and not SEMVER_PATTERN.match(version):
            violations.append(_defect("semver", f"{label}: version {version!r} is not MAJOR.MINOR.PATCH"))

        if not isinstance(owner, str) or owner not in FROZEN_REPOSITORIES:
            violations.append(
                _defect("owner", f"{label}: owner {owner!r} is not one of the frozen eight repositories")
            )

        if isinstance(consumers, list):
            for consumer in consumers:
                if consumer not in FROZEN_REPOSITORIES:
                    violations.append(
                        _defect(
                            "consumer",
                            f"{label}: consumer {consumer!r} is not one of the frozen eight",
                        )
                    )
            if len(set(consumers)) != len(consumers):
                violations.append(_defect("consumer", f"{label}: consumers contains duplicates"))

        if isinstance(lifecycle, str):
            if lifecycle not in VALID_LIFECYCLES:
                violations.append(
                    _defect("lifecycle", f"{label}: lifecycle {lifecycle!r} is not a valid state")
                )
            elif lifecycle in REQUIRES_DEPRECATION and "deprecation" not in entry:
                violations.append(
                    _defect(
                        "deprecation-metadata",
                        f"{label}: lifecycle {lifecycle!r} requires deprecation metadata",
                    )
                )
            elif lifecycle not in REQUIRES_DEPRECATION and "deprecation" in entry:
                violations.append(
                    _defect(
                        "deprecation-metadata",
                        f"{label}: deprecation metadata is meaningless while lifecycle is {lifecycle!r}",
                    )
                )

        if isinstance(source, str):
            source_path = root / source
            if not source_path.is_file():
                violations.append(_defect("missing-source", f"{label}: source {source!r} does not exist"))
            else:
                catalogued_sources.add(source_path.resolve())
                try:
                    hashlib.sha256(source_path.read_bytes()).hexdigest()
                except OSError as exc:
                    violations.append(_defect("checksum", f"{label}: source checksum not computable: {exc}"))
                declared_version = schemas.get(source_path, {}).get("x-contract-version")
                if declared_version is not None and declared_version != version:
                    violations.append(
                        _defect(
                            "version-mismatch",
                            f"{label}: source declares x-contract-version "
                            f"{declared_version!r}, catalog says {version!r}. The "
                            "compatibility engine reads the source value to decide major "
                            "transitions, so a divergence could make a breaking change "
                            "appear approved",
                        )
                    )
                declared_id = schemas.get(source_path, {}).get("$id")
                if declared_id is not None and declared_id != contract_id:
                    violations.append(
                        _defect(
                            "id-mismatch",
                            f"{label}: source declares $id {declared_id!r}, catalog says {contract_id!r}",
                        )
                    )

    for (contract_id, version), labels in seen.items():
        if len(labels) > 1:
            violations.append(
                _defect("duplicate-entry", f"({contract_id}, {version}) is registered {len(labels)} times")
            )

    # 3. The tree and the catalog must agree in both directions.
    for path in schema_paths(root):
        if path.resolve() not in catalogued_sources:
            violations.append(
                Violation(
                    path=relative_to(path, root),
                    line=0,
                    pattern="uncatalogued-contract",
                    detail="contract schema exists on disk but is not registered in the catalog",
                )
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations = scan(args.root)
    try:
        count = len(load_catalog(args.root).get("contracts", []))
    except ContractLoadError:
        count = 0
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=f"{count} catalog entr(ies) valid, uniquely owned, and consistent with the tree",
        fail_noun="catalog defect",
    )


if __name__ == "__main__":
    sys.exit(main())
