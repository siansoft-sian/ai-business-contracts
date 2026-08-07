"""Release bundle, manifest, and reproducibility tests (TEST_PLAN.md Layer E).

Two things are proven here that a passing build does not prove on its own:

1. **Reproducibility is byte-level, not "looks the same".** The bundle is
   rebuilt from scratch after deleting ``dist/`` and the archive's SHA-256 is
   compared. A test that compared file listings would pass even if the archive
   embedded the building user, the umask, or the wall clock -- which is exactly
   what makes an artifact checksum unpinnable.

2. **The exclusion rule can fail.** Asserting that today's bundle happens to
   contain no test files says little. The tests inject each excluded family
   into a bundle and assert the verifier rejects it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR))

import build_bundle  # noqa: E402
import verify_bundle  # noqa: E402
from _release import (  # noqa: E402
    CHECKSUMS_NAME,
    COMPATIBILITY_SUMMARY_NAME,
    EXAMPLE_LOCK_NAME,
    MANIFEST_NAME,
    bundle_members,
    bundle_name,
    release_version,
    sha256_file,
)


def _compatibility_summary(dist: Path) -> Path:
    """Write a minimal, valid compatibility summary for the build to consume."""
    dist.mkdir(parents=True, exist_ok=True)
    path = dist / COMPATIBILITY_SUMMARY_NAME
    path.write_text(
        json.dumps(
            {
                "baseline": None,
                "candidate": "0.1.0",
                "result": "no-baseline",
                "breaking": [],
                "review_required": [],
                "compatible": [],
                "approved_major_transition": False,
                "checked_at_utc": "2026-08-07T00:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def built(tmp_path: Path) -> Path:
    """Build the real repository's artifacts into an isolated dist directory."""
    dist = tmp_path / "dist"
    _compatibility_summary(dist)
    code = build_bundle.main(["--root", str(REPO_ROOT), "--dist", str(dist), "--allow-dirty"])
    assert code == 0, "the bundle build failed"
    return dist


# --- reproducibility -------------------------------------------------------


def test_rebuilding_reproduces_the_same_archive_bytes(tmp_path: Path, built: Path) -> None:
    """Layer E: delete dist/, rebuild, and compare the archive checksum."""
    version = release_version(REPO_ROOT)
    first = sha256_file(built / bundle_name(version))

    shutil.rmtree(built)
    _compatibility_summary(built)
    assert build_bundle.main(["--root", str(REPO_ROOT), "--dist", str(built), "--allow-dirty"]) == 0

    assert sha256_file(built / bundle_name(version)) == first


def test_rebuilding_reproduces_the_same_manifest_bytes(built: Path) -> None:
    """The manifest is what a consumer pins, so it must be reproducible too."""
    first = (built / MANIFEST_NAME).read_bytes()
    assert build_bundle.main(["--root", str(REPO_ROOT), "--dist", str(built), "--allow-dirty"]) == 0
    assert (built / MANIFEST_NAME).read_bytes() == first


def test_archive_carries_no_building_user_or_wall_clock(built: Path) -> None:
    """The three inputs that silently break reproducibility."""
    archive = built / bundle_name(release_version(REPO_ROOT))
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
    assert members, "the archive is empty"
    mtimes = {member.mtime for member in members}
    assert len(mtimes) == 1, f"member mtimes vary: {sorted(mtimes)}"
    for member in members:
        assert member.uid == 0 and member.gid == 0
        assert member.uname == "" and member.gname == ""
        assert member.mode == 0o644


def test_member_order_is_sorted_not_filesystem_order(built: Path) -> None:
    archive = built / bundle_name(release_version(REPO_ROOT))
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert names == sorted(names)


# --- contents and exclusions ----------------------------------------------


def _member_relatives(archive: Path) -> list[str]:
    with tarfile.open(archive, "r:gz") as tar:
        return ["/".join(Path(name).parts[1:]) for name in tar.getnames()]


def test_every_catalogued_contract_source_is_bundled(built: Path) -> None:
    manifest = json.loads((built / MANIFEST_NAME).read_text(encoding="utf-8"))
    bundled = set(_member_relatives(built / bundle_name(manifest["version"])))
    for entry in manifest["contracts"]:
        assert entry["source"] in bundled, f"{entry['contract_id']} source is not in the bundle"


