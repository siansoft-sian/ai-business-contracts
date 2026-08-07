# PROMPT.md

## Mission

Build **M0 — Platform Contract Foundation & Governance** for `ai-business-contracts`.

The result must establish a versioned, machine-validatable, contract-first foundation that all other AI Business Platform repositories can consume without importing another repository's implementation code.

## Frozen platform architecture

The platform consists of exactly eight independently versioned repositories:

1. `ai-business-contracts`
2. `ai-business-database`
3. `ai-business-auth`
4. `ai-business-api`
5. `ai-business-agent-runtime`
6. `ai-business-channel-gateway`
7. `ai-business-admin-web`
8. `ai-business-infrastructure`

### Authority boundaries

- `ai-business-contracts` — shared language, contract schemas, compatibility policy, contract catalog, release metadata. **Contracts only.**
- `ai-business-database` — PostgreSQL, Sqitch, stored functions, database roles, PgBouncer, database contracts, migrations.
  - Runtime FastAPI database traffic uses `asyncpg` pooling through PgBouncer.
  - Sqitch/migration traffic connects directly to PostgreSQL and bypasses PgBouncer.
- `ai-business-auth` — identity and authentication.
- `ai-business-api` — business authority and business authorization.
- `ai-business-agent-runtime` — agent orchestration; LangGraph is an implementation detail. Agent nodes never access the business database directly.
- `ai-business-channel-gateway` — external channel adapters, webhook verification, normalization, deduplication, delivery.
- `ai-business-admin-web` — browser admin application; never directly accesses PostgreSQL, PgBouncer, or LangGraph.
- `ai-business-infrastructure` — deployment/IaC, OpenTelemetry collector infrastructure, Prometheus, Grafana, and environment/deployment configuration.

Observability instrumentation remains inside each runtime service; centralized observability infrastructure is deployed by `ai-business-infrastructure`.

### Absolute no-multi-tenancy rule

The platform is **not multi-tenant**. Do not introduce or preserve:

- tenant identifiers in payloads or schemas;
- tenant-specific request headers;
- tenant context objects;
- tenant-scoped authorization;
- tenant routing;
- tenant-scoped persistence/storage;
- tenant-scoped rate-limit or idempotency keys;
- tenant fields in logs, traces, metrics, errors, events, or examples.

A repository check must fail when any prohibited multi-tenant construct appears in contract-bearing paths.

## M0 objective

Create the foundation that answers these questions deterministically:

1. **What is a contract?**
2. **Where does each contract live?**
3. **Who owns it and who consumes it?**
4. **How is it versioned?**
5. **How is backward compatibility determined?**
6. **How are references and examples validated?**
7. **How do consumer repositories pin a contract release?**
8. **How does the platform compatibility gate verify a contracts release?**
9. **How are breaking changes proposed, reviewed, released, deprecated, and retired?**
10. **How do we prove the repository contains contracts/governance rather than shared implementation?**

## Required M0 deliverables

### A. Contract source structure

Create canonical source directories for:

- OpenAPI service contracts;
- AsyncAPI/event contracts;
- reusable JSON Schema components;
- examples/fixtures that validate against schemas;
- a machine-readable contract catalog;
- compatibility metadata.

M0 does **not** need to define every future business endpoint or agent/channel message. It must define the framework and a small set of platform primitives sufficient to prove the system works.

### B. Foundation contract primitives

Provide versioned foundational schemas for at least:

1. **Error envelope** — stable machine-readable error code, safe message, optional structured details, request/correlation identifiers.
2. **Request/correlation metadata** — request ID, correlation ID, optional W3C trace context fields where appropriate; no identity secrets or PII.
3. **Event envelope** — event ID, event type, contract version, occurred-at timestamp, correlation metadata, producer identifier, payload reference/shape.
4. **Contract metadata** — contract ID, semantic version, lifecycle status, owner, consumers, compatibility mode, source path, checksum/fingerprint metadata.

Keep these primitives transport-neutral where practical. They must not encode business rules.

### C. Contract catalog

Create a machine-readable catalog containing, at minimum:

- contract ID;
- contract family/type (`openapi`, `asyncapi`, `json-schema`, or other explicitly approved type);
- version;
- lifecycle state (`draft`, `active`, `deprecated`, `retired`);
- owning repository;
- provider repository where applicable;
- consumer repositories;
- canonical source path;
- compatibility policy;
- deprecation metadata when relevant.

Ownership must be explicit. A contract without an owner is invalid.

### D. Governance policy

Document and enforce:

- semantic versioning;
- contract-first change workflow;
- backward-compatibility rules;
- breaking-change rules;
- deprecation and retirement policy;
- pull-request review requirements;
- ownership/CODEOWNERS expectations;
- consumer pinning rules;
- release artifact rules;
- immutable release principle;
- emergency/security change handling;
- no implementation-code rule.

### E. Compatibility policy

Implement a compatibility gate with test fixtures proving both positive and negative cases.

At minimum, the gate must detect or fail on:

- removal or rename of a previously published operation/path/message/field;
- incompatible type change;
- making a previously optional request field required;
- removing a previously allowed response/error shape relied upon by consumers;
- narrowing an allowed value set without a major version;
- invalid/unresolvable schema references;
- duplicate contract identifiers or versions.

The policy must also state that apparently additive changes can still require review (for example enum expansion for closed consumers).

### F. Consumer pinning and release artifacts

Define a language-neutral consumer lock format. Consumers must pin an immutable contract release by version plus integrity metadata; they must not consume `main`/`HEAD` as a production dependency.

A successful M0 build must be able to produce:

- a contract bundle archive;
- a machine-readable manifest;
- checksums/fingerprints;
- a compatibility summary;
- a machine-readable M0 evidence summary suitable for the platform compatibility gate.

No generated runtime SDK is required in M0. Avoid creating a shared runtime library that consumers import.

### G. Repository boundary enforcement

Provide automated checks proving the repository contains contract source, validation tooling, tests, governance, and build metadata — not platform implementation.

Disallow business/runtime implementation such as:

- FastAPI routers/use cases/repositories;
- database drivers or SQL migrations/functions;
- authentication providers/JWT verification implementation;
- Casbin policies/enforcers;
- LangGraph nodes/graphs;
- channel adapters/webhook handlers;
- React application code;
- deployment/IaC resources;
- runtime observability SDK initialization.

Validation scripts used to lint/test/build contracts are permitted.

### H. Quality and security gates

Provide one local command and one CI workflow that execute the same blocking checks. At minimum:

- YAML/JSON parse validation;
- JSON Schema meta-validation;
- OpenAPI/AsyncAPI validation when such artifacts exist;
- `$ref` resolution;
- example/fixture validation;
- catalog validation;
- duplicate ID/version detection;
- semantic-version validation;
- backward-compatibility tests;
- prohibited multi-tenant construct scan;
- prohibited implementation-code scan;
- test suite;
- lint/type checks for repository tooling;
- secret scan;
- dependency vulnerability scan for tooling dependencies.

Do not weaken or bypass a gate to obtain green CI.

## Scope exclusions for M0

Do **not** implement:

- business endpoints or business rules;
- authorization policies;
- authentication flows;
- database stored functions/migrations;
- PgBouncer configuration;
- LangGraph graphs/nodes;
- channel-specific integrations;
- admin web UI;
- deployment infrastructure;
- shared runtime utilities/SDKs;
- code generation clients consumed at runtime.

Those belong to their owning repositories/milestones.

## Contract ownership nuance

`ai-business-database` explicitly owns its **database contracts** because those contracts describe stored-function/database interfaces and migration compatibility. `ai-business-contracts` must not absorb SQL/database implementation or duplicate database-contract authority. The contracts repository may catalog or reference cross-repository dependencies, but it must not become the owner of database implementation contracts.

## Normative contract standard

Implement contract identifiers, schema dialects, catalog records, compatibility output, and consumer lock semantics according to `CONTRACT_STANDARD.md`.

## Definition of done

M0 is done only when all acceptance criteria pass with recorded evidence, the independent auditor returns `PASS`, the deliverable bundle is reproducible, and the contracts-side cross-repository compatibility metadata is ready for the platform M0 gate.
