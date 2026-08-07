#!/usr/bin/env python3
"""Build the release bundle, manifest, checksums, and an example consumer lock.

The output is **byte-reproducible from a commit**. Every input that would
otherwise vary per run is derived from ``HEAD`` instead of from the machine
running the build:

- member mtimes and the gzip header timestamp come from the commit time;
- owner/group are normalised to ``0``/``""`` rather than the building user;
- permissions are normalised, so a checkout with a different umask matches;
- member order is sorted by archive path, not by filesystem iteration order;
- ``built_at_utc`` in the manifest is the commit time, not the wall clock.

That last one is the substantive choice. A wall-clock build timestamp would
make the manifest differ on every rebuild, which would mean the manifest's own
checksum -- the value a consumer pins -- could not be verified by rebuilding.
What a consumer needs is which source produced the artifact, and that is a
property of the commit.

The build refuses to run against a dirty working tree. A manifest names a
commit SHA; if uncommitted edits were in the bundle, that name would be false
and the checksum would pin something no one can check out.

Exit codes:
    0 - artifacts written
    1 - the release could not be produced (dirty tree, failing compatibility
        verdict, missing input)
    2 - usage error
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

from _contracts import ContractLoadError, load_catalog, load_json
from _release import (
    CHECKSUMS_NAME,
    COMPATIBILITY_SUMMARY_NAME,
    DIST_DIR,
    EXAMPLE_LOCK_NAME,
    GOVERNANCE_VERSION,
    MANIFEST_NAME,
    ReleaseError,
    bundle_members,
    bundle_name,
    commit_epoch,
    commit_sha,
    commit_timestamp_utc,
    release_version,
    sha256_file,
    working_tree_is_dirty,
)
from _scope import repo_root

CHECK_NAME = "build_bundle"

#: Verdicts a release may carry. ``fail`` is absent on purpose: a release is
#: not published over an unapproved breaking change.
PUBLISHABLE_VERDICTS: frozenset[str] = frozenset({"pass", "review_required", "no-baseline"})

#: The consumer named in the generated example lock. Any of the frozen eight
#: except this repository would do; the API is the most representative.
EXAMPLE_LOCK_CONSUMER = "ai-business-api"


def write_bundle(root: Path, destination: Path, epoch: int) -> list[str]:
    """Write the deterministic bundle archive and return its member paths."""
    members = bundle_members(root)
    if not members:
        raise ReleaseError("no bundle members found; refusing to publish an empty release")

    prefix = destination.name
    for suffix in (".tar.gz", ".tgz"):
        if prefix.endswith(suffix):
            prefix = prefix[: -len(suffix)]
            break

    raw = io.BytesIO()
    # format=GNU_FORMAT handles paths longer than the 100-byte USTAR limit
    # without falling back to PAX extended headers, which embed
    # sub-second mtimes and would defeat reproducibility.
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for source, relative in members:
            info = archive.gettarinfo(str(source), arcname=f"{prefix}/{relative}")
            info.mtime = epoch
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            with source.open("rb") as handle:
                archive.addfile(info, handle)

    destination.parent.mkdir(parents=True, exist_ok=True)
    # filename="" keeps the source name out of the gzip header and mtime=0
    # keeps the clock out of it; both are header bytes that would otherwise
    # change the archive checksum without changing its contents.
    with (
        destination.open("wb") as out,
        gzip.GzipFile(filename="", mode="wb", fileobj=out, compresslevel=9, mtime=0) as gz,
    ):
        gz.write(raw.getvalue())

    return [relative for _, relative in members]


def read_compatibility_verdict(path: Path) -> str:
    """Read the verdict from a compatibility summary, refusing a failing one."""
    try:
        document = load_json(path)
    except ContractLoadError as exc:
        raise ReleaseError(str(exc)) from exc
    if not isinstance(document, dict):
        raise ReleaseError(f"{path}: compatibility summary must be a JSON object")
    verdict = document.get("result")
    if verdict not in PUBLISHABLE_VERDICTS:
        raise ReleaseError(
            f"{path}: compatibility verdict is {verdict!r}; a release is not published over "
            "an unapproved breaking change"
        )
    return str(verdict)


def build_manifest(
    root: Path,
    version: str,
    bundle_sha256: str,
    verdict: str,
) -> dict[str, Any]:
    """Assemble the release manifest from the catalog and the built bundle."""
    try:
        catalog = load_catalog(root)
    except ContractLoadError as exc:
        raise ReleaseError(str(exc)) from exc

    entries = catalog.get("contracts")
    if not isinstance(entries, list) or not entries:
        raise ReleaseError("catalog declares no contracts; refusing to publish an empty release")

    contracts: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ReleaseError("catalog entry is not a mapping")
        source = entry.get("source")
        if not isinstance(source, str):
            raise ReleaseError(f"catalog entry {entry.get('contract_id')!r} declares no source")
        path = root / source
        if not path.is_file():
            raise ReleaseError(f"{source}: catalogued source does not exist")
        contracts.append(
            {
                "contract_id": entry["contract_id"],
                "version": entry["version"],
                "type": entry["type"],
                "lifecycle": entry["lifecycle"],
                "owner": entry["owner"],
                "consumers": list(entry.get("consumers", [])),
                "source": source,
                "source_sha256": sha256_file(path),
            }
        )

    return {
        "repository": "ai-business-contracts",
        "version": version,
        "commit_sha": commit_sha(root),
        "built_at_utc": commit_timestamp_utc(root),
        "contracts": sorted(contracts, key=lambda c: (c["contract_id"], c["version"])),
        "bundle_sha256": bundle_sha256,
        "governance_version": GOVERNANCE_VERSION,
        "compatibility_result": verdict,
    }


def write_checksums(dist: Path, names: list[str]) -> str:
    """Write ``SHA256SUMS`` in the standard ``sha256␠␠filename`` form.

    This is what makes a lock verifiable end to end. Without it, a consumer can
    only check a manifest against itself: the manifest carries the bundle's
    digest, but nothing carries the manifest's. ``SHA256SUMS`` is the outer
    record a release is identified by.
    """
    lines = [f"{sha256_file(dist / name)}  {name}\n" for name in sorted(names)]
    path = dist / CHECKSUMS_NAME
    path.write_text("".join(lines), encoding="utf-8")
    return path.name


def write_example_lock(dist: Path, version: str, manifest_sha: str, bundle_sha: str) -> None:
    """Write a consumer lock filled in from the release actually just built.

    This is the proof that the published metadata is *sufficient*: a lock is
    produced from nothing but the release's own artifacts, and
    ``verify_consumer_lock.py`` then verifies it against that release. If a
    field a consumer needs were missing from the manifest or the checksums,
    this step could not be completed.
    """
    content = f"""# Example consumer lock, GENERATED from the release in dist/.
