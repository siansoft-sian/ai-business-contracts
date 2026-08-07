# TEST_PLAN.md

## 1. Test objectives

Verify that M0 establishes a **machine-enforced contract repository**, not merely documentation. Tests must prove schema correctness, catalog integrity, backward-compatibility behavior, repository boundaries, absence of prohibited multi-tenant constructs, reproducible release artifacts, and platform-gate metadata.

## 2. Test layers

### Layer A — Static repository boundary tests

Checks:

- forbidden implementation directories/file patterns;
- forbidden imports/dependencies associated with runtime ownership outside this repo;
- SQL/migration/PgBouncer deployment files absent;
- prohibited multi-tenant constructs absent from contract-bearing paths;
- no secrets/credential files committed.

Required mutation tests:

1. insert a prohibited tenant field into a fixture → gate must fail;
2. insert a FastAPI/LangGraph/database implementation file into a guarded path → gate must fail.

Maps to: M0-CON-001..005, 034.

### Layer B — Schema validity tests

For each JSON Schema:

- JSON parses;
- declared dialect/meta-schema validates;
- `$id` is stable and unique;
- title/version metadata exists;
- good fixtures pass;
- bad fixtures fail for the intended reason;
- local references resolve.

OpenAPI/AsyncAPI directories are validated when non-empty; an invalid sample fixture must prove the validator fails.

Maps to: M0-CON-010..017, 029.

### Layer C — Catalog tests

Validate:

- catalog file against its schema;
- unique `(contract_id, version)`;
- one authoritative owner;
- consumer repository names are from the frozen eight-repo set;
- source paths exist;
- source checksum can be computed;
- lifecycle state is valid;
- semantic version syntax is valid;
- retired/deprecated metadata rules are enforced.

Maps to: M0-CON-014..015, 020..023.

### Layer D — Compatibility tests

Maintain fixtures under:

```text
compatibility/fixtures/compatible/
compatibility/fixtures/breaking/
```

Minimum cases:

**Compatible**
- add optional object property;
- add optional response metadata that clients may ignore;
- documentation-only change;
- add a new independent contract ID.

**Breaking**
- remove field;
- rename field;
- string → integer type change;
- optional input → required input;
- remove enum value;
- tighten regex/range in a way that rejects formerly valid input;
- remove endpoint/message when OpenAPI/AsyncAPI fixtures are enabled;
- unresolved `$ref`;
- duplicate contract ID/version.

**Review-required, not blindly compatible**
- enum expansion;
- new response/event variant consumed by exhaustive matchers.

The checker must emit a machine-readable result with `compatible`, `breaking`, and `review_required` findings.

Maps to: M0-CON-024..029, 042.

### Layer E — Build and reproducibility tests

From a clean checkout:

1. run the quality gate;
2. build release bundle;
3. record manifest/checksums;
4. delete generated `dist/`;
5. rebuild using the same commit/source timestamp policy;
6. compare logical manifest contents and deterministic archive checksum if deterministic archives are required by implementation.

The bundle must exclude local caches, virtualenvs, tests (unless intentionally part of artifact policy), `.env`, credentials, and VCS metadata.

Maps to: M0-CON-030..038.

### Layer F — Cross-repo gate metadata tests

Validate `platform-m0-matrix.yaml`:

- all eight repositories present exactly once;
- authority roles match frozen architecture;
- database contracts remain owned by `ai-business-database`;
- consumer lock template includes version + integrity hash;
- negative fixtures fail on checksum/version/required-contract mismatch.

Maps to: M0-CON-040..042.

### Layer G — Evidence integrity tests

Validate evidence report completeness:

- commit SHA matches tested commit;
- commands are recorded;
- exit codes are present;
- blocking checks are not `NOT RUN`;
- artifact hashes match generated files;
- final delivery verdict is derivable from criterion statuses.

Maps to: M0-CON-043..045.

## 3. Required local commands

The implementation may choose exact tooling, but M0 must expose a single entry point similar to:

```bash
./scripts/quality_gate.sh
```

The gate should orchestrate equivalent checks for:

```text
format/lint tooling
static typing tooling
tests
schema validation
reference validation
example validation
catalog validation
compatibility validation
multi-tenancy negative scan
implementation-boundary scan
secret scan
dependency vulnerability audit
bundle/manifest validation
```

CI must call the same scripts rather than re-implementing divergent logic.

## 4. Test data rules

- Use synthetic IDs and example domains.
- Do not use real names, emails, phone numbers, credentials, access tokens, connection strings, or production payloads.
- No tenant fields exist even in positive examples.
- Negative multi-tenant fixtures should live outside release contract artifacts and should be clearly test-only so they do not pollute published schemas/catalogs.

## 5. Exit conditions

The test phase is complete only when:

- every blocking command exits 0;
- negative/mutation tests prove the gates fail when expected;
- compatibility output is machine-readable;
- release artifacts are generated and hashed;
- evidence is recorded against the exact commit being delivered.
