# CROSS_REPO_COMPATIBILITY.md

## Purpose

Define the `ai-business-contracts` contribution to the **platform M0 cross-repository compatibility gate**.

This file does not claim the other seven repository M0s are complete. It defines the artifacts this repository must publish so the platform gate can verify compatibility without importing implementation code.

## Required contracts-release outputs

A passing contracts M0 build must produce:

1. `dist/ai-business-contracts-<version>.tar.gz`
2. `dist/contract-manifest.json`
3. `dist/SHA256SUMS`
4. `dist/compatibility-summary.json`
5. `evidence/m0-summary.json`

### `contract-manifest.json` minimum fields

```json
{
  "repository": "ai-business-contracts",
  "version": "0.1.0",
  "commit_sha": "<git-sha>",
  "built_at_utc": "<timestamp>",
  "contracts": [],
  "bundle_sha256": "<sha256>",
  "governance_version": "1",
  "compatibility_result": "pass"
}
```

Each item in `contracts` must include stable ID, version, type, source path, owner, consumers, lifecycle state, and source checksum.

## Consumer pinning contract

Every consuming repository must eventually keep an immutable dependency record equivalent to:

```yaml
dependencies:
  ai-business-contracts:
    version: 0.1.0
    source: release
    bundle_sha256: <sha256>
    manifest_sha256: <sha256>
```

M0 does not require every consumer to implement its full contract usage. It does require the format and platform-gate semantics to be frozen.

## Compatibility matrix

`compatibility/platform-m0-matrix.yaml` must list all eight repositories and distinguish:

- contract provider;
- contract consumer;
- special contract authority;
- M0 compatibility check expected.

Required authority notes:

- `ai-business-contracts` is the shared interface-contract authority.
- `ai-business-database` separately owns database/stored-function contracts; runtime FastAPI traffic reaches PostgreSQL through asyncpg/PgBouncer while Sqitch/migrations connect directly to PostgreSQL and bypass PgBouncer.
- `ai-business-api` owns business behavior and authorization decisions, while its externally shared interface schemas are versioned through the contract governance model.
- `ai-business-auth` owns authentication implementation.
- `ai-business-agent-runtime` owns agent orchestration implementation; no LangGraph details belong in shared contracts unless they are externally observable protocol fields (avoid this in M0).
- `ai-business-channel-gateway` owns channel adapter implementation.
- `ai-business-admin-web` consumes APIs/contracts and never receives direct DB/LangGraph access.
- `ai-business-infrastructure` consumes deployment/observability interface requirements but does not become the source of runtime service contracts.

## Platform gate checks enabled by this repo

The platform gate must be able to verify:

1. every repository declares the `ai-business-contracts` version it was validated against when relevant;
2. no consumer points at an unversioned mutable branch as its production contract source;
3. pinned checksums match the published bundle/manifest;
4. expected consumer-facing contract IDs exist in the pinned catalog;
5. no breaking contract change is accepted without the required major-version/change approval;
6. database-contract checks use `ai-business-database` as the database contract authority rather than duplicating those interfaces here;
7. the prohibited multi-tenant scan is green in all contract artifacts exchanged across repositories.

## Failure semantics

Any mismatch in version, checksum, required contract ID, authority, or compatibility result is a **hard platform-gate failure**. The gate must fail closed; it must not silently choose a newer contract version.
