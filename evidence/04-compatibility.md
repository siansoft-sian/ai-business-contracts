# Evidence — Compatibility Validation

EP-03 Status: **COMPLETE** (compatibility is deterministic, tested, and machine-readable)

- Repository: `ai-business-contracts`
- Repository URL: `https://github.com/siansoft-sian/ai-business-contracts.git`
- Branch: `main`
- Audited commit: `d65cd872d205dd0cee92afc438b370143054fc83`
- Timestamp UTC: `2026-08-07T19:26Z`
- Working tree at observation: clean
- Executed by: EP-03 per `execution-prompts/EP-03-GOVERNANCE-AND-COMPATIBILITY.md`

> `CROSS_REPO_COMPATIBILITY.md` was read for the first time this round. It is
> audit authority #4 in `AUDITOR.md` and had not been consulted in EP-00–EP-02.
> It shaped two decisions here: the result document is the artifact the platform
> gate consumes, and the gate must **fail closed** — never silently choose a
> newer version, never treat a missing comparison as a passing one.

## 0. Commit model

```text
55b4408  docs(evidence): record EP-02 contract validation   ← EP-02 final state
│
d65cd87  feat(compatibility): add compatibility engine,     ← EP-03 work
│        fixtures, and governance                             ALL FIGURES HERE
│
I        docs(evidence): record EP-03 compatibility         ← this document
```

`git status --porcelain` at `d65cd87` produced no output (exit `0`).

## 1. The classification rule (EP-03 instruction 2)

`scripts/check_compatibility.py` places every difference in exactly one class.
The boundary is drawn by **what can be proven**, not by what feels safe.

| Class | Meaning | Gate effect |
|---|---|---|
| `breaking` | demonstrated to reject data or usage the baseline accepted | fails, unless covered by a declared major transition |
| `review_required` | cannot be shown safe | blocks automatic approval until the owner records a decision |
| `compatible` | proven not to affect existing consumers | passes |

**The asymmetry is deliberate.** A change is never called compatible because
nothing disproved it; only when the structure shows it harmless. Everything
else is escalated. This is the direct implementation of `HARNESS.md` §6: *"An
additive change is not automatically safe."*

### 1.1 Deciding an undecidable change — witnesses

Regular-expression strictness cannot be decided in general. Rather than guess,
the engine tests the values the baseline **itself declares valid** — its
`examples` — against the candidate pattern:

- a declared-valid value the candidate rejects **proves** the tightening →
  `breaking`, with the failing value recorded as `witness`;
- no such value → `review_required`. Never `compatible`.

Demonstrated at `breaking/tighten-regex`: baseline `^ref_[a-z0-9]{4,32}$`
declares `ref_zz99` valid; candidate `^ref_[a-z0-9]{8,32}$` rejects it. The
finding carries `"witness": "ref_zz99"`.

Contrast `review-required/regex-changed-without-witness`, where the pattern is
rewritten to `^ref_[a-zA-Z0-9]{4,32}$` and no declared example is rejected. The
engine escalates rather than clearing it, and the finding carries no witness.

Numeric and length bounds are decidable, so narrowing them is `breaking`
without needing a witness.

## 2. Fixtures — every mandatory Layer D case (EP-03 instruction 3)

19 curated baseline/candidate pairs under `compatibility/fixtures/`, each with a
`README.md` stating what it demonstrates. `review-required/` was added
alongside the two directories `TARGET_REPOSITORY_TREE.md` names, so the third
class is explicit rather than implied.

### 2.1 Full sweep at `d65cd87`

```bash
$ python3 scripts/check_compatibility.py --baseline <case>/baseline \
      --candidate <case>/candidate --checked-at 2026-08-07T19:00:00Z --json
```

| Class | Case | Verdict | breaking / review / compatible |
|---|---|---|---|
| compatible | `add-optional-property` | `pass` | 0 / 0 / 1 |
| compatible | `add-optional-response-metadata` | `pass` | 0 / 0 / 1 |
| compatible | `documentation-only` | `pass` | 0 / 0 / 1 |
| compatible | `add-new-contract-id` | `pass` | 0 / 0 / 1 |
| breaking | `remove-field` | `fail` | 1 / 0 / 0 |
| breaking | `rename-field` | `fail` | 1 / 0 / 0 |
| breaking | `type-change-string-to-integer` | `fail` | 1 / 0 / 0 |
| breaking | `optional-input-becomes-required` | `fail` | 1 / 0 / 0 |
| breaking | `remove-enum-value` | `fail` | 1 / 0 / 0 |
| breaking | `tighten-regex` | `fail` | 1 / 0 / 0 |
| breaking | `narrow-numeric-range` | `fail` | 1 / 0 / 0 |
| breaking | `extensible-becomes-closed` | `fail` | 1 / 0 / 0 |
| breaking | `unresolvable-reference` | `fail` | 1 / 0 / 1 |
| breaking | `duplicate-contract-version` | `fail` | 1 / 0 / 0 |
| breaking | `released-version-content-changed` | `fail` | 2 / 0 / 0 |
| breaking | `removal-approved-by-major-bump` | **`pass`** | 1 / 0 / 0 |
| review-required | `enum-expansion` | `review_required` | 0 / 1 / 0 |
| review-required | `new-variant-for-exhaustive-matchers` | `review_required` | 0 / 1 / 0 |
| review-required | `regex-changed-without-witness` | `review_required` | 0 / 1 / 0 |

