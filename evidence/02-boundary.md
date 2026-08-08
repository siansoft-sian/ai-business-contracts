# Evidence — Repository Boundary Enforcement

EP-01 Status: **COMPLETE** (boundaries are machine-enforced)

- Repository: `ai-business-contracts`
- Repository URL: `https://github.com/siansoft-sian/ai-business-contracts.git`
- Branch: `main`
- Audited commit: `f8f0d38141d6511ec51dbc5f3369b1d0c69fe245`
- Timestamp UTC: `2026-08-07T18:03Z`
- Working tree at observation: clean
- Executed by: EP-01 per `execution-prompts/EP-01-BOUNDARY-AND-SCAFFOLD.md`

> EP-01 is the first milestone step that **enforces** rather than observes.
> EP-00 recorded that the repository contained no violations but could not
> detect one; §4 below closes that gap. Criteria are claimed `PASS` only where
> both artifacts named by `ACCEPTANCE_CRITERIA.md` exist and ran green at this
> commit — see §7 for what is deliberately **not** claimed.

## 0. Commit model

As in EP-00, evidence cannot describe the commit that contains it. EP-01
therefore commits its work first and observes that committed state:

```text
86219c7  docs(evidence): close EP-00 finding 6            ← EP-00 final state
│
f8f0d38  feat(boundary): scaffold repository and          ← EP-01 work
│        enforce ownership boundaries                       ALL FIGURES BELOW
│                                                           MEASURED HERE
G        docs(evidence): record EP-01 boundary evidence   ← this document
```

Every command below was executed against the working tree at `f8f0d38`, which
`git status --porcelain` confirmed clean (no output, exit `0`).

## 1. Boundary cleanup (instruction 1)

EP-00 §2 classified every conflict category `retain` — **nothing prohibited
existed to remove**. Every `tenant`/FastAPI/SQL/LangGraph match it found at
every anchor was governance prose *forbidding* the construct.

| Item | EP-00 classification | EP-01 action | Result |
|---|---|---|---|
| Multi-tenant constructs | `retain` | none required | none existed |
| Foreign-repo implementation | `retain` | none required | none existed |
| SQL / migrations / PgBouncer | `retain` | none required | none existed; authority stays with `ai-business-database` |
| Auth / Casbin, LangGraph, channel, React, IaC | `retain` | none required | none existed |
| Pack `README.md` (untracked) | `replace` | **replaced** by the repository README | closes EP-00 finding 3 |
| `.DS_Store` | `remove` | left uncommitted, gitignored | not tracked |

**No item required `migrate-to-owner-repo` in any EP.** No material belonging
to another of the frozen eight repositories has been found at any anchor.

Pack README replacement verified lossless before overwriting: the byte-identical
copy `e6283f0fc91470a08ac7579f23617f4070e8f6a447b62676af0196d9326ece27` survives
in `ai-business-contracts-m0-execution-pack.zip`, confirmed by `unzip -p … | shasum -a 256`.

## 2. Repository tree (instruction 2 → M0-CON-010)

```bash
$ git ls-tree -r --name-only f8f0d38 | wc -l
$ git ls-tree -r --name-only f8f0d38 | grep '/' | sed 's|/[^/]*$||' | sort -u
```

Exit `0`. **70 tracked files** (28 at EP-00 + 43 added, minus overlap), across:

| Canonical directory | Present | Contents at EP-01 |
|---|---|---|
| `contracts/openapi/` | yes | `.gitkeep` — EP-02 |
| `contracts/asyncapi/` | yes | `.gitkeep` — EP-02 |
| `contracts/schemas/{common,events}/` | yes | `.gitkeep` — EP-02 |
| `contracts/examples/{common,events}/` | yes | `.gitkeep` — EP-02 |
| `catalog/` | yes | `.gitkeep` — EP-02 |
| `compatibility/` | yes | `policy.md` skeleton + `fixtures/{compatible,breaking}/` — EP-03 |
| `governance/` | yes | 6 documents |
| `templates/` | yes | `.gitkeep` — EP-04 |
| `scripts/` | yes | 3 modules |
| `tests/` | yes | 2 test modules, `conftest.py`, 9 negative fixtures |
| `dist/` | yes | `.gitkeep` (contents gitignored) |
| `.github/workflows/` | yes | `.gitkeep` — EP-05 |

Root documents added: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`CODEOWNERS`, `.editorconfig`, `pyproject.toml`, `uv.lock`.

`M0-CON-010` names *tree evidence* and the tree is present at the audited
commit. Directories whose contents belong to EP-02–EP-05 are marked above so
the claim is not mistaken for a claim about their contents.

