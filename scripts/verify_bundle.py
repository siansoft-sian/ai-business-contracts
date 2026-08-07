#!/usr/bin/env python3
"""Verify built release artifacts against the rules a release must satisfy.

This is a *verifier*, not a second builder. It states what must be true of the
artifacts independently of how they were produced, and in particular it states
the exclusion rule negatively -- a deny-list of what may never appear in a
bundle -- where ``_release.py`` states inclusion positively. A verifier that
reused the builder's own path selection could only confirm the builder agreed
with itself; it would pass unchanged if the selection rule were wrong.

Checked:

- ``SHA256SUMS`` covers each artifact and every digest matches the file;
- the manifest validates against ``release-manifest.v1``;
- the manifest's ``bundle_sha256`` is the archive's actual digest;
- every catalogued contract appears in the manifest, and each declared
  ``source_sha256`` is the real digest of that source in the working tree;
- every manifest source path is present inside the bundle;
- the bundle contains no excluded material -- tests, negative fixtures, caches,
  virtualenvs, VCS metadata, environment files, or generated output;
- archive members are owned by no one and carry no absolute or escaping paths.

Exit codes:
    0 - the artifacts are release-valid
    1 - at least one defect (blocking)
"""

from __future__ import annotations

import re
import sys
import tarfile
from pathlib import Path
from typing import Any

from _contracts import (
    ContractLoadError,
    build_registry,
    load_catalog,
    load_json,
    load_schemas,
    validator_for,
)
from _release import (
    CHECKSUMS_NAME,
    COMPATIBILITY_SUMMARY_NAME,
    DIST_DIR,
    MANIFEST_NAME,
    bundle_name,
    release_version,
    sha256_file,
)
from _scope import Violation, build_parser, report

CHECK_NAME = "verify_bundle"

MANIFEST_SCHEMA_ID = "urn:ai-business:contracts:common:release-manifest:v1"

#: Path segments that must never appear in a release bundle. Stated
#: independently of the builder's inclusion rule, and deliberately in terms of
#: what the material *is* rather than where the builder happens to look.
FORBIDDEN_SEGMENTS: tuple[str, ...] = (
    "tests",
    "fixtures",
    "scripts",
    "evidence",
    "dist",
    "execution-prompts",
    ".git",
    ".github",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)

#: Filenames and suffixes that must never ship, wherever they sit.
FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {".env", ".env.local", ".DS_Store", "id_rsa", "credentials", ".npmrc", ".netrc"}
)
FORBIDDEN_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo", ".so", ".key", ".pem", ".p12", ".env")

SHA256SUMS_LINE = re.compile(r"^([0-9a-f]{64})  (.+)$")


def _defect(path: str, pattern: str, detail: str) -> Violation:
    return Violation(path=path, line=0, pattern=pattern, detail=detail)


def _archive_member_paths(archive: Path) -> tuple[list[str], list[Violation]]:
    """Return bundle-relative member paths, plus defects in the members themselves."""
    defects: list[Violation] = []
    relatives: list[str] = []
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if name.startswith("/") or ".." in Path(name).parts:
                defects.append(
                    _defect(archive.name, "unsafe-member-path", f"{name!r} escapes the extraction root")
                )
                continue
            if not member.isfile():
                defects.append(_defect(archive.name, "non-regular-member", f"{name!r} is not a regular file"))
                continue
            if member.uid != 0 or member.gid != 0 or member.uname or member.gname:
                defects.append(
                    _defect(
                        archive.name,
                        "member-ownership",
                        f"{name!r} records ownership ({member.uname or member.uid}); a release "
                        "artifact must not carry the building user",
                    )
                )
            # Strip the single top-level release directory.
            parts = Path(name).parts
            relatives.append("/".join(parts[1:]) if len(parts) > 1 else name)
    return relatives, defects


def check_exclusions(archive_name: str, members: list[str]) -> list[Violation]:
    """Return a defect for every bundled path that must not have shipped."""
    defects: list[Violation] = []
    for relative in members:
        parts = Path(relative).parts
        name = parts[-1]
        for segment in FORBIDDEN_SEGMENTS:
            if segment in parts:
                defects.append(
                    _defect(
                        archive_name,
                        "excluded-content",
                        f"{relative!r} lies under a {segment!r} path, which is never published",
                    )
                )
                break
        if name in FORBIDDEN_NAMES:
            defects.append(_defect(archive_name, "excluded-file", f"{relative!r} is a prohibited filename"))
        if name.endswith(FORBIDDEN_SUFFIXES):
            defects.append(_defect(archive_name, "excluded-file", f"{relative!r} has a prohibited suffix"))
    return defects


def check_checksums(dist: Path, expected: list[str]) -> list[Violation]:
    """Verify ``SHA256SUMS`` covers each artifact and every digest is correct."""
    path = dist / CHECKSUMS_NAME
    if not path.is_file():
        return [_defect(CHECKSUMS_NAME, "missing-checksums", "no SHA256SUMS was produced")]

    defects: list[Violation] = []
    recorded: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        match = SHA256SUMS_LINE.match(line)
        if not match:
            defects.append(
                Violation(
                    path=CHECKSUMS_NAME,
                    line=number,
                    pattern="malformed-checksum-line",
                    detail=f"{line!r} is not '<64 hex>  <filename>'",
                )
            )
            continue
        recorded[match.group(2)] = match.group(1)

    for name in expected:
        if name not in recorded:
            defects.append(
                _defect(CHECKSUMS_NAME, "unchecksummed-artifact", f"{name} has no recorded digest")
            )
            continue
        artifact = dist / name
        if not artifact.is_file():
            defects.append(_defect(name, "missing-artifact", "recorded in SHA256SUMS but not present"))
            continue
        actual = sha256_file(artifact)
        if actual != recorded[name]:
            defects.append(
                _defect(
                    name,
                    "checksum-mismatch",
                    f"SHA256SUMS records {recorded[name]} but the file hashes to {actual}",
                )
            )
    return defects


