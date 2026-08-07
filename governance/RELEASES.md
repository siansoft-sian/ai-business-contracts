# Release Policy

**Status:** policy complete. Bundle generation and reproducibility checks are
implemented by EP-05, so `M0-CON-036`–`M0-CON-038` are claimed there, not here.

## Immutable releases

**A released contract artifact is immutable.** Corrections produce a new
version; a published release is never edited, re-tagged, or replaced.

This is what makes an integrity hash meaningful. A consumer pinning
`bundle_sha256` is asserting that a specific byte sequence is what it validated
against; if a published version's content could change, the pin would verify
nothing.

The rule is machine-enforced rather than merely stated.
`scripts/check_compatibility.py` reports the same `(contract_id, version)` with
different content as `released-version-content-changed`, a breaking finding
that fails the gate. Re-releasing a changed `0.1.0` is not a policy violation
someone might notice in review; it is a build failure.

## Release artifacts

A release produces, per `CROSS_REPO_COMPATIBILITY.md`:

| Artifact | Contents |
|---|---|
| `dist/ai-business-contracts-<version>.tar.gz` | the contract bundle |
| `dist/contract-manifest.json` | commit SHA, version, and a checksum per contract source |
| `dist/SHA256SUMS` | checksums for the bundle and manifest |
| `dist/compatibility-summary.json` | the compatibility result document |
| `evidence/m0-summary.json` | machine-readable milestone summary for the platform gate |

`compatibility-summary.json` is itself governed, by
`urn:ai-business:contracts:common:compatibility-result:v1`. The platform gate
validates the summary it consumes instead of trusting our output shape.

## Bundle contents and exclusions

The bundle carries contract and governance artifacts only. It **excludes**:

- `tests/`, including `tests/fixtures/negative/` and `tests/fixtures/invalid/`;
- `compatibility/fixtures/`, which are curated proofs of the engine rather than
  published contracts;
- local caches, virtual environments, and build directories;
- `.env` files, credentials, and secrets;
- VCS metadata;
- anything not on the release surface (`scripts/_scope.py`).

The negative fixtures matter specifically: they contain deliberately prohibited
constructs so the boundary gates can be proven to fail. They live outside the
release surface and must never ship. `tests/test_no_multitenancy.py` asserts
they are out of scanner scope; EP-05 asserts they are out of the bundle.

## Consumer pinning

Consumers pin a released version plus integrity metadata:

```yaml
dependencies:
  ai-business-contracts:
    version: 0.1.0
    source: release
    manifest_sha256: <sha256>
    bundle_sha256: <sha256>
```

Consuming `main`, a mutable branch, or a floating range as the sole production
dependency is **forbidden**. The lock is validated in consumer CI; it is not a
runtime import mechanism, and this repository never becomes an imported
library.

The lock template and the platform matrix are EP-04 deliverables.

## Baseline and the first release

Until `0.1.0` is published there is no baseline to compare against.
`compatibility/baseline.yaml` records this explicitly, and the engine reports
`no-baseline` rather than `pass`, because a pass would read as "compared and
found compatible".

The engine is proven meanwhile by the curated fixtures under
`compatibility/fixtures/`, which cover every mandatory case in `TEST_PLAN.md`
Layer D in both directions. On publication, `baseline_release` becomes `0.1.0`
and every later candidate is compared against the released artifact.

## Fail closed

Any mismatch in version, checksum, required contract ID, authority, or
compatibility result is a hard failure. The gate must never silently choose a
newer contract version, and must never treat a missing comparison as a passing
one.