#
# Not a template: every value here was read from the artifacts this build
# produced. Its purpose is to demonstrate that a consumer can construct a
# verifiable pin from the published metadata alone. The hand-editable template
# is templates/consumer-contract-lock.yaml.

consumer: {EXAMPLE_LOCK_CONSUMER}

dependencies:
  ai-business-contracts:
    version: "{version}"
    source: release
    manifest_sha256: "{manifest_sha}"
    bundle_sha256: "{bundle_sha}"
    required_contracts:
      - urn:ai-business:contracts:common:error-envelope:v1
      - urn:ai-business:contracts:common:request-metadata:v1
"""
    (dist / EXAMPLE_LOCK_NAME).write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=repo_root(), help="repository root")
    parser.add_argument(
        "--dist",
        type=Path,
        default=None,
        help=f"output directory (default: <root>/{DIST_DIR})",
    )
    parser.add_argument(
        "--compatibility-summary",
        type=Path,
        default=None,
        help=f"compatibility result document (default: <dist>/{COMPATIBILITY_SUMMARY_NAME})",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="build from an uncommitted tree for local iteration; the artifacts are NOT release-valid",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root: Path = args.root
    dist: Path = args.dist or (root / DIST_DIR)
    summary_path: Path = args.compatibility_summary or (dist / COMPATIBILITY_SUMMARY_NAME)

    try:
        if working_tree_is_dirty(root):
            if not args.allow_dirty:
                print(
                    f"{CHECK_NAME}: FAIL - the working tree has uncommitted changes to tracked "
                    "files. A manifest names a commit SHA; building here would pin content that "
                    "commit does not contain. Commit first, or pass --allow-dirty for local "
                    "iteration.",
                    file=sys.stderr,
                )
                return 1
            print(
                f"{CHECK_NAME}: WARNING - building from a dirty working tree. These artifacts "
                "are NOT release-valid: the manifest's commit_sha does not describe their "
                "contents.",
                file=sys.stderr,
            )

        version = release_version(root)
        verdict = read_compatibility_verdict(summary_path)
        epoch = commit_epoch(root)

        dist.mkdir(parents=True, exist_ok=True)
        archive_name = bundle_name(version)
        members = write_bundle(root, dist / archive_name, epoch)
        bundle_sha = sha256_file(dist / archive_name)

        manifest = build_manifest(root, version, bundle_sha, verdict)
        manifest_path = dist / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        write_checksums(dist, [archive_name, MANIFEST_NAME, COMPATIBILITY_SUMMARY_NAME])
        write_example_lock(dist, version, sha256_file(manifest_path), bundle_sha)
    except ReleaseError as exc:
        print(f"{CHECK_NAME}: FAIL - {exc}", file=sys.stderr)
        return 1

    print(
        f"{CHECK_NAME}: PASS - {archive_name} ({len(members)} files), {MANIFEST_NAME} "
        f"({len(manifest['contracts'])} contracts), {CHECKSUMS_NAME}, {EXAMPLE_LOCK_NAME}"
    )
    print(f"  bundle_sha256   {bundle_sha}")
    print(f"  manifest_sha256 {sha256_file(manifest_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
