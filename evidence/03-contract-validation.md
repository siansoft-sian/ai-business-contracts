# Evidence — Contract, Reference & Catalog Validation

EP-02 Status: **COMPLETE** (foundation contracts exist and validate from a clean checkout)

- Repository: `ai-business-contracts`
- Repository URL: `https://github.com/siansoft-sian/ai-business-contracts.git`
- Branch: `main`
- Audited commit: `db08b4620565e156f9225428b81ce1b29a3f2a04`
- Timestamp UTC: `2026-08-07T18:38:55Z`
- Working tree at observation: clean
- Executed by: EP-02 per `execution-prompts/EP-02-CONTRACT-FOUNDATION.md`

> EP-01 built gates around an empty release surface. EP-02 populates it. The
> validators below are only meaningful because §4 shows each one **failing**
> when a defect is introduced — a validator that cannot fail proves nothing.

## 0. Commit model

Unchanged from EP-00/EP-01: the work is committed first, then observed.

```text
a860f05  docs(evidence): record EP-01 boundary enforcement   ← EP-01 final state
│
db08b46  feat(contracts): add foundation primitives,         ← EP-02 work
│        catalog, and validators                               ALL FIGURES HERE
│
H        docs(evidence): record EP-02 contract validation    ← this document
```

`git status --porcelain` at `db08b46` produced no output (exit `0`).

## 1. Foundation primitives (EP-02 instructions 1–4)

Four JSON Schema Draft 2020-12 contracts, none of which encodes a business
rule or an implementation technology.

| Contract | `$id` | Source |
|---|---|---|
| Error envelope | `urn:ai-business:contracts:common:error-envelope:v1` | `contracts/schemas/common/error-envelope.v1.schema.json` |
| Request/correlation metadata | `urn:ai-business:contracts:common:request-metadata:v1` | `contracts/schemas/common/request-metadata.v1.schema.json` |
| Event envelope | `urn:ai-business:contracts:events:event-envelope:v1` | `contracts/schemas/events/event-envelope.v1.schema.json` |
| Contract metadata / catalog | `urn:ai-business:contracts:common:contract-metadata:v1` | `contracts/schemas/common/contract-metadata.v1.schema.json` |

All four declare `$schema` as Draft 2020-12, carry `title` and
`x-contract-version: 0.1.0`, and follow the `<name>.v<major>.schema.json`
filename form. Identity is asserted by `tests/test_schema_validity.py`, and
`validate_contracts.py` independently rejects a schema that drifts from any of
these rules (§4.1).

### 1.1 Extensibility is a decision, recorded per schema

`CONTRACT_STANDARD.md` requires the unknown-field policy to be explicit. JSON
Schema defaults `additionalProperties` to true, so an author who omits it has
silently chosen a policy. `validate_contracts.py` therefore treats an object
schema without an explicit declaration as a defect — the
`implicit-additional-properties` case in §4.1.

| Schema | Policy | Reason |
|---|---|---|
| error-envelope.v1 | `true` | a payload must be able to gain a field in a MINOR release |
| request-metadata.v1 | `true` | same |
| event-envelope.v1 | `true` | same; `payload` is deliberately unconstrained so payload contracts evolve on their own version line |
| contract-metadata.v1 | **`false`** | control plane: a misspelled catalog key is a mistake, not a forward-compatible addition |

`HARNESS.md` §6 classifies extensible → closed as **breaking**. Starting the
envelopes closed would therefore have locked that decision permanently, so the
open choice is the one that preserves future freedom. The closed catalog is
what makes `complatibility:` fail instead of being ignored (§4.3).

### 1.2 References are real, not decorative

`error-envelope.v1` and `event-envelope.v1` both `$ref` identifier definitions
owned by `request-metadata.v1`:

```json
{ "$ref": "urn:ai-business:contracts:common:request-metadata:v1#/$defs/request_id" }
```

So identifier semantics are defined once, and `M0-CON-016` has something real
to resolve. `contract-metadata.v1` does double duty — its root describes the
**catalog document**, its `$defs.contract_entry` describes **one entry** — so
the catalog is validated by a registered contract rather than by an
unregistered side-schema. 13 references resolve in total.

