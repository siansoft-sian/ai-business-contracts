#!/usr/bin/env python3
"""Validate the platform M0 compatibility matrix.

The matrix declares which repositories exist and what each is authoritative
for. It is validated against ``platform-matrix.v1``, and then against the
invariants a schema cannot express:

- all eight frozen repositories present, each exactly once;
- exclusive authority roles claimed by exactly one repository;
- every role assigned to the repository the frozen architecture names;
- datastore-access boundaries as frozen.

The exclusivity checks are the substantive ones. A schema can require that
``authority`` values come from a closed set; it cannot notice that two
repositories both claim to own business decisions, which is precisely the kind
of drift that erodes an ownership boundary.

Exit codes:
    0 - the matrix is valid and matches the frozen architecture
    1 - at least one defect (blocking)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from _contracts import (
    FROZEN_REPOSITORIES,
    ContractLoadError,
    build_registry,
    load_schemas,
    load_yaml,
    validator_for,
)
from _scope import Violation, build_parser, report

CHECK_NAME = "validate_matrix"

MATRIX_PATH = "compatibility/platform-m0-matrix.yaml"
MATRIX_SCHEMA_ID = "urn:ai-business:contracts:common:platform-matrix:v1"

#: Roles exactly one repository may hold. Two claimants is a boundary
#: collapse, zero is an unowned responsibility -- both are errors.
EXCLUSIVE_ROLES: dict[str, str] = {
    "shared-interface-contracts": "ai-business-contracts",
    "database-contracts": "ai-business-database",
    "authentication": "ai-business-auth",
    "business-authority": "ai-business-api",
    "business-authorization": "ai-business-api",
    "agent-orchestration": "ai-business-agent-runtime",
    "channel-adaptation": "ai-business-channel-gateway",
    "admin-presentation": "ai-business-admin-web",
    "deployment-and-observability-infrastructure": "ai-business-infrastructure",
}

#: Datastore-access boundary per the frozen architecture. 'forbidden' means the
#: repository must never reach business data directly, including through any
#: pooling layer.
EXPECTED_DATASTORE_ACCESS: dict[str, str] = {
    "ai-business-contracts": "forbidden",
    "ai-business-database": "owner",
    "ai-business-auth": "permitted",
    "ai-business-api": "permitted",
    "ai-business-agent-runtime": "forbidden",
    "ai-business-channel-gateway": "forbidden",
    "ai-business-admin-web": "forbidden",
    "ai-business-infrastructure": "forbidden",
}


def _defect(pattern: str, detail: str) -> Violation:
    return Violation(path=MATRIX_PATH, line=0, pattern=pattern, detail=detail)


def load_matrix(root: Path) -> dict[str, Any]:
    """Load the matrix document."""
    path = root / MATRIX_PATH
    if not path.is_file():
        raise ContractLoadError(f"{MATRIX_PATH}: matrix not found")
    document = load_yaml(path)
    if not isinstance(document, dict):
        raise ContractLoadError(f"{MATRIX_PATH}: matrix root must be a mapping")
    return document


def scan(root: Path) -> list[Violation]:
    """Return every matrix defect under ``root``."""
    violations: list[Violation] = []

    try:
        matrix = load_matrix(root)
        schemas = load_schemas(root)
    except ContractLoadError as exc:
        return [_defect("load-error", str(exc))]

    schema = next((doc for doc in schemas.values() if doc.get("$id") == MATRIX_SCHEMA_ID), None)
    if schema is None:
        return [_defect("missing-schema", f"{MATRIX_SCHEMA_ID} not found; the matrix cannot be validated")]

    validator = validator_for(schema, build_registry(schemas))
    for error in sorted(validator.iter_errors(matrix), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "(root)"
        violations.append(_defect("schema-invalid", f"at {location}: {error.message}"))

    entries = matrix.get("repositories")
    if not isinstance(entries, list):
        return violations or [_defect("schema-invalid", "'repositories' must be a list")]

    # 1. Every frozen repository present exactly once.
    listed = [e.get("repository") for e in entries if isinstance(e, dict)]
    for name in sorted(FROZEN_REPOSITORIES):
        count = listed.count(name)
        if count == 0:
            violations.append(_defect("missing-repository", f"{name} is absent from the matrix"))
        elif count > 1:
            violations.append(
                _defect("duplicate-repository", f"{name} is listed {count} times; expected exactly once")
            )
    for name in sorted({n for n in listed if n not in FROZEN_REPOSITORIES and n is not None}):
        violations.append(
            _defect("unknown-repository", f"{name!r} is not one of the frozen eight repositories")
        )

    # 2. Exclusive authority roles.
    claimants: dict[str, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        claimant = str(entry.get("repository"))
        for role in entry.get("authority", []) or []:
            claimants.setdefault(role, []).append(claimant)

    for role, expected_owner in EXCLUSIVE_ROLES.items():
        holders = claimants.get(role, [])
        if not holders:
            violations.append(_defect("unowned-authority", f"role {role!r} is claimed by no repository"))
        elif len(holders) > 1:
            violations.append(
                _defect(
                    "shared-authority",
                    f"role {role!r} is claimed by {holders}; exactly one repository may hold it",
                )
            )
        elif holders[0] != expected_owner:
            violations.append(
                _defect(
                    "wrong-authority",
                    f"role {role!r} is claimed by {holders[0]!r}; the frozen architecture "
                    f"assigns it to {expected_owner!r}",
                )
            )

    for role in sorted(set(claimants) - set(EXCLUSIVE_ROLES)):
        violations.append(_defect("unknown-authority", f"role {role!r} is not a recognised authority"))

    # 3. Datastore-access boundaries.
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        repository = entry.get("repository")
        if not isinstance(repository, str) or repository not in EXPECTED_DATASTORE_ACCESS:
            continue
        actual = entry.get("direct_datastore_access")
        expected = EXPECTED_DATASTORE_ACCESS[repository]
        if actual != expected:
            violations.append(
                _defect(
                    "datastore-boundary",
                    f"{repository}: direct_datastore_access is {actual!r}; the frozen "
                    f"architecture requires {expected!r}",
                )
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations = scan(args.root)
    try:
        count = len(load_matrix(args.root).get("repositories", []))
    except ContractLoadError:
        count = 0
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=f"{count} repositories listed once each, with authority as frozen",
        fail_noun="matrix defect",
    )


if __name__ == "__main__":
    sys.exit(main())
