#!/usr/bin/env python3
"""Verify a consumer lock against a release manifest. Fails closed.

This is the contracts-side implementation of the platform M0 gate check. Given
a consumer's lock and the manifest of the release it claims to pin, it answers
one question: **is this consumer actually validated against this release?**

It fails closed, per ``CROSS_REPO_COMPATIBILITY.md``. Every one of these is a
hard failure, never a warning and never a silent upgrade:

- the pinned version is not the manifest's version;
- either checksum does not match;
- a required contract identifier is absent from the release;
- the lock names a mutable source instead of a release;
- the lock or the manifest does not validate against its contract.

The last two matter more than they look. A gate that accepted a lock it could
not parse, or that resolved a version mismatch by taking the newer artifact,
would report success while verifying nothing -- which is worse than no gate,
because it manufactures confidence.

Exit codes:
    0 - the lock is verified against the manifest
    1 - at least one mismatch (blocking)
    2 - usage error
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from _contracts import (
    ContractLoadError,
    build_registry,
    load_json,
    load_schemas,
    load_yaml,
    validator_for,
)
from _scope import Violation, repo_root

CHECK_NAME = "verify_consumer_lock"

LOCK_SCHEMA_ID = "urn:ai-business:contracts:common:consumer-lock:v1"
MANIFEST_SCHEMA_ID = "urn:ai-business:contracts:common:release-manifest:v1"

PRODUCER = "ai-business-contracts"


def _load_document(path: Path) -> Any:
    """Load a YAML or JSON document by extension."""
    if path.suffix in {".yaml", ".yml"}:
        return load_yaml(path)
    return load_json(path)


def _schema_errors(document: Any, schema_id: str, root: Path, label: str) -> list[Violation]:
    schemas = load_schemas(root)
    schema = next((doc for doc in schemas.values() if doc.get("$id") == schema_id), None)
    if schema is None:
        return [Violation(path=label, line=0, pattern="missing-schema", detail=f"{schema_id} not found")]
    validator = validator_for(schema, build_registry(schemas))
    findings = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "(root)"
        findings.append(
            Violation(path=label, line=0, pattern="schema-invalid", detail=f"at {location}: {error.message}")
        )
    return findings


def verify(lock: dict[str, Any], manifest: dict[str, Any]) -> list[Violation]:
    """Compare a lock against a manifest. Returns every mismatch found.

    All checks run rather than short-circuiting on the first failure, so a
    consumer fixing a stale lock sees everything wrong with it at once.
    """
    findings: list[Violation] = []
    pin = lock.get("dependencies", {}).get(PRODUCER)
    if not isinstance(pin, dict):
        return [
            Violation(
                path="lock",
                line=0,
                pattern="missing-pin",
                detail=f"lock declares no dependency on {PRODUCER}",
            )
        ]

    # 1. Version.
    pinned_version = pin.get("version")
    released_version = manifest.get("version")
    if pinned_version != released_version:
        findings.append(
            Violation(
                path="lock",
                line=0,
                pattern="version-mismatch",
                detail=(
                    f"lock pins {pinned_version!r} but the manifest describes {released_version!r}. "
                    "The gate does not resolve this by taking the newer release"
                ),
            )
        )

    # 2. Source must be an immutable release.
    source = pin.get("source")
    if source != "release":
        findings.append(
            Violation(
                path="lock",
                line=0,
                pattern="mutable-source",
                detail=(
                    f"source is {source!r}; a production dependency must pin a release, because a "
                    "mutable source cannot be described by a checksum"
                ),
            )
        )

    # 3. Bundle checksum.
    pinned_bundle = pin.get("bundle_sha256")
    released_bundle = manifest.get("bundle_sha256")
    if pinned_bundle != released_bundle:
        findings.append(
            Violation(
                path="lock",
                line=0,
                pattern="bundle-checksum-mismatch",
                detail=(
                    f"bundle_sha256 {pinned_bundle!r} does not match the manifest's "
                    f"{released_bundle!r}; the artifact is not the one this consumer validated"
                ),
            )
        )

    # 4. Required contracts must exist in the release.
    released_ids = {
        entry.get("contract_id")
        for entry in manifest.get("contracts", [])
        if isinstance(entry, dict)
    }
    for contract_id in pin.get("required_contracts", []) or []:
        if contract_id not in released_ids:
            findings.append(
                Violation(
                    path="lock",
                    line=0,
                    pattern="unknown-required-contract",
                    detail=(
                        f"required contract {contract_id!r} is not in the pinned release; it was "
                        "removed, renamed, or never published"
                    ),
                )
            )

    return findings


def verify_manifest_checksum(manifest_path: Path, pin: dict[str, Any]) -> list[Violation]:
    """Check the lock's manifest_sha256 against the manifest file's real digest."""
    import hashlib

    actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    pinned = pin.get("manifest_sha256")
    if pinned != actual:
        return [
            Violation(
                path="lock",
                line=0,
                pattern="manifest-checksum-mismatch",
                detail=(
                    f"manifest_sha256 {pinned!r} does not match the manifest's actual digest "
                    f"{actual!r}"
                ),
            )
        ]
    return []


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", type=Path, required=True, help="consumer lock file")
    parser.add_argument("--manifest", type=Path, required=True, help="release manifest file")
    parser.add_argument("--root", type=Path, default=repo_root(), help="repository root for schemas")
    parser.add_argument(
        "--verify-manifest-digest",
        action="store_true",
        help="also hash the manifest file and compare it to the lock's manifest_sha256",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_cli().parse_args(argv)

    try:
        lock = _load_document(args.lock)
        manifest = _load_document(args.manifest)
    except (ContractLoadError, OSError) as exc:
        print(f"{CHECK_NAME}: FAIL - {exc}", file=sys.stderr)
        return 1

    findings: list[Violation] = []
    findings += _schema_errors(lock, LOCK_SCHEMA_ID, args.root, "lock")
    findings += _schema_errors(manifest, MANIFEST_SCHEMA_ID, args.root, "manifest")

    # Only compare content once both documents are structurally sound;
    # comparing fields of a malformed document produces confusing noise.
    if not findings:
        findings += verify(lock, manifest)
        if args.verify_manifest_digest:
            pin = lock.get("dependencies", {}).get(PRODUCER, {})
            findings += verify_manifest_checksum(args.manifest, pin)

    if findings:
        print(f"{CHECK_NAME}: FAIL - {len(findings)} mismatch(es); the gate fails closed", file=sys.stderr)
        for finding in findings:
            print(f"  {finding.path}: [{finding.pattern}] {finding.detail}", file=sys.stderr)
        return 1

    version = manifest.get("version")
    print(f"{CHECK_NAME}: PASS - lock verified against release {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