## 3. Scanner design and results (instruction 4)

### 3.1 Scope is defined positively — the EP-00 constraint, implemented

`scripts/_scope.py` declares the release surface:

```python
CONTRACT_BEARING_PATHS = ("contracts", "catalog", "compatibility", "templates")
```

Everything else — root governing documents, `governance/`, `evidence/`,
`execution-prompts/`, `scripts/`, `tests/`, `dist/`, `.github/` — is outside
scanner scope **by construction, with no ignore-list anywhere in either
scanner**.

This is the binding input EP-00 recorded across three runs (§1.1, §1.3,
§D.4.2). A root-wide scan flags `PROMPT.md`, `HARNESS.md`, and every evidence
file — the documents that mandate the scan — and the count grows on every
evidence write (measured 30 → 36 → 42 tenant matches, with later runs matching
earlier runs' own result tables). An ignore-list would require a new exception
each run: a gate weakening monotonically as the milestone progresses, which
`HARNESS.md` §7 and EP-05 both forbid. Positive scoping leaves no exception to
erode.

`tests/test_no_multitenancy.py::test_evidence_and_governance_are_outside_scanner_scope`
asserts this property mechanically rather than leaving it to convention.

### 3.2 Scanner results at `f8f0d38`

```bash
$ python3 scripts/check_no_multitenancy.py
$ python3 scripts/check_no_multitenancy.py --json
$ python3 scripts/check_no_implementation_code.py
$ python3 scripts/check_no_implementation_code.py --json
```

| Command | Exit | Result |
|---|---:|---|
| `check_no_multitenancy.py` | `0` | `PASS - no prohibited constructs in scope (contracts, catalog, compatibility, templates)` |
| `check_no_multitenancy.py --json` | `0` | `"result": "pass"`, `"violation_count": 0` |
| `check_no_implementation_code.py` | `0` | `PASS - no prohibited implementation (file families repository-wide; content in contracts, catalog, compatibility, templates)` |
| `check_no_implementation_code.py --json` | `0` | `"result": "pass"`, `"violation_count": 0` |

### 3.3 Two scan families, scoped differently and deliberately

`check_no_implementation_code.py` runs two families because they warrant
different scopes:

| Family | Scope | Rationale |
|---|---|---|
| **Content patterns** (FastAPI, asyncpg/DDL, Casbin/JWT, LangGraph, channel SDKs, React, Terraform/K8s, OTel SDK init) | release surface only | prose *naming* a prohibited construct is legitimate — the governing documents must be able to forbid FastAPI without failing their own gate |
| **File families** (`.sql`, `.tf`, `.tfvars`, `.tsx`, `.jsx`, `pgbouncer.ini`, `sqitch.plan`, `Dockerfile`, `docker-compose.y*ml`) | repository-wide | a `.sql` or `.tf` file has no legitimate home anywhere in a contracts repository, regardless of directory — this is what makes `M0-CON-005` enforceable |
| **`.py`** | release surface only | `PROMPT.md` §G explicitly permits validation scripts, so Python is legal in `scripts/`/`tests/` and illegal in `contracts/`/`catalog/`/`compatibility/`/`templates/` |

Generated and ephemeral trees (`.git`, `.venv`, caches, `dist`) are not
traversed by the repository-wide family scan: they are build output, not
source. Release-artifact contents are validated separately by EP-05
(`M0-CON-037`).

## 4. Mutation tests (instruction 5) — the gap EP-00 could not close

`TEST_PLAN.md` Layer A requires two mutation tests: inject a tenant field, and
inject an implementation file; **the gate must fail** in both cases.

### 4.1 Live mutation demonstration at `f8f0d38`

Each fixture was copied into the real `contracts/schemas/common/` under its
real filename, the scanner run, and the file removed:

| Injected into `contracts/schemas/common/` | Scanner | Exit |
|---|---|---:|
| *(baseline — nothing injected)* | `check_no_multitenancy.py` | `0` |
| `tenant-field.json` | `check_no_multitenancy.py` | **`1`** |
| `tenant-header.yaml` | `check_no_multitenancy.py` | **`1`** |
| *(baseline — nothing injected)* | `check_no_implementation_code.py` | `0` |
| `fastapi-router.py` | `check_no_implementation_code.py` | **`1`** |
| `langgraph-node.py` | `check_no_implementation_code.py` | **`1`** |
| `migration.sql` | `check_no_implementation_code.py` | **`1`** |
| `pgbouncer.ini` | `check_no_implementation_code.py` | **`1`** |
| `terraform-main.tf` | `check_no_implementation_code.py` | **`1`** |
| `react-component.tsx` | `check_no_implementation_code.py` | **`1`** |
| `asyncpg-pool.json` | `check_no_implementation_code.py` | **`1`** |
| *(after cleanup)* | both scanners | `0`, `0` |

`git status --porcelain` after the demonstration: **0 changes**. No injected
file leaked.

Sample rejection output, showing the gate names the file, line, classification,
and matched text:

```text
check_no_multitenancy: FAIL - 1 prohibited construct(s) found
  contracts/schemas/common/manual-check.json:1: [tenant-identifier] tenant identifier or tenant-scoped field (matched 'tenant_id')
```

### 4.2 Automated suite

```bash
$ uv run pytest -q
```

Exit `0` — **29 passed**. Coverage by intent:

| Test class | Count | Proves |
|---|---:|---|
| Clean-repository / clean-surface positives | 4 | the gates do not fire spuriously |
| Temp-tree injections (multi-tenancy) | 6 | every release-surface directory is guarded: `contracts/schemas/common`, `contracts/examples/common`, `contracts/openapi`, `catalog`, `templates`, `compatibility/fixtures/compatible` |
| Temp-tree injections (implementation) | 6 | `sql-source`, `pgbouncer-config`, `terraform`, `react-component`, `python-on-release-surface` |
| Content-pattern injections | 3 | `database-driver` detected on the surface; a tenant fixture correctly produces **no** implementation violation, proving the two checks are not interchangeable |
| **In-repo guarded-path mutations** | 4 | the *default* invocation guards the *real* `contracts/schemas/common/`, not just a temp replica |
| SQL-anywhere | 1 | `M0-CON-005`: SQL fails even outside the release surface |
| Off-surface prose negative | 1 | governance text naming FastAPI/LangGraph/asyncpg does **not** fail the gate — the false-positive class EP-00 identified |
| Scope assertions | 4 | `tests/`, `evidence/`, `execution-prompts/`, `governance/` and the root documents are out of scope; no `.fixture` leaked onto the release surface; the scanners' own Python is not flagged |

The in-repo mutations use `try`/`finally` with a `__mutation_test__` filename
prefix, and `.gitignore` carries a matching backstop so a crashed run cannot
commit a prohibited construct.

### 4.3 Negative fixtures and release exclusion (instruction 6)

Nine fixtures live in `tests/fixtures/negative/`, each carrying a neutralising
`.fixture` suffix (`migration.sql.fixture`, `fastapi-router.py.fixture`, …).

The suffix is load-bearing: these are **not** `.sql`/`.py`/`.tf` files, so the
repository-wide file-family scan does not match them and **no scanner exception
is required for the repository's own test data**. Tests rename each fixture to
its real name at injection time, so the real extension and content are still
exercised against the real scanner.

`tests/` lies outside the release surface, so the fixtures can never be scanned
as contract source — asserted by `test_negative_fixtures_are_outside_scanner_scope`
and `test_no_neutralised_fixture_leaked_onto_release_surface`.
`governance/RELEASES.md` records the bundle-exclusion rule; EP-05 implements and
validates the bundle-level check (`M0-CON-037`).

## 5. Tooling quality

```bash
$ uv run ruff check
$ uv run mypy
```

| Command | Exit | Result |
|---|---:|---|
| `ruff check` | `0` | `All checks passed!` |
| `mypy` (strict, `python_version = 3.11`) | `0` | `Success: no issues found in 6 source files` |
| `pytest -q` | `0` | `29 passed` |

Recorded as fact, **not** as a claim on `M0-CON-032` — that criterion belongs to
EP-05's quality gate and is not claimed here.

## 6. Artifacts / hashes

Blob hashes at `f8f0d38`, computed via `git show <ref>:<path> | shasum -a 256`
(exit `0`).

| Artifact | SHA-256 |
|---|---|
| `scripts/_scope.py` | `4afff21a0b1f289d4004a1acfcae74fca7450f547c57955c4883c1d0aba60e18` |
| `scripts/check_no_multitenancy.py` | `81d35156043026f8cf185053e73ab919c5e5f08633a9647280d04dfaf9cd1faf` |
| `scripts/check_no_implementation_code.py` | `fb6eb920b788f83d1f62deda64267c312b00ab364412c5c86b10091348b7a35c` |
| `tests/conftest.py` | `fbef776149c1688f8cc5fd61648a59369ed5fcd60030b33bd238c7dc1ea39d08` |
| `tests/test_no_multitenancy.py` | `dd195b2f026ffc22d4d648c0bef8494fc57bade0887e825533e3093f7fb12bdb` |
| `tests/test_no_implementation_code.py` | `7e5003ab4c59bda9cf61f1dffee2e36a50e138299895534466c8bee82b559a44` |
| `README.md` | `db1da4dbcafb811a567258cff709a8ba1f3adb5f5e03eee88731e025333aaa7a` |
| `CONTRIBUTING.md` | `e606ec095c3bdd50fb7d21e40cc50a4429dee0115ff439ca81175182aef511fe` |
| `SECURITY.md` | `c0c360ad8869555dec3138051feef02d564d83460dca561df7429308c06b0039` |
| `CODEOWNERS` | `1b1ee2d927b2eda9310de5abc7e4ac8cefafa178ca316868708304f2d71c0102` |
| `pyproject.toml` | `fdadfa73f2a6d85c16f48166c1cb0176a8fb61d73c23e565ede6b2f32fcda212` |
| `governance/OWNERSHIP.md` | `67fae344f8713580e700d89766636c1ce80cfc389d14fe5bde20ca6acad1fc86` |
| `governance/CONTRACT_POLICY.md` | `4f265408aec30b17ff34675e758b22e391ab588be519d80928ede2b89f5f3172` |
| `governance/VERSIONING.md` | `32b4ed3c7891475ae4260ab9b7f7ebcb8c83fe456b1824c779ee1a5731a038e4` |
| `governance/CHANGE_PROCESS.md` | `5883a877a26c9a901a3a7ba63daca33293274e4d6e9d89a2175239311d282a34` |
| `governance/DEPRECATION.md` | `7d77837d4908349de206dcd99fd43376b81abc9f7dca0e4d4fd609c0fc249b7d` |
| `governance/RELEASES.md` | `b252643d72c6908ce85ab548a26923f34cafab325da1e304c1f718d3f93e7f32` |
| `compatibility/policy.md` | `4141134b6601c80b2fee581e1536ba5e4c841649be088df1cf38bce45e155190` |
| `tests/fixtures/negative/tenant-field.json.fixture` | `e9323fab498aa1584e3f7a0c3e3ae027426fe1ed6761269794a0f6942e397aad` |
| `tests/fixtures/negative/tenant-header.yaml.fixture` | `f91a215b0e8d3af0a479fde4c77a29792caea7d118989a1fead090c3b9057c07` |
| `tests/fixtures/negative/fastapi-router.py.fixture` | `e2325b465a3543e142fba70a8888152d0ad346b1bfc1865f509edb6ab6d0fdff` |
| `tests/fixtures/negative/langgraph-node.py.fixture` | `238cae1eb1c4b5c79e165cac26405314ef0829ac9f22ea5b496c57283adbba8a` |
| `tests/fixtures/negative/migration.sql.fixture` | `af732fbf34457b443ca22396fb66e9d37655680163ef994cd26127943c00f1b0` |
| `tests/fixtures/negative/pgbouncer.ini.fixture` | `51954a1ad83abc776a2620f4320f222fa03a9704f6d9252e566c32565aeb11d6` |
| `tests/fixtures/negative/react-component.tsx.fixture` | `4ee4c53caf5dba56e89635b63ebc67046bddb7e6ca2e51f93c101f4a5269dfd6` |
| `tests/fixtures/negative/terraform-main.tf.fixture` | `9a93cccbdf5c8d4c543f88f2a06a1fd5ad4e253cee60f62611af02c2adbfe07d` |
| `tests/fixtures/negative/asyncpg-pool.json.fixture` | `6720feb73593a4901aa96f692aa9dd3c5ca6b07be3e4e8c36755416f40c4b37f` |
| `tests/fixtures/negative/README.md` | `08fc0a6924bab955564331ebe8de317d543f95a03a6f638a6961a68f89d8981e` |

## 7. Acceptance criteria status

> **Snapshot, superseded.** The statuses below are as of this EP and are kept
> unchanged as a historical record — several read `NOT RUN` because the check
> that would establish them had not been built yet. They are **not** the
> milestone's current state. The final per-criterion statuses are in
> [`08-audit-verdict.md`](08-audit-verdict.md), and `evidence/m0-summary.json`
> derives them mechanically from gate exit codes. At the delivery commit all 38
> criteria pass.

| Criterion | Status | Basis |
|---|---|---|
| `M0-CON-001` | **PASS** | `README.md` states contracts/governance-only purpose and the no-implementation rule; boundary scanners exit `0` (§3.2). Both artifacts the criterion names exist. |
| `M0-CON-002` | **NOT RUN** | see below |
| `M0-CON-003` | **PASS** | `check_no_multitenancy.py` + mutation tests; injection fails the gate at exit `1` in the real guarded path (§4.1, §4.2) |
| `M0-CON-004` | **PASS** | `check_no_implementation_code.py` + mutation tests covering all seven other repositories' implementation families (§4.1, §4.2) |
| `M0-CON-005` | **PASS** | file-family scan rejects SQL/Sqitch/PgBouncer **repository-wide**, proven by `test_sql_is_rejected_anywhere_not_only_on_release_surface`; `governance/OWNERSHIP.md` assigns database-contract authority to `ai-business-database` |
| `M0-CON-010` | **PASS** | canonical directories present in the committed tree (§2) |

### Why `M0-CON-002` is `NOT RUN`

`ACCEPTANCE_CRITERIA.md` names its evidence as **"governance/ownership +
catalog/matrix"**. The ownership half is complete: `governance/OWNERSHIP.md`
documents all eight repositories with responsibilities intact and no
collapsing. The other half does not yet exist — `catalog/contract-catalog.yaml`
is EP-02 and `compatibility/platform-m0-matrix.yaml` is EP-04, and neither can
be validated before it is written.

Marking this `PASS` on the ownership document alone would claim evidence that
does not exist. `ACCEPTANCE_CRITERIA.md` treats `NOT RUN` as `FAIL` for
milestone completion, which is the correct state: **M0 does not pass at EP-01.**

This is the one gap against EP-01's stated exit condition
("`M0-CON-001..005` and `M0-CON-010` are technically enforceable"). Four of the
five, plus `M0-CON-010`, are enforceable now; `M0-CON-002` becomes verifiable
when EP-02 and EP-04 supply the catalog and the matrix.

### Not claimed

`M0-CON-011` onward remain `NOT RUN`. In particular, and despite being tempting
from this commit's output:

- `M0-CON-032` (lint/type checks) — `ruff` and `mypy` pass (§5), but the
  criterion belongs to EP-05's quality gate, which does not exist yet.
- `M0-CON-033` (test suite from a clean checkout) — 29 tests pass here, but
  from *this* checkout; the clean-checkout run is EP-05's.
- `M0-CON-034` (secret scan) — `detect-secrets` has not been run. EP-00 finding
  8 stands: a hand-written grep is not the gate.

## 8. Unresolved findings

**Blocking:** none.

**Carried forward:**

1. `M0-CON-002` requires the EP-02 catalog and EP-04 platform matrix (§7).
2. `evidence/03-contract-validation.md` … `08-audit-verdict.md` remain `NOT RUN`.
3. EP-00 finding 3 (repository `README.md` absent) — **RESOLVED** at this commit.
4. EP-00 finding 1 (scanner path-scoping) — **RESOLVED**: implemented positively
   in `scripts/_scope.py` and asserted by test, with no ignore-list.
5. `compatibility/policy.md` and the six `governance/` documents are skeletons.
   Each names the EP that completes it and the criteria not yet claimable.
   They must not be read as satisfying `M0-CON-020`–`M0-CON-023`.
6. **New:** contract-bearing prose constraint. Because the release surface is
   scanned in full with no extension filter, documents *inside* `contracts/`,
   `catalog/`, `compatibility/`, or `templates/` cannot discuss prohibited
   constructs by name. `compatibility/policy.md` is written accordingly.
   Governance prose about tenancy or foreign implementation belongs in
   `governance/`. This is a deliberate cost of having no ignore-list.

**Carried to EP-05 (unchanged from EP-00):**

7. `jq`, `gitleaks`, and `trivy` remain absent; the `detect-secrets`/`pip-audit`
   substitution must be implemented and evidenced, not assumed.
8. The EP-00 secret grep is an observation, not a gate; it must not be cited as
   satisfying `M0-CON-034`.

## 9. Exit condition

`EP-01-BOUNDARY-AND-SCAFFOLD.md` requires: *"`M0-CON-001..005` and
`M0-CON-010` are technically enforceable, not merely documented."*

**Met for `M0-CON-001`, `003`, `004`, `005`, and `010`.** The repository now
rejects an injected tenant construct and an injected implementation file in a
real guarded path, with recorded non-zero exit codes for eleven distinct
injections and 29 automated tests including four that mutate the real
repository. Enforcement is no longer a claim about absence.

**Not met for `M0-CON-002`**, whose named evidence depends on artifacts owned by
EP-02 and EP-04. Recorded as `NOT RUN` rather than glossed.

**EP-02 has not been started.** No foundation schema, catalog entry, or
compatibility fixture exists. No acceptance criterion beyond those in §7 is
claimed as `PASS` anywhere in this document.
