# Security Policy

## Scope

`ai-business-contracts` publishes interface contracts and governance. It runs
no service, stores no data, and is not imported as a runtime dependency, so
its security surface is the **integrity of published contracts** and the
**absence of sensitive material in contract source**.

## Reporting a vulnerability

Report privately to the repository owner. Do not open a public issue for an
unpublished vulnerability, and do not include real credentials or production
payloads in the report.

## Contract content rules

`HARNESS.md` section 4 and `CONTRACT_STANDARD.md` are binding. Contract
payloads, examples, and fixtures must never contain:

- secrets, raw credentials, bearer tokens, API keys, or private keys;
- database connection strings or PgBouncer credentials;
- realistic personal data - use synthetic identifiers and example domains;
- internal stack traces or provider error details.

Error envelopes carry a stable machine-readable code and a client-safe
message. Internal diagnostic detail never belongs in a contract.

## Automated checks

- **Secret scan** - `detect-secrets`, blocking. Findings are blocking unless
  documented as verified false positives through the approved baseline
  mechanism. (Implemented in EP-05.)
- **Dependency vulnerability audit** - `pip-audit` over validation tooling,
  triaged explicitly rather than silently suppressed. (Implemented in EP-05.)
- **Boundary scanners** - reject implementation code and multi-tenant
  constructs on the release surface. (Implemented in EP-01.)

A blocking gate is never weakened to obtain a green result. If a gate cannot
pass, the milestone is reported as blocked.

## Release integrity

Released contract artifacts are immutable and carry SHA-256 checksums for both
the manifest and the bundle. Consumers verify version plus integrity hash;
consuming a mutable branch as a production dependency is forbidden. Corrections
are published as a new version, never as an edit to a released artifact.