Resolution is purely local, through a `referencing` registry keyed by the URN
`$id` of each schema. `test_no_network_reference_is_used` asserts no `$ref`
targets an `http(s)` URL, which is what makes "validates from a clean checkout"
achievable rather than dependent on network availability.

### 1.3 Deliberate constraints worth recording

- **`error.code` is a `pattern`, not a closed enum.** Enumerating business
  error codes here would route every new business error through a contracts
  release. Business authority belongs to `ai-business-api`, so this contract
  constrains the *shape* (`^[A-Z][A-Z0-9_]{2,63}$`) and leaves allocation to
  the owning service.
- **`error.message` is documented as not a compatibility key**, per
  `CONTRACT_STANDARD.md` §4, so consumers may not branch on it.
- **`producer` is a closed enum of four services** — api, auth, agent-runtime,
  channel-gateway. admin-web and infrastructure do not emit business events,
  and the contracts repository is not a runtime. Expanding this list is
  additive but `review_required`, since consumers may match exhaustively.
- **`occurred_at` requires UTC with a literal `Z`.** A local offset is
  ambiguous across daylight transitions, so the pattern rejects it (§4.2).
- **No business vocabulary or transport technology** appears in authored text,
  asserted by `test_no_business_rules_or_implementation_technology`.

## 2. Catalog (EP-02 instruction 5)

`catalog/contract-catalog.yaml`, `catalog_version: 0.1.0`, registering all four
primitives. Every entry carries exactly one `owner`, explicit `consumers` drawn
from the frozen eight, a `source` path that must exist, a `lifecycle`, and a
`compatibility` mode.

| Contract | Version | Lifecycle | Owner | Consumers | Compatibility |
|---|---|---|---|---|---|
| error-envelope:v1 | 0.1.0 | active | ai-business-contracts | api, auth, agent-runtime, channel-gateway, admin-web | backward |
| request-metadata:v1 | 0.1.0 | active | ai-business-contracts | api, auth, agent-runtime, channel-gateway, admin-web | backward |
| event-envelope:v1 | 0.1.0 | active | ai-business-contracts | api, auth, agent-runtime, channel-gateway, admin-web | backward |
| contract-metadata:v1 | 0.1.0 | active | ai-business-contracts | ai-business-contracts | backward |

`0.1.0` follows `HARNESS.md` §5; `active` follows the canonical entry in
`CONTRACT_STANDARD.md` §7. Consumer lists are stated per contract rather than
copied: `contract-metadata` is a control-plane artifact consumed by release
tooling and the platform gate, not by any runtime service.

`validate_catalog.py` enforces what a schema cannot: **the tree and the catalog
must agree in both directions.** A contract added to `contracts/schemas/` but
never registered fails as `uncatalogued-contract` (§4.3) — otherwise it would
ship in a bundle with no owner and no declared consumers.

## 3. Validator results at `db08b46`

```bash
$ python3 scripts/validate_contracts.py
$ python3 scripts/check_references.py
$ python3 scripts/validate_examples.py
$ python3 scripts/validate_catalog.py
$ python3 scripts/check_no_multitenancy.py
$ python3 scripts/check_no_implementation_code.py
$ uv run pytest -q
$ uv run ruff check
$ uv run mypy
```

| Command | Exit | Result |
|---|---:|---|
| `validate_contracts.py` | `0` | `4 contract schema(s) valid, uniquely identified, and explicitly scoped` |
| `check_references.py` | `0` | `all 13 schema reference(s) resolve locally` |
| `validate_examples.py` | `0` | `all 7 example(s) validate against their contract` |
| `validate_catalog.py` | `0` | `4 catalog entr(ies) valid, uniquely owned, and consistent with the tree` |
| `check_no_multitenancy.py` | `0` | `PASS` — **first run against a populated release surface** |
| `check_no_implementation_code.py` | `0` | `PASS` — same |
| `pytest -q` | `0` | **109 passed** (29 at EP-01) |
| `ruff check` | `0` | `All checks passed!` |
| `mypy` (strict) | `0` | `Success: no issues found in 15 source files` |

The two boundary scanners passing here matters independently: EP-01 proved they
guard an empty surface, and this is the first evidence they accept real
contract content without a single exception being added.

