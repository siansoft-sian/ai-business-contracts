#!/usr/bin/env python3
"""Validate that every contract schema is well-formed and self-describing.

Checks per ``TEST_PLAN.md`` Layer B:

- the file parses as JSON;
- the declared dialect is Draft 2020-12 and the schema meta-validates;
- ``$id`` is present, well-formed, and unique across the repository;
- title and contract-version metadata are present;
- the additional-properties policy is stated explicitly, never left implicit.

The last check is the reason this script exists rather than a bare
meta-validation call. JSON Schema defaults ``additionalProperties`` to true,
so an author who simply forgets has silently chosen an extensibility policy.
``CONTRACT_STANDARD.md`` requires that choice to be deliberate, so an object
schema that omits it fails here.

Exit codes:
    0 - every schema is valid
    1 - at least one schema is invalid (blocking)
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from _contracts import (
    ContractLoadError,
    load_schemas,
    relative_schema_name,
    schema_paths,
)
from _scope import Violation, build_parser, relative_to, report

CHECK_NAME = "validate_contracts"

DIALECT = "https://json-schema.org/draft/2020-12/schema"

#: urn:ai-business:contracts:<family>:<name>:v<major>
ID_PATTERN = re.compile(r"^urn:ai-business:contracts:[a-z0-9-]+:[a-z0-9-]+:v[0-9]+$")

SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

#: Filename form required by CONTRACT_STANDARD.md section 3.
FILENAME_PATTERN = re.compile(r"^[a-z0-9-]+\.v[0-9]+\.schema\.json$")


def _violation(path: Path, root: Path, pattern: str, detail: str) -> Violation:
    return Violation(path=relative_to(path, root), line=0, pattern=pattern, detail=detail)


def _check_object_schemas_declare_additional_properties(
    node: Any, pointer: str, out: list[str]
) -> None:
    """Recursively require an explicit additionalProperties on object schemas."""
    if not isinstance(node, dict):
        return
    declares_object = node.get("type") == "object" or "properties" in node
    if declares_object and "additionalProperties" not in node:
        out.append(pointer or "#")
    for key, value in node.items():
        if key in {"properties", "$defs", "definitions", "patternProperties"} and isinstance(
            value, dict
        ):
            for sub_key, sub_value in value.items():
                _check_object_schemas_declare_additional_properties(
                    sub_value, f"{pointer}/{key}/{sub_key}", out
                )
        elif key in {"items", "additionalProperties", "not"} and isinstance(value, dict):
            _check_object_schemas_declare_additional_properties(value, f"{pointer}/{key}", out)
        elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
            for index, sub_value in enumerate(value):
                _check_object_schemas_declare_additional_properties(
                    sub_value, f"{pointer}/{key}/{index}", out
                )


def scan(root: Path) -> list[Violation]:
    """Return every schema defect under ``root``."""
    violations: list[Violation] = []

    paths = schema_paths(root)
    if not paths:
        return [
            Violation(
                path="contracts/schemas",
                line=0,
                pattern="no-schemas",
                detail="no contract schema source found",
            )
        ]

    try:
        schemas = load_schemas(root)
    except ContractLoadError as exc:
        return [Violation(path=str(exc).split(":")[0], line=0, pattern="parse-error", detail=str(exc))]

    ids_seen: dict[str, list[str]] = defaultdict(list)

    for path, document in schemas.items():
        name = relative_to(path, root)
        filename_ok = bool(FILENAME_PATTERN.match(path.name))

        if not filename_ok:
            violations.append(
                _violation(
                    path,
                    root,
                    "filename",
                    f"must match '<name>.v<major>.schema.json', got {path.name!r}",
                )
            )

        dialect = document.get("$schema")
        if dialect != DIALECT:
            violations.append(
                _violation(path, root, "dialect", f"$schema must be {DIALECT!r}, got {dialect!r}")
            )

        schema_id = document.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            violations.append(_violation(path, root, "missing-id", "$id is required"))
        else:
            ids_seen[schema_id].append(name)
            if not ID_PATTERN.match(schema_id):
                violations.append(
                    _violation(
                        path,
                        root,
                        "id-format",
                        "$id must match 'urn:ai-business:contracts:<family>:<name>:v<major>', "
                        f"got {schema_id!r}",
                    )
                )
            elif filename_ok:
                # Only meaningful once the filename itself is well-formed;
                # otherwise the mismatch is already reported as a filename
                # defect and deriving a generation from it would raise.
                expected_major = f"v{relative_schema_name(path)[1]}"
                actual_major = schema_id.rsplit(":", 1)[-1]
                if expected_major != actual_major:
                    violations.append(
                        _violation(
                            path,
                            root,
                            "id-filename-mismatch",
                            f"$id generation {actual_major!r} does not match filename {expected_major!r}",
                        )
                    )

        if not document.get("title"):
            violations.append(_violation(path, root, "missing-title", "title is required"))

        version = document.get("x-contract-version")
        if not isinstance(version, str) or not SEMVER_PATTERN.match(version):
            violations.append(
                _violation(
                    path,
                    root,
                    "version-metadata",
                    f"x-contract-version must be MAJOR.MINOR.PATCH, got {version!r}",
                )
            )

        try:
            Draft202012Validator.check_schema(document)
        except SchemaError as exc:
            violations.append(
                _violation(path, root, "meta-validation", f"schema is not valid: {exc.message}")
            )

        implicit: list[str] = []
        _check_object_schemas_declare_additional_properties(document, "", implicit)
        for pointer in implicit:
            violations.append(
                _violation(
                    path,
                    root,
                    "implicit-additional-properties",
                    f"object schema at {pointer} must state additionalProperties explicitly",
                )
            )

    for schema_id, names in ids_seen.items():
        if len(names) > 1:
            violations.append(
                Violation(
                    path=names[0],
                    line=0,
                    pattern="duplicate-id",
                    detail=f"$id {schema_id!r} is declared by {len(names)} schemas: {', '.join(names)}",
                )
            )

    return violations


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations = scan(args.root)
    count = len(schema_paths(args.root))
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=f"{count} contract schema(s) valid, uniquely identified, and explicitly scoped",
        fail_noun="schema defect",
    )


if __name__ == "__main__":
    sys.exit(main())