### 2.2 Deferred, and why

`TEST_PLAN.md` Layer D lists "remove endpoint/message **when OpenAPI/AsyncAPI
fixtures are enabled**". `contracts/openapi/` and `contracts/asyncapi/` hold no
artifacts, so that case is **not covered** and is recorded as finding 4 rather
than faked with a JSON Schema stand-in. Doing so would have produced a green
row proving nothing about the artifact family it names.

## 3. Major-version approval (EP-03 instruction 4)

`CONTRACT_STANDARD.md` §8: a non-empty `breaking` list fails *unless the
candidate is an approved major-version transition*.

`breaking/removal-approved-by-major-bump` and `breaking/remove-field` contain
**the identical removal**. The only difference is the candidate's version:

| Fixture | Candidate version | Verdict | `approved_major_transition` | Breaking listed |
|---|---|---|---|---|
| `remove-field` | `1.1.0` | `fail` | `false` | yes |
| `removal-approved-by-major-bump` | `2.0.0` | `pass` | `true` | **yes** |

`test_same_change_without_a_major_bump_fails` asserts both produce the same
change class, so the difference is the declaration and nothing else. The
breaking finding remains in the document either way: **an approved break is
declared, not hidden**, and a reader of the result can always see what changed.

## 4. Immutability is enforced, not just documented (`M0-CON-022`)

The engine reports the same `(contract_id, version)` with different content as
`released-version-content-changed`, a breaking finding.

Re-releasing a changed `0.1.0` is therefore a **build failure**, not a policy
violation someone might notice in review. This is what makes a consumer's
`bundle_sha256` pin meaningful: if a published version's content could change,
the pin would verify nothing.

Demonstrated by `breaking/released-version-content-changed` → `fail`, and
asserted by `test_immutability_violation_is_detected`.

## 5. Baseline behaviour (EP-03 instruction 7)

No release exists, so there is nothing to compare against.
`compatibility/baseline.yaml` records this explicitly:

```yaml
baseline_release: null
first_published_baseline: "0.1.0"
```

```bash
$ python3 scripts/check_compatibility.py
```

Exit `0`:

```text
check_compatibility: NO BASELINE - no prior release exists, so nothing was
compared. The engine is proven by the fixtures under compatibility/fixtures/;
the first published baseline will be 0.1.0.
```

The verdict is `no-baseline`, **not `pass`**. A pass would read as "compared and
found compatible", which would be false. `CROSS_REPO_COMPATIBILITY.md` requires
the gate to fail closed, and a gate reporting success when it did not run is
worse than one reporting nothing. `test_no_baseline_is_reported_explicitly_not_as_a_pass`
asserts the distinction.

## 6. The result document is itself a governed contract

`urn:ai-business:contracts:common:compatibility-result:v1` — a fifth
catalogued contract, added so the platform gate validates the summary it
consumes rather than trusting the shape our tooling happens to emit.

Every emitted document is validated against it in
`test_emitted_document_validates_against_its_contract`, parameterised across
all 19 fixtures, so the engine cannot drift from `CONTRACT_STANDARD.md` §8.

Adding it correctly broke three EP-02 tests that pinned the contract count at
four (`test_all_four_foundation_schemas_exist`, `test_every_foundation_contract_is_registered`,
`test_examples_exist_for_every_contract`). That is the catalog/tree agreement
check from EP-02 working as designed, and the tests were updated to expect five.

## 7. Command results at `d65cd87`

| Command | Exit | Result |
|---|---:|---|
| `validate_contracts.py` | `0` | 5 schemas valid |
| `check_references.py` | `0` | references resolve |
| `validate_examples.py` | `0` | 9 examples validate |
| `validate_catalog.py` | `0` | 5 entries valid and consistent with the tree |
| `check_no_multitenancy.py` | `0` | PASS |
| `check_no_implementation_code.py` | `0` | PASS |
| `check_compatibility.py` | `0` | `no-baseline`, stated explicitly |
| `pytest -q` | `0` | **170 passed** (109 at EP-02) |
| `ruff check` | `0` | `All checks passed!` |
| `mypy` (strict) | `0` | `Success: no issues found in 17 source files` |

