# ai-business-contracts

**The shared language of the AI Business Platform.** This repository holds the
versioned interface contracts that the platform's repositories agree on, and
the governance that controls how those contracts change.

> **Contracts and governance only.** This repository contains no shared
> business implementation, and no other repository imports code from it.
> Consumers pin a released contract bundle by version and integrity hash.

## What lives here

| Path | Contents |
|---|---|
| `contracts/schemas/` | reusable JSON Schema (Draft 2020-12) data contracts |
| `contracts/openapi/` | OpenAPI 3.1.x HTTP interface contracts |
| `contracts/asyncapi/` | AsyncAPI 3.x event/message interface contracts |
| `contracts/examples/` | fixtures that must validate against their contracts |
| `catalog/` | machine-readable contract catalog: id, version, owner, consumers |
| `compatibility/` | compatibility policy, fixtures, and the platform M0 matrix |
| `governance/` | versioning, change process, deprecation, ownership, releases |
| `templates/` | the consumer lock template |
| `scripts/` | validation, boundary, compatibility, and release tooling |
| `tests/` | tests for the contracts and the tooling |

## What does not live here

This repository is a platform boundary, so the exclusions are enforced rather
than merely documented:

- FastAPI routers, use cases, or repositories — `ai-business-api`
- SQL, migrations, stored functions, PgBouncer config — `ai-business-database`
- authentication providers and JWT verification — `ai-business-auth`
- Casbin policies and enforcers — `ai-business-api`
- LangGraph nodes and graphs — `ai-business-agent-runtime`
- channel adapters and webhook handlers — `ai-business-channel-gateway`
- React application code — `ai-business-admin-web`
- deployment and IaC resources — `ai-business-infrastructure`
- runtime observability SDK initialisation — each runtime service

Validation scripts used to lint, test, and build contracts are permitted, and
are the only executable code in the repository.

### The platform is not multi-tenant

No contract may define tenant identifiers, tenant request headers, tenant
context, tenant-scoped authorization, tenant routing, or tenant-scoped
storage. This is checked, not assumed.

## Building and validating

One command runs every blocking check — lint, types, tests, schema, reference,
example, catalog, matrix, compatibility, boundary scans, secret scan,
dependency audit, and the release build. CI runs this same script.

```bash
uv sync --locked --all-groups
./scripts/quality_gate.sh            # add --skip-release while iterating
```

It produces `dist/` (bundle, `contract-manifest.json`, `SHA256SUMS`,
`compatibility-summary.json`) and `evidence/m0-summary.json`. The bundle and
manifest are byte-reproducible from a commit: rebuilding the same commit
yields the same checksums, which is what makes a consumer's pin verifiable.

## Boundary enforcement

Two scanners guard the **release surface** — `contracts/`, `catalog/`,
`compatibility/`, `templates/`:

```bash
python3 scripts/check_no_multitenancy.py          # exit 1 on any tenant construct
python3 scripts/check_no_implementation_code.py   # exit 1 on foreign implementation
uv run pytest                                     # includes mutation tests
```

Both accept `--root` and `--json`. Scope is defined *positively* in
`scripts/_scope.py`: governance documents, evidence, and execution prompts are
outside it by construction, because those documents must be able to name the
constructs they forbid without failing the gate. The mutation tests in
`tests/` prove each scanner **fails** when a violation is injected into a
guarded path — detection, not just absence.

## Consuming contracts

Pin a released version plus integrity metadata. Never depend on `main`:

```yaml
dependencies:
  ai-business-contracts:
    version: 0.1.0
    source: release
    manifest_sha256: <sha256>
    bundle_sha256: <sha256>
```

See `governance/RELEASES.md` and `templates/consumer-contract-lock.yaml`.

## Platform topology

Eight independently versioned repositories: `ai-business-contracts`,
`ai-business-database`, `ai-business-auth`, `ai-business-api`,
`ai-business-agent-runtime`, `ai-business-channel-gateway`,
`ai-business-admin-web`, `ai-business-infrastructure`. Authority boundaries are
recorded in `governance/OWNERSHIP.md`.

## Status

Milestone **M0 — Platform Contract Foundation & Governance**, in progress.
Execution follows `execution-prompts/EP-00` … `EP-06`; recorded outcomes live
in `evidence/`. M0 is not complete, and no acceptance criterion is claimed as
passing without recorded evidence for the audited commit.
