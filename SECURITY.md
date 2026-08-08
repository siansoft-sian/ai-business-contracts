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

## Secret scan: findings, the digest rule, and the baseline

`scripts/check_secrets.py` runs `detect-secrets` over every tracked file.
**Any finding that is not explained fails the build.** There is no warn-only
mode.

A finding is explained in exactly one of two ways.

### 1. The digest rule

This repository is *required* to contain high-entropy hex strings. The release
manifest is built from SHA-256 checksums, contract examples declare them, and a
consumer lock is meaningless without them. An entropy detector cannot tell a
checksum from a credential, and it should not try.

So a finding is discarded only when the line it sits on assigns a value of
40–64 lowercase hex characters to a field whose name ends in `sha256` or is
`commit_sha`. Both halves matter: naming a field `api_sha256` does not launder
a credential, because the value must still have the shape of a digest, and a
bare hex string with no digest field name stays blocking.

This is checked on **every run**, not recorded once. The alternative — a
baseline entry per finding — rots: baseline entries are keyed by line number,
and `evidence/m0-summary.json` is regenerated on every gate run with digests
that move. Re-baselining each run would be auto-suppression wearing a
baseline's clothes.

`tests/test_quality_gate.py` proves the rule both ways: digest assignments are
exempt, and the same hex string as an `api_key`, a `token`, a bare value, or
inside prose is not.

### 2. The reviewed baseline

`.secrets.baseline` is the approved false-positive mechanism required by
`HARNESS.md` section 9, for anything the digest rule does not cover. It is
currently **empty**, which is the honest state: every real finding here is a
checksum or a commit SHA. Rules for using it:

1. A finding may be recorded as `is_secret: false` **only after** it has been
   inspected and shown not to be a credential.
2. An entry with no `is_secret` verdict is an unreviewed suppression and is not
   honoured — `check_secrets.py` ignores it and the finding stays blocking.
3. Entries are matched by `(filename, hashed_secret)`, not by line number, so
   reflowing a file does not resurrect a reviewed finding.
4. `pragma: allowlist secret` inline comments are not used. An inline
   suppression is invisible in review; a baseline entry is a reviewable diff.

The baseline file itself is not scanned. It stores SHA-1 *hashes* of findings
rather than the findings — that is the point of the format — and scanning it
would flag the record of a reviewed finding, making the mechanism unusable the
moment it was used.

### Writing tests about secrets

A live secret scan constrains its own test suite: a tracked file containing a
credential-shaped literal is exactly what the scan rejects, and "it is only
there to test the scanner" is the justification every such string arrives with.
Test credentials and digest witnesses are therefore **assembled at runtime**,
never written as literals. The file the scanner is pointed at still contains
the real value, so the proof is unchanged.

If the scanner cannot run at all, `check_secrets.py` exits `2` and the gate
fails. A scan that did not happen has not passed.

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