def test_source_checksums_are_the_real_digests(built: Path) -> None:
    manifest = json.loads((built / MANIFEST_NAME).read_text(encoding="utf-8"))
    for entry in manifest["contracts"]:
        assert entry["source_sha256"] == sha256_file(REPO_ROOT / entry["source"])


def test_bundle_excludes_tests_scripts_and_generated_output(built: Path) -> None:
    relatives = _member_relatives(built / bundle_name(release_version(REPO_ROOT)))
    for relative in relatives:
        parts = Path(relative).parts
        for forbidden in ("tests", "scripts", "dist", "evidence", ".git", ".venv", "__pycache__"):
            assert forbidden not in parts, f"{relative} should never ship"


def test_bundle_excludes_the_compatibility_fixtures(built: Path) -> None:
    """The fixtures deliberately contain invalid and breaking contract source.

    Shipping them would put artifacts into a release that this repository's own
    validators exist to reject.
    """
    relatives = _member_relatives(built / bundle_name(release_version(REPO_ROOT)))
    assert not [r for r in relatives if r.startswith("compatibility/fixtures/")]
    # ...while the rest of compatibility/ is still published.
    assert "compatibility/policy.md" in relatives
    assert "compatibility/platform-m0-matrix.yaml" in relatives


def test_bundle_carries_governance_alongside_contracts(built: Path) -> None:
    """Contracts without their change rules are a snapshot, not a contract."""
    relatives = _member_relatives(built / bundle_name(release_version(REPO_ROOT)))
    for required in (
        "governance/VERSIONING.md",
        "governance/CHANGE_PROCESS.md",
        "governance/RELEASES.md",
        "templates/consumer-contract-lock.yaml",
        "catalog/contract-catalog.yaml",
    ):
        assert required in relatives, f"{required} belongs in a release"


def test_bundle_member_selection_matches_the_declared_rule(built: Path) -> None:
    declared = {relative for _, relative in bundle_members(REPO_ROOT)}
    assert set(_member_relatives(built / bundle_name(release_version(REPO_ROOT)))) == declared


# --- checksums and the example lock ---------------------------------------


def test_checksums_cover_every_published_artifact(built: Path) -> None:
    recorded = {}
    for line in (built / CHECKSUMS_NAME).read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        recorded[name] = digest
    for name in (bundle_name(release_version(REPO_ROOT)), MANIFEST_NAME, COMPATIBILITY_SUMMARY_NAME):
        assert name in recorded
        assert recorded[name] == sha256_file(built / name)


def test_generated_lock_verifies_against_the_release_it_came_from(built: Path) -> None:
    """M0-CON-041: the published metadata is sufficient to construct a pin.

    The lock is built from nothing but the release's own artifacts and then
    verified against that release, including the manifest's own digest. If a
    field a consumer needs were missing, this could not complete.
    """
    import verify_consumer_lock

    code = verify_consumer_lock.main(
        [
            "--lock",
            str(built / EXAMPLE_LOCK_NAME),
            "--manifest",
            str(built / MANIFEST_NAME),
            "--root",
            str(REPO_ROOT),
            "--verify-manifest-digest",
        ]
    )
    assert code == 0


# --- the verifier must be able to fail ------------------------------------


def _repack(dist: Path, extra: dict[str, str] | None = None, drop: str | None = None) -> None:
    """Rewrite the bundle, optionally adding files or dropping one."""
    version = release_version(REPO_ROOT)
    archive = dist / bundle_name(version)
    prefix = f"ai-business-contracts-{version}"
    staging = dist / "_staging"
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(staging, filter="data")
    root = staging / prefix
    for relative, content in (extra or {}).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    if drop:
        (root / drop).unlink()
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=f"{prefix}/{path.relative_to(root)}")
    shutil.rmtree(staging)


def test_verifier_passes_on_an_unmodified_release(built: Path) -> None:
    """The control: without it, every failure below could be a false alarm."""
    assert verify_bundle.main(["--root", str(REPO_ROOT), "--dist", str(built)]) == 0


@pytest.mark.parametrize(
    ("relative", "reason"),
    [
        ("tests/test_leak.py", "test code"),
        ("compatibility/fixtures/breaking/x/baseline/a.schema.json", "negative fixture"),
        (".env", "environment file"),
        ("contracts/schemas/common/__pycache__/x.pyc", "local cache"),
        ("scripts/build_bundle.py", "tooling"),
    ],
)
def test_excluded_content_is_rejected_by_the_verifier(built: Path, relative: str, reason: str) -> None:
    """Each excluded family must actually fail, not merely be absent today."""
    _repack(built, extra={relative: "x\n"})
    violations = verify_bundle.scan(REPO_ROOT, built)
    patterns = {v.pattern for v in violations}
    assert patterns & {"excluded-content", "excluded-file"}, f"{reason} was not rejected: {violations}"