## 4. Negative evidence — the validators fail when they should

### 4.1 Schema defects

`tests/test_schema_validity.py` injects one defect at a time into a temp tree
and asserts the reported defect class:

| Injected defect | Reported as |
|---|---|
| Draft-07 `$schema` | `dialect` |
| `$id` removed | `missing-id` |
| `$id` not a URN | `id-format` |
| `$id` generation ≠ filename generation | `id-filename-mismatch` |
| `title` removed | `missing-title` |
| `x-contract-version` absent or not SemVer | `version-metadata` |
| `additionalProperties` omitted | `implicit-additional-properties` |
| structurally invalid schema | `meta-validation` |
| two schemas sharing an `$id` | `duplicate-id` (`M0-CON-029`) |
| malformed filename | `filename` |
| unparseable JSON | `parse-error` |
| empty `contracts/schemas/` | `no-schemas` |

### 4.2 Invalid instance fixtures — failing for the *intended* reason

19 fixtures in `tests/fixtures/invalid/`, each declared in `manifest.yaml` with
its schema, the JSON pointer where the error must surface, and a substring the
message must contain. The tests assert all three.

This distinction is the point: a fixture that fails for the *wrong* reason
reports a passing test while leaving the rule it claims to cover untested.
`test_manifest_covers_every_invalid_fixture` additionally forbids a fixture
from sitting on disk untested.

Representative cases: a lowercase `error.code`; `success: true` in a failure
envelope; an unprefixed `request_id` (which proves the cross-schema `$ref` is
actually enforced, not merely present); a 16-hex-character `traceparent`;
`producer: ai-business-admin-web`; `occurred_at` with a `+03:00` offset; a
single-segment `event_type`; and `complatibility` against the closed catalog
schema.

### 4.3 Live demonstrations at `db08b46`

Each defect was introduced into the real repository, the validator run, and the
file restored:

| Injected | Command | Exit | Reported |
|---|---|---:|---|
| duplicate catalog entry | `validate_catalog.py` | **`1`** | `[duplicate-entry] (urn:…:error-envelope:v1, 0.1.0) is registered 2 times` |
| `$ref` to an undeclared URN | `check_references.py` | **`1`** | `[unresolvable-ref] … names 'urn:…:absent:v1', which no schema in this repository declares as its $id` |
| example drifted from contract | `validate_examples.py` | **`1`** | `[example-invalid] at error/code: 'resource_not_found' does not match '^[A-Z][A-Z0-9_]{2,63}$'` |
| *(after each restore)* | respective validator | `0` | — |

`git status --porcelain` after all three: **0 changes**.

Together these are both halves of `M0-CON-029`: an unresolvable reference and a
duplicate `(contract_id, version)` each fail validation.

### 4.4 Catalog invariants

`tests/test_catalog.py` mutates a copy of the real tree: duplicate entry,
unknown owner, missing source file, uncatalogued contract, `$id` mismatch
between catalog and source, unknown key, deprecated-without-metadata, and
active-with-deprecation-metadata. Each is rejected.

### 4.5 Two bugs the tests caught

Recorded because they are the reason the negative tests exist:

1. `validate_contracts.py` **crashed** with an unhandled `ContractLoadError`
   on a malformed filename instead of reporting the defect. Fixed by deriving
   the generation only once the filename is known well-formed.
2. `test_no_business_rules_or_implementation_technology` matched `http` inside
   the mandated dialect URL `https://json-schema.org/draft/2020-12/schema`.
   The test was scanning raw JSON including structural keywords; it now scans
   authored text only, with word boundaries.

## 5. Exit condition — verified from a clean checkout

EP-02's exit condition is *"All schemas, examples, references, and catalog
entries validate from a clean checkout."* Verified from an actual clean clone,
not this working tree:

```bash
$ git clone <repo> /tmp/ep02clean && cd /tmp/ep02clean && git checkout db08b46
$ uv venv && uv pip install jsonschema PyYAML pytest
$ python3 scripts/{validate_contracts,check_references,validate_examples,validate_catalog}.py
$ uv run pytest -q
```

