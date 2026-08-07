# Release Policy

**Status:** skeleton at EP-01. EP-05 implements bundle generation and the
reproducibility checks. `M0-CON-022`, `M0-CON-036`, `M0-CON-037`, and
`M0-CON-038` are not claimed until then.

## Immutable releases

A released contract artifact is immutable. Corrections produce a **new
version**; a published release is never edited, re-tagged, or replaced. This is
what makes an integrity hash meaningful.

## Release artifacts

A release produces:

- a contract bundle archive;
- a machine-readable manifest, identifying the commit SHA and a checksum for
  each contract source file;
- SHA-256 checksums for the manifest and the bundle;
- a compatibility summary;
- a machine-readable M0 evidence summary for the platform gate.

## Bundle contents and exclusions

The bundle carries contract and governance artifacts only. It **excludes**:

- tests and test-only negative fixtures (`tests/fixtures/negative/`);
- local caches, virtual environments, and build directories;
- `.env` files, credentials, and secrets;
- VCS metadata;
- anything not on the release surface.

The negative fixtures matter here specifically: they contain deliberately
prohibited constructs so the boundary gates can be proven to fail. They live
outside the release surface (`scripts/_scope.py`) and must never ship.
`tests/test_no_multitenancy.py` asserts they are out of scanner scope; EP-05
asserts they are out of the bundle.

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
dependency is forbidden. The lock is validated in consumer CI; it is not a
runtime import mechanism.

## To be completed in EP-05

- deterministic archive construction and reproducibility comparison;
- manifest schema and validation;
- the release workflow.
