# HARNESS.md

## Purpose

This harness governs execution of `ai-business-contracts` M0 by a coding agent or human implementer. It is stricter than ordinary task instructions because this repository becomes a platform boundary.

## 1. Source-of-truth precedence

Use this precedence when requirements conflict:

1. The frozen 8-repository platform architecture in `PROMPT.md`.
2. `ACCEPTANCE_CRITERIA.md`.
3. `TEST_PLAN.md`.
4. Existing repository code/docs that do not conflict with 1–3.
5. Implementation convenience.

Never preserve a legacy pattern merely because it already exists if it conflicts with the frozen architecture.

## 2. Execution protocol

Execute the milestone in this order:

1. **Preflight** — inventory repository contents; identify legacy or conflicting material.
2. **Boundary cleanup** — remove/replace prohibited multi-tenant or implementation content in contract-bearing scope.
3. **Scaffold** — create canonical directories, governance docs, tooling, and tests.
4. **Foundation contracts** — implement only the minimal platform primitives required by M0.
5. **Validation** — implement local quality gate and CI equivalent.
6. **Compatibility** — implement backward-compatibility fixtures and release/lock metadata.
7. **Evidence** — capture actual commands, exit codes, and artifact hashes.
8. **Audit** — run the independent auditor in read-only mode.
9. **Delivery** — complete `DELIVERY_REPORT.md` from evidence only.

Do not jump directly to implementation without preflight evidence.

## 3. Architectural invariants

### 3.1 Contracts only

Allowed:

- OpenAPI/AsyncAPI/JSON Schema source;
- examples and fixtures;
- contract catalog and compatibility metadata;
- governance documentation;
- validation/build/release scripts;
- tests for contracts/tooling;
- CI configuration for this repository.

Forbidden:

- shared business logic;
- runtime application modules;
- database access code;
- auth implementation;
- business authorization implementation;
- LangGraph implementation;
- channel adapter implementation;
- frontend code;
- deployment/IaC resources.

### 3.2 No cross-repository implementation imports

No source in this repository may import implementation code from any of the other seven repositories. Likewise, this M0 must not create a runtime package intended to be imported as shared implementation.

### 3.3 No multi-tenancy

Contract-bearing paths must contain no tenant identifier/header/context/routing/storage/authorization semantics. The automated negative test is mandatory.

### 3.4 Database contract ownership

Do not relocate database stored-function contracts into this repo. `ai-business-database` remains authoritative for PostgreSQL/Sqitch/stored-function/PgBouncer database contracts.

## 4. Contract design rules

- Prefer explicit schemas over prose-only contracts.
- Every published contract has a stable ID and semantic version.
- Every contract has one authoritative owner.
- Every schema reference resolves from a clean checkout.
- Examples are executable validation fixtures, not decorative samples.
- Error codes are stable identifiers; messages are safe for clients but are not compatibility keys.
- Contract payloads must not contain secrets, raw credentials, bearer tokens, connection strings, or realistic personal data.
- Date/time fields use explicit ISO-8601/RFC-3339 semantics and timezone rules.
- Identifiers declare format and constraints rather than relying on undocumented conventions.
- Unknown/additional fields policy must be explicit per schema.
- Avoid embedding implementation technology in a transport-neutral contract unless the technology is itself part of the interface.

## 5. Versioning rules

- Initial M0 contract foundation release: `0.1.0` unless an existing repository history requires a different non-conflicting version.
- `MAJOR` — incompatible contract change.
- `MINOR` — backward-compatible capability/addition.
- `PATCH` — clarification/metadata/bug fix that does not change consumer-visible semantics.
- Released artifacts are immutable. Corrections produce a new version.
- Production consumers pin a released version and integrity hash; no `main`, mutable branch, or floating range as the sole production pin.

## 6. Compatibility discipline

A compatibility checker must operate against a declared baseline release/ref. If no prior release exists, M0 uses curated compatibility fixtures to prove the engine before the first publication.

A change is breaking unless proven otherwise when it:

- removes/renames a published operation, message, schema, field, or required response;
- changes a field type incompatibly;
- adds a new required request/input field without a default/compatible transition;
- narrows allowed values;
- changes identifier semantics;
- changes error-code semantics relied on by consumers;
- changes a payload from extensible to closed in a way that rejects previously valid data.

An additive change is not automatically safe. Enum expansion, new response variants, or new event types may break closed/exhaustive consumers and require explicit review.

## 7. Evidence discipline

Evidence is factual output, not narrative confidence.

For every blocking gate record:

- exact command;
- UTC timestamp;
- commit SHA;
- exit code;
- relevant output summary;
- artifact path when applicable;
- checksum/hash for release artifacts.

Do not write `PASS` if the command was not executed. Mark unavailable checks `NOT RUN` with a reason; `NOT RUN` on a blocking criterion means M0 does not pass.

## 8. Testing discipline

- Include positive and negative fixtures.
- Tests must fail if a prohibited tenant construct is inserted into a contract fixture.
- Tests must fail if implementation-code patterns are inserted into a guarded path.
- Compatibility tests must include at least one known-compatible and one known-breaking change for each supported contract family present in M0.
- CI and local quality gate must invoke the same underlying commands/scripts.

## 9. Security discipline

- Never commit real secrets.
- Secret scanner findings are blocking unless documented as verified false positives using the repository's approved baseline mechanism.
- Dependency vulnerabilities in contract tooling are triaged explicitly; do not silently suppress them.
- Do not log schema fixture payloads if they may contain sensitive values.

## 10. Stop conditions

Stop and report a blocked milestone rather than guessing when:

- a required architecture decision cannot be reconciled without changing the frozen 8-repo boundaries;
- the compatibility engine cannot reliably determine a required breaking-change class;
- a blocking security/quality gate cannot pass without weakening the gate;
- a required artifact cannot be reproduced from a clean checkout.

Do not solve a repository-boundary conflict by moving implementation into `ai-business-contracts`.
