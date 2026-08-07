# Contract Ownership & Authority Map

**Status:** authoritative for repository boundaries. Catalog-level owner
enforcement is live: `catalog/contract-catalog.yaml` registers one owner per
contract and `scripts/validate_catalog.py` rejects any other arrangement. The
platform matrix is an EP-04 deliverable.

## Rule

Every contract has **exactly one authoritative owner**. A contract without an
owner is invalid. Ownership is recorded in the catalog and enforced at review
time through `CODEOWNERS`.

Owning a contract means owning its shape, its version, its deprecation, and
its compatibility decisions. Consumers are listed explicitly so that consumer
impact is a fact rather than a guess.

## The frozen eight repositories

The platform consists of exactly eight independently versioned repositories.
Responsibilities are not collapsed or merged.

| Repository | Authority |
|---|---|
| `ai-business-contracts` | shared language: contract schemas, compatibility policy, contract catalog, release metadata. Contracts only. |
| `ai-business-database` | PostgreSQL, Sqitch, stored functions, database roles, PgBouncer, **database contracts**, migrations |
| `ai-business-auth` | identity and authentication |
| `ai-business-api` | business authority and business authorization |
| `ai-business-agent-runtime` | agent orchestration; LangGraph is an implementation detail. Agent nodes never access the business database directly. |
| `ai-business-channel-gateway` | external channel adapters, webhook verification, normalization, deduplication, delivery |
| `ai-business-admin-web` | browser admin application; never directly accesses PostgreSQL, PgBouncer, or LangGraph |
| `ai-business-infrastructure` | deployment/IaC, OpenTelemetry collector infrastructure, Prometheus, Grafana, environment/deployment configuration |

Observability instrumentation stays inside each runtime service; centralized
observability infrastructure is deployed by `ai-business-infrastructure`.

## Database contract authority stays with ai-business-database

This is called out separately because it is the ownership boundary most likely
to be eroded by convenience.

`ai-business-database` owns its **database contracts**, because those contracts
describe stored-function and database interfaces and migration compatibility.
`ai-business-contracts` must not:

- absorb SQL, DDL, migrations, or stored-function bodies;
- hold PgBouncer configuration or credentials;
- duplicate or override database-contract authority.

This repository **may** catalog or reference a cross-repository dependency on a
database contract. It never becomes that contract's owner.

Frozen database/API boundary facts, recorded here but implemented elsewhere:
runtime FastAPI database traffic uses `asyncpg` pooling through PgBouncer, and
migration traffic connects directly to PostgreSQL, bypassing PgBouncer.

## Authentication and authorization are separate

Authentication is `ai-business-auth`. Business authorization is
`ai-business-api`. No contract in this repository encodes an authorization
decision, and request/correlation identifiers are observability metadata, never
authorization inputs.

## No cross-repository implementation imports

No repository imports implementation code from another. Repositories agree
through **versioned contract releases pinned by version and integrity hash**.
This repository must never become a shared runtime library.

## Enforcement

| Rule | Enforced by |
|---|---|
| No foreign implementation on the release surface | `scripts/check_no_implementation_code.py` + mutation tests |
| No SQL/PgBouncer/Sqitch anywhere in this repository | same scanner, file-family family (repository-wide) |
| No multi-tenant constructs | `scripts/check_no_multitenancy.py` + mutation tests |
| Exactly one owner per contract | `scripts/validate_catalog.py` + catalog tests |
| A contract on disk but unregistered | catalog/tree agreement check |
| A breaking change without a major bump | `scripts/check_compatibility.py` |
| Owner review before merge | `CODEOWNERS` |