| Check | Exit | Result |
|---|---:|---|
| `git status --porcelain` in the clone | `0` | 0 files — nothing untracked carried over |
| `validate_contracts.py` | `0` | 4 schemas valid |
| `check_references.py` | `0` | 13 references resolve |
| `validate_examples.py` | `0` | 7 examples validate |
| `validate_catalog.py` | `0` | 4 entries valid and consistent |
| `check_no_multitenancy.py` | `0` | PASS |
| `check_no_implementation_code.py` | `0` | PASS |
| `pytest -q` | `0` | 109 passed |

No network fetch was required for reference resolution.

## 6. Artifacts / hashes

Blob hashes at `db08b46` via `git show <ref>:<path> | shasum -a 256` (exit `0`).
Tracked files: **106**. Schemas: 4. Examples: 7. Invalid fixtures: 19.

| Artifact | SHA-256 |
|---|---|
| `contracts/schemas/common/error-envelope.v1.schema.json` | `4d805266af0d3ee4e4d7e7447c34e27186ac247e07bc7bcf3db515e74c87f0ef` |
| `contracts/schemas/common/request-metadata.v1.schema.json` | `c9f8c5e22501a67588dc2c33ab10846f0777fa9af691f76fe941a5d4868a4599` |
| `contracts/schemas/common/contract-metadata.v1.schema.json` | `b3388e488bf690884610aeb906caac389fa54d00d5b96bc521825590f0734814` |
| `contracts/schemas/events/event-envelope.v1.schema.json` | `ec5909f92b424ee5328f930904bc4d0b62a9a659d398dadf4586b456e6e7f4c2` |
| `catalog/contract-catalog.yaml` | `a8cfbd36f513fc6e35c28a31e47edcf50d86e5391cca386a265769ac7c7cd946` |
| `scripts/_contracts.py` | `21b3983ca7f2bfb1a1816775298fba616a95d3e16a0376b164eed3327d7f43e7` |
| `scripts/validate_contracts.py` | `96348b51ebfa83a09c16e2bd32ec30d745d48e290ab1dca9f93300de7b634134` |
| `scripts/check_references.py` | `5db06f4f5b959af4a13571789171a133e13c8ea42b3ea6ca6ef024b8a87562b1` |
| `scripts/validate_examples.py` | `1ced623a7e77710748a65930780471120ac6a4d0fd8fbb7b637dc5d8212933cd` |
| `scripts/validate_catalog.py` | `28c62306a5b90f45a7ff13ef4afec61db9c32729bd38c7d96c3c0af050fa9ec1` |
| `tests/fixtures/invalid/manifest.yaml` | `11baf23b812713373fbcc0192fe2f9a0e30f9a2cd5a96917174bb8a378376c7f` |
| `contracts/examples/common/contract-metadata.v1.catalog.example.json` | `a0df6d8f41ec80d97d6827e954689f56ed3f9781a40437333ac4606e8ded2199` |
| `contracts/examples/common/error-envelope.v1.minimal.example.json` | `4c78ef51ae5e189e947d7386fe6993b0816cf7457b051fd8389245b355cecde9` |
| `contracts/examples/common/error-envelope.v1.validation-failed.example.json` | `6cbeabe67554c117da754cbea6dd739a66c1c6fd3e8c3e099f210968cb054ddf` |
| `contracts/examples/common/request-metadata.v1.minimal.example.json` | `35b53f90e62996f0f5e676c833f051721b6c595d04fd1767f1cf33b6bb32908c` |
| `contracts/examples/common/request-metadata.v1.traced.example.json` | `5ecff5bcb3a6abac9bab0562ed9fa4777555379dd38ce7119bb02cfd3c3e3266` |
| `contracts/examples/events/event-envelope.v1.entity-changed.example.json` | `ee4d8876998975b69c417b1cb357b3140ec53f8709ef6fa31f8987c069fdc407` |
| `contracts/examples/events/event-envelope.v1.minimal.example.json` | `7e65027372385350d0cd8e85ffbfaa69e5586dc6d38fa7e59bf7be21e080793d` |

## 7. Acceptance criteria status

