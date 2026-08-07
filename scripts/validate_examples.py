#!/usr/bin/env python3
"""Validate every committed example against the contract it declares.

``HARNESS.md`` section 4: "Examples are executable validation fixtures, not
decorative samples." An example that no longer matches its contract is a
defect in the contract or the example, and either way it must fail the build
rather than mislead a consumer reading it as documentation.

The example-to-contract mapping is by filename, not by a field inside the
example, so an example cannot drift onto the wrong contract and cannot
declare itself valid:

    contracts/examples/<family>/<name>.v<major>.<case>.example.json
        validates against
    contracts/schemas/<family>/<name>.v<major>.schema.json

Exit codes:
    0 - every example validates against its contract
    1 - at least one example is invalid (blocking)
"""

from __future__ import annotations

import sys
from pathlib import Path

from _contracts import (
    ContractLoadError,
    build_registry,
    example_paths,
    example_schema_path,
    load_json,
    load_schemas,
    validator_for,
)
from _scope import Violation, build_parser, relative_to, report

CHECK_NAME = "validate_examples"


def scan(root: Path) -> list[Violation]:
    """Return every example that fails to validate under ``root``."""
    try:
        schemas = load_schemas(root)
    except ContractLoadError as exc:
        return [Violation(path=str(exc).split(":")[0], line=0, pattern="parse-error", detail=str(exc))]

    registry = build_registry(schemas)
    violations: list[Violation] = []

    examples = example_paths(root)
    if not examples:
        return [
            Violation(
                path="contracts/examples",
                line=0,
                pattern="no-examples",
                detail="no committed example found; contracts must ship validating examples",
            )
        ]

    for example in examples:
        name = relative_to(example, root)

        try:
            schema_path = example_schema_path(example, root)
        except ContractLoadError as exc:
            violations.append(
                Violation(path=name, line=0, pattern="example-naming", detail=str(exc))
            )
            continue

        if schema_path not in schemas:
            violations.append(
                Violation(
                    path=name,
                    line=0,
                    pattern="unknown-contract",
                    detail=f"declares contract {relative_to(schema_path, root)}, which does not exist",
                )
            )
            continue

        try:
            instance = load_json(example)
        except ContractLoadError as exc:
            violations.append(Violation(path=name, line=0, pattern="parse-error", detail=str(exc)))
            continue

        validator = validator_for(schemas[schema_path], registry)
        for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path)):
            location = "/".join(str(part) for part in error.absolute_path) or "(root)"
            violations.append(
                Violation(
                    path=name,
                    line=0,
                    pattern="example-invalid",
                    detail=f"at {location}: {error.message}",
                )
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations = scan(args.root)
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=f"all {len(example_paths(args.root))} example(s) validate against their contract",
        fail_noun="invalid example",
    )


if __name__ == "__main__":
    sys.exit(main())