def check_manifest(root: Path, dist: Path, manifest: dict[str, Any], members: list[str]) -> list[Violation]:
    """Validate the manifest against its contract and against reality."""
    defects: list[Violation] = []

    try:
        schemas = load_schemas(root)
    except ContractLoadError as exc:
        return [_defect(MANIFEST_NAME, "load-error", str(exc))]

    schema = next((doc for doc in schemas.values() if doc.get("$id") == MANIFEST_SCHEMA_ID), None)
    if schema is None:
        return [_defect(MANIFEST_NAME, "missing-schema", f"{MANIFEST_SCHEMA_ID} not found")]

    validator = validator_for(schema, build_registry(schemas))
    for error in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path) or "(root)"
        defects.append(_defect(MANIFEST_NAME, "schema-invalid", f"at {location}: {error.message}"))

    version = manifest.get("version")
    archive = dist / bundle_name(str(version))
    if not archive.is_file():
        defects.append(
            _defect(MANIFEST_NAME, "missing-bundle", f"{archive.name} is not present in {dist.name}/")
        )
    else:
        actual = sha256_file(archive)
        if manifest.get("bundle_sha256") != actual:
            defects.append(
                _defect(
                    MANIFEST_NAME,
                    "bundle-checksum-mismatch",
                    f"manifest records {manifest.get('bundle_sha256')} but {archive.name} hashes to {actual}",
                )
            )

    try:
        declared_version = release_version(root)
    except Exception:  # noqa: BLE001 - reported as a defect, not raised
        declared_version = None
    if declared_version is not None and version != declared_version:
        defects.append(
            _defect(
                MANIFEST_NAME,
                "version-mismatch",
                f"manifest declares {version!r} but the repository declares {declared_version!r}",
            )
        )

    # Every catalogued contract must be published, with a truthful checksum.
    try:
        catalog = load_catalog(root)
    except ContractLoadError as exc:
        defects.append(_defect(MANIFEST_NAME, "load-error", str(exc)))
        return defects

    published = {
        entry.get("contract_id"): entry for entry in manifest.get("contracts", []) if isinstance(entry, dict)
    }
    member_set = set(members)
    for entry in catalog.get("contracts", []):
        if not isinstance(entry, dict):
            continue
        contract_id = entry.get("contract_id")
        release_entry = published.get(contract_id)
        if release_entry is None:
            defects.append(
                _defect(
                    MANIFEST_NAME,
                    "uncatalogued-release",
                    f"catalogued contract {contract_id!r} is absent from the manifest",
                )
            )
            continue
        source = release_entry.get("source")
        if source not in member_set:
            defects.append(
                _defect(
                    MANIFEST_NAME,
                    "source-not-bundled",
                    f"{contract_id!r} declares source {source!r}, which is not inside the bundle",
                )
            )
        path = root / str(source)
        if path.is_file():
            actual = sha256_file(path)
            if release_entry.get("source_sha256") != actual:
                defects.append(
                    _defect(
                        MANIFEST_NAME,
                        "source-checksum-mismatch",
                        f"{contract_id!r} records {release_entry.get('source_sha256')} but "
                        f"{source} hashes to {actual}",
                    )
                )

    catalogued = {str(e.get("contract_id")) for e in catalog.get("contracts", []) if isinstance(e, dict)}
    for contract_id in sorted({str(cid) for cid in published} - catalogued):
        defects.append(
            _defect(
                MANIFEST_NAME,
                "unknown-release-entry",
                f"manifest publishes {contract_id!r}, which the catalog does not declare",
            )
        )

    return defects


def scan(root: Path, dist: Path) -> list[Violation]:
    """Return every release defect found in ``dist``."""
    manifest_path = dist / MANIFEST_NAME
    if not manifest_path.is_file():
        return [_defect(MANIFEST_NAME, "missing-manifest", f"no manifest in {dist}; run build_bundle.py")]

    try:
        manifest = load_json(manifest_path)
    except ContractLoadError as exc:
        return [_defect(MANIFEST_NAME, "load-error", str(exc))]
    if not isinstance(manifest, dict):
        return [_defect(MANIFEST_NAME, "load-error", "manifest root must be a JSON object")]

    archive = dist / bundle_name(str(manifest.get("version")))
    if not archive.is_file():
        return [_defect(archive.name, "missing-bundle", "the manifest's bundle is not present")]

    members, defects = _archive_member_paths(archive)
    defects += check_exclusions(archive.name, members)
    defects += check_manifest(root, dist, manifest, members)
    defects += check_checksums(dist, [archive.name, MANIFEST_NAME, COMPATIBILITY_SUMMARY_NAME])
    return defects


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--dist", type=Path, default=None, help=f"artifact directory (default: <root>/{DIST_DIR})"
    )
    args = parser.parse_args(argv)
    dist: Path = args.dist or (args.root / DIST_DIR)

    violations = scan(args.root, dist)
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=(
            f"release artifacts in {dist.name}/ are internally consistent and carry no excluded content"
        ),
        fail_noun="release defect",
    )


if __name__ == "__main__":
    sys.exit(main())