| Criterion | Status | Basis |
|---|---|---|
| `M0-CON-011` | **PASS** | error-envelope schema valid and versioned; 2 passing examples, 5 failing fixtures each rejected for its declared reason |
| `M0-CON-012` | **PASS** | request-metadata valid and versioned; no secret or PII field — identifiers are observability-only and documented as not authorization inputs; 2 passing, 3 failing fixtures |
| `M0-CON-013` | **PASS** | event-envelope valid, versioned, transport-neutral (no protocol or broker binding); 2 passing, 5 failing fixtures |
| `M0-CON-014` | **PASS** | contract-metadata captures contract_id, SemVer, lifecycle, owner, consumers, type, source, compatibility; validates the real catalog (§3) |
| `M0-CON-015` | **PASS** | exactly one owner per entry and unique `(contract_id, version)`, asserted positively and by a duplicate-entry rejection (§4.3) |
| `M0-CON-016` | **PASS** | 13 references resolve from a clean clone with no network access (§5); an undeclared URN is rejected (§4.3) |
| `M0-CON-017` | **PASS** | all 7 committed examples validate; a drifted example is rejected (§4.3) |
| `M0-CON-029` | **PASS** | both halves proven: unresolvable reference **and** duplicate id/version fail validation (§4.1, §4.3) |
| `M0-CON-002` | **NOT RUN** | see below |

### Why `M0-CON-002` is still `NOT RUN`

Its evidence is *"governance/ownership + catalog/matrix"*. Two of three parts
now exist — `governance/OWNERSHIP.md` from EP-01 and the validated catalog from
EP-02 — but `compatibility/platform-m0-matrix.yaml` is an EP-04 deliverable and
cannot be validated before it is written. Unchanged from EP-01, and it remains
the one criterion trailing its EP.

### Not claimed

`M0-CON-020`–`028` and `030`–`045` remain `NOT RUN`. Specifically, despite
green output at this commit:

- `M0-CON-032` — `ruff` and `mypy` pass, but the quality gate is EP-05's.
- `M0-CON-033` — 109 tests passed from a clean checkout (§5), which is close to
  this criterion's wording, but it is evidenced by EP-05's gate and is claimed
  there, not here.
- `M0-CON-034` — `detect-secrets` has not been run. EP-00 finding 8 stands.

## 8. Unresolved findings

**Blocking:** none.

**Carried forward:**

1. `M0-CON-002` requires the EP-04 platform matrix.
2. `evidence/04-compatibility.md` … `08-audit-verdict.md` remain `NOT RUN`.
3. `compatibility/policy.md` and the six `governance/` documents remain EP-01
   skeletons; `M0-CON-020`–`023` are not claimable from them.
4. **New:** `contracts/openapi/` and `contracts/asyncapi/` are still empty, so
   their validation pipelines are untested against real artifacts.
   `TEST_PLAN.md` Layer B requires an invalid sample to prove each validator
   fails once those directories are non-empty. EP-00 §5.1 already recorded that
   AsyncAPI validation must reach specification-level conformance before the
   first AsyncAPI contract becomes active — that obligation is now closer.
5. **New:** the `x-contract-version` metadata in each schema duplicates the
   `version` in the catalog. `validate_catalog.py` cross-checks `$id` against
   `contract_id`, but **not** the version. A schema could carry
   `x-contract-version: 0.2.0` while the catalog says `0.1.0` without failing.
   EP-03 should close this when it implements version-aware compatibility.

**Carried to EP-05 (unchanged):**

6. `jq`, `gitleaks`, `trivy` absent; the `detect-secrets`/`pip-audit`
   substitution must be implemented and evidenced.
7. The EP-00 secret grep is an observation, not a gate.

## 9. Exit condition

`EP-02-CONTRACT-FOUNDATION.md` requires: *"All schemas, examples, references,
and catalog entries validate from a clean checkout."*

**Met, and verified from an actual clean clone** (§5): 4 schemas, 7 examples,
13 references, and 4 catalog entries all validate at exit `0`, with 109 tests
passing, and with no network access required.

The validators are demonstrably capable of failing (§4), which is what makes
those zeros meaningful rather than vacuous.

**EP-03 has not been started.** No compatibility engine, no compatibility
fixtures, no completed governance documents. `M0-CON-002` and every criterion
from `M0-CON-020` onward except `M0-CON-029` remain `NOT RUN`; M0 does not pass
at EP-02.
