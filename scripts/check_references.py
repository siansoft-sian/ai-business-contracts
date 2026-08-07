#!/usr/bin/env python3
"""Verify every schema reference resolves from a clean checkout.

``HARNESS.md`` section 4 requires that every schema reference resolve without
a network fetch. Contract schemas identify themselves by URN, so resolution is
purely local: a ``$ref`` resolves only if some schema in this repository
declares the referenced ``$id``, and the JSON pointer fragment (if any) points
at something that exists.

An unresolvable reference is a blocking defect. It means a consumer cloning a
release cannot interpret the contract, which is exactly the failure the
release process exists to prevent.

Exit codes:
    0 - every reference resolves
    1 - at least one reference is unresolvable (blocking)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from referencing.exceptions import Unresolvable

from _contracts import (
    ContractLoadError,
    build_registry,
    load_schemas,
    schema_by_id,
)
from _scope import Violation, build_parser, relative_to, report

CHECK_NAME = "check_references"


def _iter_refs(node: Any, pointer: str = "") -> list[tuple[str, str]]:
    """Return every ``(json_pointer, ref)`` pair in a schema document."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{pointer}/{key}"
            if key == "$ref" and isinstance(value, str):
                found.append((pointer or "#", value))
            else:
                found.extend(_iter_refs(value, here))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_iter_refs(value, f"{pointer}/{index}"))
    return found


def _resolve_pointer(document: Any, fragment: str) -> bool:
    """Return whether a JSON pointer fragment resolves inside ``document``."""
    if fragment in {"", "/"}:
        return True
    node = document
    for raw in fragment.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if token not in node:
                return False
            node = node[token]
        elif isinstance(node, list):
            if not token.isdigit() or int(token) >= len(node):
                return False
            node = node[int(token)]
        else:
            return False
    return True


def scan(root: Path) -> list[Violation]:
    """Return every unresolvable reference under ``root``."""
    try:
        schemas = load_schemas(root)
    except ContractLoadError as exc:
        return [Violation(path=str(exc).split(":")[0], line=0, pattern="parse-error", detail=str(exc))]

    registry = build_registry(schemas)
    by_id = schema_by_id(schemas)
    violations: list[Violation] = []

    for path, document in schemas.items():
        name = relative_to(path, root)
        own_id = document.get("$id")

        for pointer, ref in _iter_refs(document):
            target, _, fragment = ref.partition("#")

            # Local reference: resolve the pointer inside this document.
            if not target:
                if not _resolve_pointer(document, fragment):
                    violations.append(
                        Violation(
                            path=name,
                            line=0,
                            pattern="dangling-local-ref",
                            detail=f"at {pointer}: {ref!r} does not resolve within this schema",
                        )
                    )
                continue

            # Cross-schema reference: the URN must be declared locally.
            if target == own_id:
                resolved = document
            elif target in by_id:
                resolved = by_id[target][1]
            else:
                violations.append(
                    Violation(
                        path=name,
                        line=0,
                        pattern="unresolvable-ref",
                        detail=(
                            f"at {pointer}: {ref!r} names {target!r}, which no schema in this "
                            "repository declares as its $id"
                        ),
                    )
                )
                continue

            if not _resolve_pointer(resolved, fragment):
                violations.append(
                    Violation(
                        path=name,
                        line=0,
                        pattern="dangling-cross-ref",
                        detail=f"at {pointer}: {ref!r} resolves to {target!r} but the fragment is absent",
                    )
                )

        # Independent confirmation through the resolver the validators use, so
        # a reference cannot pass this check yet fail during example validation.
        if isinstance(own_id, str) and own_id:
            try:
                registry.resolver().lookup(own_id)
            except Unresolvable as exc:
                violations.append(
                    Violation(
                        path=name,
                        line=0,
                        pattern="registry-lookup",
                        detail=f"{own_id!r} is not resolvable through the registry: {exc}",
                    )
                )

    return violations


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations = scan(args.root)
    try:
        total = sum(len(_iter_refs(doc)) for doc in load_schemas(args.root).values())
    except ContractLoadError:
        total = 0
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=f"all {total} schema reference(s) resolve locally",
        fail_noun="unresolvable reference",
    )


if __name__ == "__main__":
    sys.exit(main())