### 7.1 CLI exit codes follow the verdict

The exit code is the contract CI branches on:

| Fixture | Verdict | Exit |
|---|---|---:|
| `compatible/add-optional-property` | `pass` | `0` |
| `review-required/enum-expansion` | `review_required` | `0` |
| `breaking/remove-field` | `fail` | **`1`** |
| `breaking/removal-approved-by-major-bump` | `pass` | `0` |

`review_required` exits `0` deliberately: it blocks *automatic approval*, not
the build. The block is a human decision recorded in the pull request
(`governance/CHANGE_PROCESS.md`), not a red pipeline.

### 7.2 Determinism

`test_output_is_deterministic_for_a_fixed_timestamp` runs the same comparison
twice with a fixed `--checked-at` and asserts byte-identical output. EP-05
needs this: a release artifact that changes between builds cannot be
checksummed meaningfully.

## 8. Clean-checkout verification

Cloned to a temporary directory at `d65cd87`, tooling installed, everything
re-run there:

| Check | Exit |
|---|---:|
| all 7 gates | `0` each |
| `pytest -q` | `0` — 170 passed |
| 19-fixture sweep | every case classified as in §2.1 |

## 9. Governance completion (EP-03 instruction 1)

| Document | State | Covers |
|---|---|---|
| `governance/VERSIONING.md` | complete | change class → required bump table; `MAJOR` produces a new `$id`, not an edit; `0.x` is not a licence to break silently |
| `governance/CHANGE_PROCESS.md` | complete | seven stages; the owner decision record that resolves `review_required`; major-version approval; emergency handling; what may never be done |
| `governance/DEPRECATION.md` | complete | lifecycle state machine; six-month minimum window; five retirement preconditions |
| `governance/RELEASES.md` | policy complete | immutability; artifacts; bundle exclusions; pinning; fail-closed |
| `governance/OWNERSHIP.md` | complete | authority map; enforcement table updated with the live checks |
| `governance/CONTRACT_POLICY.md` | complete | what a contract is; where each rule lives |
| `compatibility/policy.md` | complete | the three classes; witness rule; deferred coverage |

The owner decision record is worth singling out. `review_required` is resolved
only by a recorded decision naming **which consumers were checked** — "no
consumer matches exhaustively" is a claim about specific consumers, and a
generic basis is not a decision.

`compatibility/policy.md` sits on the scanned release surface (EP-01 finding 6),
so it discusses change classes without naming prohibited constructs; that prose
lives in `governance/`.

## 10. Artifacts / hashes

Blob hashes at `d65cd87`. Tracked files: **169**. Contract schemas: 5. Fixture
schemas: 40 across 19 cases.

| Artifact | SHA-256 |
|---|---|
| `scripts/check_compatibility.py` | `cad2c8ff19afb7f329b06c08845edbefc05b0afc762a8abed3a221145951631d` |
| `contracts/schemas/common/compatibility-result.v1.schema.json` | `3d3c5da22a3bc651b2e4192f3995096bccd2d9049e85880706c758b918d1fbc3` |
| `compatibility/baseline.yaml` | `8eb753e8d389228270178f1f2f8be73191c11e3440401c699b65cfad85a5dd81` |
| `compatibility/policy.md` | `573653878176c5405386c2209c8cf7885e26397f7c6b01a8e7ccbead5e9455c0` |
| `catalog/contract-catalog.yaml` | `dde63b2f66a372b44eb1980a5bb282397f34dea4275134f3f1f807010a2889bc` |
| `governance/VERSIONING.md` | `d1d90cdda95049b54f53e7e0434efcfa6ee36715d4ca5e974b90073c06c81ab0` |
| `governance/CHANGE_PROCESS.md` | `e0387b7a7083d4e87ce25cc39eb344066bbb0e29ab1f41e9f3d169514d7deef5` |
| `governance/DEPRECATION.md` | `03e2d5d11ef412d433f4fc6fe9e8b37627cfed84bb79a1e3f4c6ace38d091de9` |
| `governance/RELEASES.md` | `e28eb3f924728fc96ee47669d81fb9acf026375986f8ec2359498209bd213af9` |
| `governance/OWNERSHIP.md` | `47ef3a0d39bb9a45b5e4903a7c66443d906d4cd53326c9ad9e1d736c0f4c4aaa` |
| `governance/CONTRACT_POLICY.md` | `d445716cbb44886846af6d0ca8c048193ccac7c59ea378f75d489bbc40258e36` |
| `tests/test_compatibility.py` | `4354e29408874509bcc033444c8bc6c485f832da5b05295972c67d07fbe48a1f` |

