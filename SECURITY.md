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

All of these run inside `scripts/quality_gate.sh`, which CI invokes unchanged.

- **Secret scan** — `detect-secrets`, blocking. See below.
- **Dependency vulnerability audit** — `pip-audit`, blocking. See below.
- **Boundary scanners** — reject implementation code and multi-tenant
  constructs on the release surface.

A blocking gate is never weakened to obtain a green result. If a gate cannot
pass, the milestone is reported as blocked.

## Secret scan: findings and the baseline

The gate runs `detect-secrets-hook` over every tracked file against
`.secrets.baseline`. **Any finding the baseline does not already account for
fails the build.** There is no warn-only mode.

`.secrets.baseline` is the approved false-positive mechanism required by
`HARNESS.md` section 9. Rules for using it:

1. A finding may be recorded as `is_secret: false` **only after** it has been
   inspected and shown not to be a credential.
2. Every entry must be audited. An entry with no `is_secret` verdict is an
   unreviewed suppression and is treated as a defect.
3. The suppression claim is itself verified.
   `tests/test_quality_gate.py::test_every_suppressed_finding_is_provably_a_digest_not_a_secret`
   re-reads each suppressed line and requires it to be an assignment of a
   SHA-256 checksum or a commit SHA — values that are digests by contract.
   A suppression on any other kind of line fails the test.
4. `pragma: allowlist secret` inline comments are not used. An inline
   suppression is invisible to review; a baseline entry is a reviewable diff.

The current baseline contains only checksum and commit-SHA fields inside
contract examples and cross-repository lock fixtures. Those are integrity
values that contracts require to be present — the release manifest and consumer
lock schemas both declare them — so removing them is not an option, and
suppressing them is verified rather than asserted.

## Dependency vulnerability audit: blocking policy

The gate runs `pip-audit --strict` over the installed validation toolchain.
This repository declares **no runtime dependencies** — it is never imported —
so the entire dependency surface is tooling that builds and validates
contracts. A compromise there is a supply-chain risk to the artifacts, which
is why the audit blocks rather than warns.

| Finding | Action |
|---|---|
| Vulnerability with a fixed version available | **Blocking.** Upgrade and re-lock. There is no deferral. |
| Vulnerability with no fix available | **Blocking until triaged.** Record the advisory ID, the affected package, why the code path is or is not reachable from contract validation, and the mitigation, in the evidence file for the release. Only then may it be pinned to a specific advisory ID with an expiry. |
| Audit cannot reach the advisory database | **Blocking.** An audit that did not run has not passed. `--strict` makes an unresolvable dependency a failure rather than a skipped entry, and the gate records the non-zero exit rather than tolerating it. |

Blanket ignore flags are not used. A suppression names one advisory, one
package, and one reason.

## Release integrity

Released contract artifacts are immutable and carry SHA-256 checksums for both
the manifest and the bundle. Consumers verify version plus integrity hash;
consuming a mutable branch as a production dependency is forbidden. Corrections
are published as a new version, never as an edit to a released artifact.