def test_missing_contract_source_is_rejected(built: Path) -> None:
    _repack(built, drop="contracts/schemas/common/error-envelope.v1.schema.json")
    violations = verify_bundle.scan(REPO_ROOT, built)
    assert "source-not-bundled" in {v.pattern for v in violations}


def test_tampered_bundle_breaks_the_manifest_checksum(built: Path) -> None:
    """The point of the digest: a changed archive stops matching its manifest."""
    _repack(built, extra={"governance/EXTRA.md": "added after the manifest was written\n"})
    violations = verify_bundle.scan(REPO_ROOT, built)
    assert "bundle-checksum-mismatch" in {v.pattern for v in violations}


def test_edited_manifest_breaks_the_recorded_checksum(built: Path) -> None:
    manifest_path = built / MANIFEST_NAME
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["governance_version"] = "99"
    manifest_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    violations = verify_bundle.scan(REPO_ROOT, built)
    assert "checksum-mismatch" in {v.pattern for v in violations}


def test_manifest_claiming_an_uncatalogued_contract_is_rejected(built: Path) -> None:
    manifest_path = built / MANIFEST_NAME
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = dict(document["contracts"][0])
    entry["contract_id"] = "urn:ai-business:contracts:common:invented:v1"
    document["contracts"].append(entry)
    manifest_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    violations = verify_bundle.scan(REPO_ROOT, built)
    assert "unknown-release-entry" in {v.pattern for v in violations}


def test_falsified_source_checksum_is_rejected(built: Path) -> None:
    manifest_path = built / MANIFEST_NAME
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["contracts"][0]["source_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    violations = verify_bundle.scan(REPO_ROOT, built)
    assert "source-checksum-mismatch" in {v.pattern for v in violations}


def test_missing_manifest_is_rejected(tmp_path: Path) -> None:
    violations = verify_bundle.scan(REPO_ROOT, tmp_path)
    assert "missing-manifest" in {v.pattern for v in violations}


# --- the build must refuse the cases it should ----------------------------


def test_build_refuses_a_failing_compatibility_verdict(tmp_path: Path) -> None:
    """A release is not published over an unapproved breaking change."""
    dist = tmp_path / "dist"
    summary = _compatibility_summary(dist)
    document = json.loads(summary.read_text(encoding="utf-8"))
    document["result"] = "fail"
    summary.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    assert build_bundle.main(["--root", str(REPO_ROOT), "--dist", str(dist), "--allow-dirty"]) == 1
    assert not (dist / MANIFEST_NAME).exists()


def test_build_refuses_a_dirty_tree_without_the_explicit_flag(tmp_path: Path) -> None:
    """A manifest names a commit; building over uncommitted edits would lie.

    The repository under test is checked out clean in CI, so the refusal is
    exercised against a scratch clone with an uncommitted edit rather than by
    dirtying the real tree.
    """
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(REPO_ROOT), str(clone)],
        check=True,
        capture_output=True,
    )
    (clone / "catalog" / "contract-catalog.yaml").write_text("# edited\n", encoding="utf-8")

    dist = clone / "dist"
    _compatibility_summary(dist)
    assert build_bundle.main(["--root", str(clone), "--dist", str(dist)]) == 1
    assert not (dist / MANIFEST_NAME).exists()


def test_evidence_output_does_not_count_as_a_dirty_build_input(tmp_path: Path) -> None:
    """Writing the M0 summary must not block the next build.

    evidence/ is an output of the gate, never an input to a build, so a change
    there does not make the manifest's commit_sha untrue.
    """
    from _release import working_tree_is_dirty

    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(REPO_ROOT), str(clone)],
        check=True,
        capture_output=True,
    )
    assert working_tree_is_dirty(clone) is False

    (clone / "evidence" / "EVIDENCE_INDEX.md").write_text("# rewritten\n", encoding="utf-8")
    assert working_tree_is_dirty(clone) is False, "evidence/ must not count as a build input"

    (clone / "catalog" / "contract-catalog.yaml").write_text("# edited\n", encoding="utf-8")
    assert working_tree_is_dirty(clone) is True, "a contract edit must still count"