## 11. Acceptance criteria status

| Criterion | Status | Basis |
|---|---|---|
| `M0-CON-020` | **PASS** | `governance/VERSIONING.md` defines major/minor/patch by consumer effect and maps every change class the engine emits to a required bump |
| `M0-CON-021` | **PASS** | `governance/CHANGE_PROCESS.md` defines proposal, owner review, compatibility check, consumer impact, release, deprecation, retirement; `DEPRECATION.md` completes the last two |
| `M0-CON-022` | **PASS** | immutability is machine-enforced — `released-version-content-changed` fails the gate (§4), proven by fixture and test. **EP-05 adds the bundle-level half** (`M0-CON-036`–`038`) |
| `M0-CON-024` | **PASS** | `remove-field`, `rename-field`, `contract-removed` detected (§2.1) |
| `M0-CON-025` | **PASS** | `type-change-string-to-integer` detected; widening classified compatible instead |
| `M0-CON-026` | **PASS** | `optional-input-becomes-required` and `field-added-required` detected |
| `M0-CON-027` | **PASS** | `remove-enum-value`, `narrow-numeric-range`, and witness-proven `tighten-regex` detected |
| `M0-CON-028` | **PASS** | `enum-expansion` and `new-variant-for-exhaustive-matchers` classified `review_required`, never compatible |
| `M0-CON-029` | **PASS** (reaffirmed) | unresolvable reference and duplicate `(contract_id, version)` fail in both the EP-02 validators and the compatibility engine |
| `M0-CON-023` | **NOT RUN** | lock template is an EP-04 deliverable; `RELEASES.md` states the policy half only |
| `M0-CON-002` | **NOT RUN** | platform matrix is EP-04 |
| `M0-CON-042` | **NOT RUN** | the evidence template lists it here, but platform-gate mismatch semantics are EP-04 instruction 4 |

### Not claimed

`M0-CON-030`–`041` and `043`–`045` remain `NOT RUN`. `ruff`, `mypy`, and 170
tests pass at this commit, but `M0-CON-032`/`033` are evidenced by EP-05's
quality gate. `detect-secrets` still has not run, so `M0-CON-034` stands
unclaimed and EP-00 finding 8 holds.

## 12. Unresolved findings

**Blocking:** none.

**Carried forward:**

1. `M0-CON-002`, `023`, and `042` require EP-04's lock template and platform
   matrix.
2. `evidence/05-quality-security.md` … `08-audit-verdict.md` remain `NOT RUN`.
3. `x-contract-version` is still not cross-checked against the catalog version
   (EP-02 finding 5). The compatibility engine reads `x-contract-version` to
   decide major transitions, so a schema and catalog disagreeing on the version
   would let a breaking change look approved. **This is now more than cosmetic
   and should be closed in EP-04 or EP-05.**
4. **New:** endpoint/message removal is uncovered while `contracts/openapi/` and
   `contracts/asyncapi/` are empty (§2.2). Fixtures must be added with the first
   such contract. EP-00 §5.1's obligation — specification-level AsyncAPI
   conformance before the first AsyncAPI contract goes active — still stands.
5. **New:** the engine compares JSON Schema structure. It follows a same-document
   `$ref` one hop so `$defs` are compared by value, but it does not resolve
   cross-schema URN references during comparison. A breaking change made inside
   a *referenced* contract is caught when that contract is itself compared, not
   transitively through its referrer. Adequate at M0, where every contract is in
   the compared set; it would need revisiting if contracts were ever compared
   in isolation.

**Carried to EP-05 (unchanged):**

6. `jq`, `gitleaks`, `trivy` absent; the `detect-secrets`/`pip-audit`
   substitution must be implemented and evidenced.
7. The EP-00 secret grep is an observation, not a gate.

## 13. Exit condition

`EP-03-GOVERNANCE-AND-COMPATIBILITY.md` requires: *"Compatibility behavior is
deterministic, tested, and produces structured results usable by CI and the
platform gate."*

**Met.**

- **Deterministic** — byte-identical output for identical inputs and a fixed
  timestamp (§7.2), verified from a clean checkout (§8).
- **Tested** — 19 fixtures covering every mandatory `TEST_PLAN.md` Layer D case
  except the explicitly deferred one, with the class asserted per fixture and a
  coverage test that fails if a case loses its fixture.
- **Structured and usable** — the result document is a governed contract,
  validated on every fixture, with exit codes CI branches on.

**EP-04 has not been started.** No consumer lock template, no platform matrix.
`M0-CON-002`, `023`, `042`, and `030`–`045` remain `NOT RUN`; M0 does not pass
at EP-03.
