# ACCEPTANCE_CRITERIA.md

## Verdict model

Each criterion is `PASS` or `FAIL`; blocking criteria cannot be waived inside M0. `NOT RUN` is treated as `FAIL` for milestone completion.

### Foundation and boundary

| ID | Criterion | Evidence |
|---|---|---|
| M0-CON-001 | Repository purpose explicitly states contracts/governance only; no shared business implementation. | README + boundary scan |
| M0-CON-002 | Frozen eight-repository authority map is documented without collapsing responsibilities. | governance/ownership + catalog/matrix |
| M0-CON-003 | Contract-bearing paths contain no prohibited multi-tenant constructs. | negative scanner + mutation test |
| M0-CON-004 | No implementation code from API, DB, auth, agent runtime, channel gateway, admin web, or infrastructure is present/imported. | boundary scanner + mutation test |
| M0-CON-005 | Database/stored-function contract ownership remains assigned to `ai-business-database`; no SQL/migrations/PgBouncer config exists here. | repository scan + governance text |

### Contract model

| ID | Criterion | Evidence |
|---|---|---|
| M0-CON-010 | Canonical directories exist for OpenAPI, AsyncAPI, JSON Schema, examples, catalog, compatibility, governance, scripts, tests. | tree evidence |
| M0-CON-011 | Foundation error-envelope schema is valid, versioned, and has passing/failing fixtures. | schema + tests |
| M0-CON-012 | Foundation request/correlation metadata schema is valid, versioned, contains no secret/PII fields, and has fixtures. | schema + tests |
| M0-CON-013 | Foundation event-envelope schema is valid, versioned, transport-neutral, and has fixtures. | schema + tests |
| M0-CON-014 | Contract-metadata schema captures stable ID, SemVer, lifecycle, owner, consumers, type, source, compatibility mode. | schema + catalog validation |
| M0-CON-015 | Every contract in the catalog has exactly one owner and a unique `(contract_id, version)` tuple. | catalog tests |
| M0-CON-016 | All local `$ref`/schema references resolve from a clean checkout. | reference checker |
| M0-CON-017 | All committed examples validate against their declared contract versions. | example validator |

### Governance and compatibility

| ID | Criterion | Evidence |
|---|---|---|
| M0-CON-020 | Semantic-versioning policy defines major/minor/patch contract semantics. | governance/versioning |
| M0-CON-021 | Contract change process defines proposal, owner review, compatibility check, consumer impact, release, deprecation, retirement. | governance/change process |
| M0-CON-022 | Released contract artifacts are immutable; corrections require a new version. | release policy + release test |
| M0-CON-023 | Production consumers are required to pin version plus integrity metadata; mutable-branch-only consumption is forbidden. | lock template + policy |
| M0-CON-024 | Compatibility checker detects operation/message/field removal or rename. | breaking fixture test |
| M0-CON-025 | Compatibility checker detects incompatible type changes. | breaking fixture test |
| M0-CON-026 | Compatibility checker detects newly required request/input fields. | breaking fixture test |
| M0-CON-027 | Compatibility checker detects narrowing of allowed values. | breaking fixture test |
| M0-CON-028 | Compatibility policy flags enum expansion/new variants as review-required where exhaustive consumers may break. | policy + test/metadata |
| M0-CON-029 | Invalid references and duplicate IDs/versions fail validation. | negative fixtures |

### Build, CI, security, release

| ID | Criterion | Evidence |
|---|---|---|
| M0-CON-030 | One local quality-gate command runs every blocking repository validation. | quality_gate output |
| M0-CON-031 | CI runs the same underlying blocking checks as the local quality gate. | workflow inspection + CI evidence |
| M0-CON-032 | Tooling lint and static type checks pass. | command output |
| M0-CON-033 | Test suite passes from a clean checkout. | pytest output |
| M0-CON-034 | Secret scan passes or only approved false positives remain. | scanner output |
| M0-CON-035 | Tooling dependency vulnerability scan is executed and blocking policy is documented. | audit output + policy |
| M0-CON-036 | Contract bundle, manifest, checksums, compatibility summary, and machine-readable M0 summary are reproducibly generated. | dist hashes + rebuild comparison |
| M0-CON-037 | Bundle contents contain contract/governance artifacts only and exclude tests, local caches, secrets, and unrelated implementation. | bundle listing test |
| M0-CON-038 | Release manifest identifies commit SHA and each contract source checksum. | manifest validation |

### Cross-repository readiness and evidence

| ID | Criterion | Evidence |
|---|---|---|
| M0-CON-040 | Platform M0 compatibility matrix lists all eight repositories and preserves authority boundaries. | matrix validation |
| M0-CON-041 | Contracts repo publishes the metadata needed for consumer version/checksum verification. | manifest + lock template |
| M0-CON-042 | Platform gate semantics fail closed on version/hash/required-contract mismatch. | negative compatibility fixture |
| M0-CON-043 | Evidence files record real command, timestamp, commit SHA, exit code, and artifact hash where applicable. | evidence audit |
| M0-CON-044 | `AUDITOR.md` read-only audit returns `PASS` with no unresolved blocking findings. | audit evidence |
| M0-CON-045 | `DELIVERY_REPORT.md` is completed from evidence only and contains no unsupported pass claims. | delivery report audit |

## M0 pass formula

```text
Contracts M0 PASS = ALL(M0-CON-001 .. M0-CON-045 applicable criteria) == PASS
                   AND Auditor == PASS
                   AND Required release/evidence artifacts exist
```

Platform M0 remains a separate composite verdict across all eight repository M0s plus the cross-repository compatibility gate.
