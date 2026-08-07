# Evidence — Preflight & Conflict Inventory

EP-00 Status: **COMPLETE** (inventory recorded)

- Repository: `ai-business-contracts`
- Branch: `main`
- Baseline audited commit: `13afef142f24b1bca5a5979cc7aaefc20d284ce0` (tag: `m0-ep00-baseline`)
- Evidence recording commit: not self-declared; see repository history
- Timestamp UTC: `2026-08-07T16:27:25Z`
- Executed by: EP-00 per `execution-prompts/EP-00-PREFLIGHT.md`

> **No acceptance criterion is marked `PASS` in this document.** EP-00 *observes* the starting state; it does not *enforce* it. See §6.

## 0. Commit model

Evidence cannot describe the commit that contains it. EP-00 therefore uses a two-commit model:

```text
A  chore: bootstrap ai-business-contracts M0 governing pack   ← tag: m0-ep00-baseline
│                                                             ← EP-00 executed against THIS state
B  docs(evidence): record EP-00 preflight                     ← this file
│
HEAD
```

All searches, inventories, and hashes below were executed against `m0-ep00-baseline`, **not** against `HEAD` and **not** against the working tree. The tag is the durable anchor; `HEAD^` would drift on any later commit.

---

## Section A — Starting state as found (observation, before any mutation)

### A.1 Target repository did not exist

The directory supplied for this milestone, `/Users/alifaraj/Downloads/ai-business-contracts-m0-execution-pack`, is the **M0 execution pack** — the governing specification — **not** the `ai-business-contracts` repository it governs.

| Observation | Finding |
|---|---|
| `ai-business-contracts` on disk | Absent. Only the pack directory and its `.zip` exist |
| Git | Not a git repository — no branch, no commit SHA, no working-tree status |
| Contract source | None |
| `contracts/` `catalog/` `compatibility/` `governance/` `scripts/` `tests/` `templates/` `.github/` | All absent |
| `pyproject.toml` / `package.json` / lockfiles | All absent |
| Legacy or conflicting material | **None. This is a greenfield start.** |

Commands:

```bash
$ ls -la /Users/alifaraj/Downloads/ai-business-contracts-m0-execution-pack
$ find /Users/alifaraj/Downloads/ai-business-contracts-m0-execution-pack -not -path '*/.git/*' | sort
$ git -C /Users/alifaraj/Downloads/ai-business-contracts-m0-execution-pack status
$ find /Users/alifaraj -maxdepth 4 -name "ai-business*" -not -path "*/node_modules/*"
$ ls -ld /Users/alifaraj/Downloads/ai-business-contracts
```

| Command | Exit code | Result |
|---|---:|---|
| `ls -la <pack>` | `0` | 11 root `.md`, `evidence/`, `execution-prompts/`, `.DS_Store` |
| `find <pack> ... \| sort` | `0` | 28 files; no contract source of any kind |
| `git -C <pack> status` | `128` | `fatal: not a git repository` |
| `find /Users/alifaraj -maxdepth 4 -name "ai-business*"` | `0` | 2 hits: the pack and `…-execution-pack.zip`. No repository |
| `ls -ld /Users/alifaraj/Downloads/ai-business-contracts` | `1` | `No such file or directory` |

**Consequence.** `HARNESS.md` §7 requires a commit SHA on every gate record, and `M0-CON-038` / `M0-CON-043` require one in the manifest and evidence. A non-repository cannot produce one. Bootstrapping a real git repository was therefore a precondition of EP-00 producing valid evidence at all — recorded in Section B as an explicit mutation, not smuggled in as observation.

### A.2 Toolchain inventory

| Tool | Version | Status |
|---|---|---|
| `git` | 2.55.0 | present |
| `python3` | 3.12.2 | present |
| `pip3` | 25.2 | present |
| `uv` | 0.6.14 | present |
| `node` | v26.4.0 | present |
| `npm` | 11.17.0 | present |
| `docker` | 29.6.1 | present |
| `shasum` | 6.02 | present |
| `gitleaks` | — | **absent** |
| `trivy` | — | **absent** |
| `jq` | — | **absent** |

Git identity configured: `siansoft <siansoft@gmail.com>`. `init.defaultBranch` **unset** — `git init -b main` was therefore issued explicitly rather than relying on the default.

### A.3 Dependency inventory

**No dependencies are declared.** There is no `pyproject.toml`, `requirements.txt`, `package.json`, `uv.lock`, or `poetry.lock` at the baseline commit (verified in §3). Recorded as an absence of state, not an inferred state.

---

## Section B — Bootstrap actions taken during EP-00 (mutation)

Per the user-confirmed decision, the target repository was created as a **sibling directory**; the execution pack remains untouched as a pristine reference copy.

```bash
$ mkdir -p /Users/alifaraj/Downloads/ai-business-contracts
$ git -C /Users/alifaraj/Downloads/ai-business-contracts init -b main
$ cp <pack>/{PROMPT,HARNESS,ACCEPTANCE_CRITERIA,TEST_PLAN,CONTRACT_STANDARD,AUDITOR,\
     DELIVERY_REPORT,CROSS_REPO_COMPATIBILITY,M0_MANIFEST,TARGET_REPOSITORY_TREE,\
     ARCHITECTURE_COMPLIANCE_MATRIX}.md <target>/
$ cp <pack>/execution-prompts/*.md <target>/execution-prompts/
$ cp <pack>/evidence/*.md          <target>/evidence/
$ git -C <target> add -A
$ git -C <target> commit -m "chore: bootstrap ai-business-contracts M0 governing pack"
$ git -C <target> tag m0-ep00-baseline
$ git -C <target> rev-parse m0-ep00-baseline
```

| Command | Exit code |
|---|---:|
| `mkdir -p <target>` | `0` |
| `git init -b main` | `0` |
| `cp` (11 root docs + 7 EP files + 9 evidence templates) | `0` |
| `git add -A` | `0` |
| `git commit` | `0` |
| `git tag m0-ep00-baseline` | `0` |
| `git rev-parse m0-ep00-baseline` | `0` → `13afef142f24b1bca5a5979cc7aaefc20d284ce0` |
| `git status --porcelain` (after commit A) | `0` → empty |

### B.1 Deliberately excluded from the baseline commit

| Item | Reason |
|---|---|
| `.DS_Store` | macOS artifact; classified `remove`, gitignored |
| pack `README.md` | Describes *the pack*, not *the repository*; classified `replace` — a repo `README.md` is an EP-01 deliverable |

### B.2 Files authored during EP-00

| File | Rationale |
|---|---|
| `.gitignore` | Minimal bootstrap only (`.DS_Store`, `dist/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`) so the baseline commit is free of OS artifacts and generated output. The full scaffold is an EP-01 responsibility. |

### B.3 Scaffold deliberately NOT created

`README.md` (repo), `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, `pyproject.toml`, `.editorconfig`, `contracts/`, `catalog/`, `compatibility/`, `governance/`, `templates/`, `scripts/`, `tests/`, `dist/`, `.github/workflows/` — all remain EP-01/EP-02 deliverables per `TARGET_REPOSITORY_TREE.md`. EP-00 does not scaffold.

---

## 1. Conflict searches (executed against `m0-ep00-baseline`)

Command form:

```bash
git grep -n -I -E -i '<pattern>' m0-ep00-baseline
```

`git grep` exits `0` when matched, `1` when not. Both are recorded verbatim.

| # | Category | Pattern (abridged) | Exit | Match lines | Files |
|---|---|---|---:|---:|---:|
| C1 | Multi-tenant constructs | `tenant` | `0` | 30 | 14 |
| C2 | Foreign-repo implementation (FastAPI/runtime) | `fastapi\|APIRouter\|uvicorn\|Depends(\|@app.(get\|post\|put\|delete)` | `0` | 6 | 5 |
| C3 | SQL / migrations / DB drivers / PgBouncer | `asyncpg\|psycopg\|sqlalchemy\|pgbouncer\|sqitch\|create (table\|or replace function)\|alembic` | `0` | 19 | 11 |
| C4 | Auth / JWT / Casbin | `casbin\|pyjwt\|jwt.decode\|jwks\|oauth2\|passlib\|bcrypt\|argon2` | `0` | 4 | — |
| C5 | LangGraph | `langgraph\|langchain\|StateGraph` | `0` | 17 | — |
| C6 | Channel adapters / webhooks | `webhook\|twilio\|whatsapp\|telegram\|X-Hub-Signature\|slack_sdk` | `0` | 3 | — |
| C7 | React / frontend | `from 'react'\|useState\|useEffect\|ReactDOM\|next/(app\|link)\|@types/react` | `1` | 0 | 0 |
| C8 | Deployment / IaC | `terraform\|kubernetes\|kubectl\|helm chart\|apiVersion: apps\|docker-compose` | `0` | 2 | — |
| C9 | Existing schemas / CI / tests / release metadata | `$schema\|^openapi:\|^asyncapi:\|def test_\|^jobs:\|runs-on:` | `1` | 0 | 0 |
| C10 | Prohibited file types | `git ls-tree … \| grep -Ei '\.(sql\|tf\|tfvars\|tsx\|jsx\|ts\|js\|py\|ipynb\|yaml\|yml\|toml\|env)$'` | `1` | 0 | 0 |

### 1.1 Critical interpretation — prose vs. construct

**Every match in C1–C6 and C8 is governance prose that *prohibits* the construct. Not one is an actual implementation artifact.** Representative lines:

```text
PROMPT.md:41                 - tenant identifiers in payloads or schemas;          ← a prohibition
PROMPT.md:163                - FastAPI routers/use cases/repositories;              ← a prohibition
CONTRACT_STANDARD.md:179     - asyncpg pool objects;                               ← a prohibition
CONTRACT_STANDARD.md:181     - Casbin model/policy implementation;                 ← a prohibition
CONTRACT_STANDARD.md:185     - Terraform/Kubernetes implementation resources.      ← a prohibition
TEST_PLAN.md:21              1. insert a prohibited tenant field into a fixture → gate must fail;
```

The distinction — **a document naming a forbidden construct** versus **a forbidden construct existing in a contract-bearing path** — is exactly the false-positive class the EP-01 scanners must handle. Recorded here as a design input to EP-01:

> The EP-01 multi-tenancy and implementation-boundary scanners **must be path-scoped** to contract-bearing paths (`contracts/`, `catalog/`, `compatibility/`, `templates/`) rather than scanning the repository root indiscriminately. A root-wide scan would flag `PROMPT.md`, `HARNESS.md`, and `CONTRACT_STANDARD.md` — the very documents that mandate the scan — and the resulting pressure would be to weaken the scanner. `HARNESS.md` §7 and EP-05 both forbid resolving that by loosening a gate. Path scoping is the correct resolution; a blanket ignore-list is not.

C7 and C9 returning exit `1` with zero matches independently confirms the greenfield finding: no frontend source, no pre-existing schemas, no CI, no tests, no release metadata.

## 2. Conflict classification

Per EP-00 instruction 4, each item is classified `remove` / `migrate-to-owner-repo` / `replace` / `retain`.

| Item | Classification | Action |
|---|---|---|
| Multi-tenant constructs | `retain` | **Nothing to fix — none exist.** Only prohibitions in governance prose |
| Foreign-repo implementation code | `retain` | None exists |
| SQL / migrations / DB drivers / PgBouncer | `retain` | None exists. Authority stays with `ai-business-database` (`M0-CON-005`) |
| Auth / JWT / Casbin implementation | `retain` | None exists |
| LangGraph implementation | `retain` | None exists |
| Channel adapters / webhook handlers | `retain` | None exists |
| React / frontend source | `retain` | None exists |
| Deployment / IaC | `retain` | None exists |
| 11 root governing `.md` docs | `retain` | Seeded into the repository at commit A |
| `execution-prompts/` (7 files) | `retain` | Seeded at commit A |
| `evidence/` templates (9 files) | `replace` | This file replaced in commit B; the other 7 remain `NOT RUN` |
| pack `README.md` | `replace` | Repo `README.md` is an EP-01 deliverable |
| `.DS_Store` | `remove` | Not committed; gitignored |

**No item required `migrate-to-owner-repo`.** No material belonging to another of the frozen eight repositories was found.

## 3. Baseline inventory

```bash
$ git ls-tree -r --name-only m0-ep00-baseline | wc -l
28
$ git ls-tree -r --name-only m0-ep00-baseline | grep -c '.DS_Store'
0
$ git ls-tree -r --name-only m0-ep00-baseline | grep -Ec 'pyproject.toml|requirements.*txt|package.json|uv.lock|poetry.lock'
0
```

28 tracked files: 11 root governing docs + `.gitignore` + 7 execution prompts + 9 evidence templates. No OS artifacts, no dependency manifests.

## 4. Artifacts / hashes

Hashes are derived from the **blobs at `m0-ep00-baseline`**, not from the working tree. Hashing the working tree would be self-referential — this file cannot contain its own SHA-256, since writing the hash changes the hash. Reading from the tagged commit removes the circularity structurally.

```bash
BASELINE_SHA="$(git rev-parse m0-ep00-baseline)"
git ls-tree -r --name-only "$BASELINE_SHA" |
while IFS= read -r file; do
    hash="$(git show "$BASELINE_SHA:$file" | shasum -a 256 | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$file"
done
```

Exit code: `0`.

| Artifact | SHA-256 |
|---|---|
| `.gitignore` | `14e8fca1c387fc8743636c086db10b572fc19b58250bb037e6c8ad96999d1619` |
| `ACCEPTANCE_CRITERIA.md` | `6ce119c43f6c75cb32ccbc3403c9fcd3f2e109cbc988615a328202d6304c8c94` |
| `ARCHITECTURE_COMPLIANCE_MATRIX.md` | `a8e9629ef1588168338e6fb84935edc8a22ed4c06be5139386432d5483281f08` |
| `AUDITOR.md` | `01d400cce7790248eb993174d3581dbe82a97626e939bcdccb8c13b2d4287140` |
| `CONTRACT_STANDARD.md` | `6779e67016f3f9a8ee4d2f23dfe90b13db54e88c49781159c7f32dfe79680f88` |
| `CROSS_REPO_COMPATIBILITY.md` | `c81f1038e8b1e5979ffcc2f97924a61ff36a100d6df3572fffa49b30d42298c8` |
| `DELIVERY_REPORT.md` | `3183cb5307115b789591e65e3eb8f96d118756c5d2b76978a6fdcef43224afff` |
| `HARNESS.md` | `11863503d70a32eb5b4ee5c15336140077fbd9ffca612e1fbb077a45c674cec7` |
| `M0_MANIFEST.md` | `3e37cbfeb0a471f4ea24cdd8e80f4f4bd98298f57552e160901995fd35fc8d7b` |
| `PROMPT.md` | `d63fe7ee3ab3926c23fcb7ae533ddd8b6adf886de213948643e06ec7da83a54a` |
| `TARGET_REPOSITORY_TREE.md` | `4f87047ad731ac59b383b13392990595b5be5498c2d86186b020e9746c913c93` |
| `TEST_PLAN.md` | `95ccfed0c2c0e3019f2cbac904b9fcab73e0a7c4ae758fdc50748ed6121124cf` |
| `evidence/01-preflight.md` † | `02bff1ea53adf18210efb44a2b6489a537fdd7480e38e83a3b968335f05656d8` |
| `evidence/02-boundary.md` | `1cc1129634e11a2b2cb696fda594d83387221407f292adc8616cc5f22bd8e613` |
| `evidence/03-contract-validation.md` | `ade0c8b722f6832136fa174745cbf9f19bfd27be03b29fe2745ef05e0472da12` |
| `evidence/04-compatibility.md` | `0eabfeec2fea595505af32632a41e912cf92d3767c0cb5a6ab99187e66caef7e` |
| `evidence/05-quality-security.md` | `07914ed4a212d8fbfd12d61a6a5b7b0a8e27bad7e3bc2837af0d44f0c2b9c6cc` |
| `evidence/06-release-artifacts.md` | `c32937d8f154ab5ca879334902b1588a90ab159ada41383a10743f952233b0d8` |
| `evidence/07-cross-repo-readiness.md` | `3d5b8edcbb59a4ad7b1bbfb3f4664093ae921735d30859eee4fddbe1e0da7a7e` |
| `evidence/08-audit-verdict.md` | `c52658260997a17b6719aebc9089554c9c81610069e966b9afafad6167b5b5b5` |
| `evidence/EVIDENCE_INDEX.md` | `3b5d37370f30be42f28a12887b89670a09b1a82aadf676036c9d87432eb4f978` |
| `execution-prompts/EP-00-PREFLIGHT.md` | `21b73a1f141333ed4626bb5ce35fe56a9ca6d8ec0f4af4b32556023b49d3679c` |
| `execution-prompts/EP-01-BOUNDARY-AND-SCAFFOLD.md` | `374c731773e297e75c7a3b94297c1eed99c3f482196c113c80fc2acd1afde999` |
| `execution-prompts/EP-02-CONTRACT-FOUNDATION.md` | `7457d571e4f02d98ff9b81f2ea88d23ca666efc06966493ff81245c9142aa34a` |
| `execution-prompts/EP-03-GOVERNANCE-AND-COMPATIBILITY.md` | `3be556a7f22cd32f0f7831ea76bf32e5763b7d4ccfc1bc7c67947e3c3824797a` |
| `execution-prompts/EP-04-CONSUMER-PINNING-AND-PLATFORM-MATRIX.md` | `9cb2ce01ad6e9ab2f8a02d1f7ff6bef0abf0bd6364f7b20ff4b04b1bf60bcc1d` |
| `execution-prompts/EP-05-QUALITY-CI-AND-BUNDLE.md` | `10e7bb1affe54748010f494d1957609fa2abeefebf5ad1ec9310f2cf5a2426fb` |
| `execution-prompts/EP-06-EVIDENCE-AUDIT-DELIVERY.md` | `310396c37758ba74d67396e26d29f2aae0608f09ad2fed13333908739c2906b9` |

† This row is the hash of the **unmodified `NOT RUN` template** as it existed at commit A. The populated version — this document — is introduced in commit B and is deliberately **not** self-hashed.

## 5. Recorded decisions (inputs to EP-01 and later)

| Decision | Value |
|---|---|
| Repository location | Sibling directory `/Users/alifaraj/Downloads/ai-business-contracts`; execution pack left pristine |
| Scope of this run | **EP-00 only.** EP-01…EP-06 await separate authorization |
| Initial release version | `0.1.0` per `HARNESS.md` §5 (no prior repository history exists to conflict with it) |
| Validation toolchain | Pure Python via `uv`: `jsonschema`, `openapi-spec-validator`, `PyYAML`, `detect-secrets`, `pip-audit`, `ruff`, `mypy`, `pytest`. No npm, no brew binaries — one toolchain, one lockfile, CI reproduces it exactly |
| Secret scan | `detect-secrets` (supersedes absent `gitleaks`) |
| Dependency vulnerability scan | `pip-audit` (supersedes absent `trivy`) |
| Scanner scoping | Multi-tenancy and implementation-boundary scanners **must be path-scoped to contract-bearing paths** — see §1.1 |

### 5.1 AsyncAPI validation — provisional, not frozen

Structural AsyncAPI validation is acceptable **only while `contracts/asyncapi/` contains no published contracts.** Before the first AsyncAPI contract reaches `active`/released lifecycle state, validation must provide **specification-level AsyncAPI 3.x conformance**, not generic YAML/JSON structural validation.

This is recorded so a temporary implementation convenience cannot harden into the permanent contract-quality standard. `HARNESS.md` §7 and EP-05 both prohibit achieving a green gate by weakening it.

## 6. Acceptance criteria status

| Criterion | Status | Basis |
|---|---|---|
| `M0-CON-001` | **NOT RUN** — enforcement pending EP-01 | Repository purpose observed as contracts/governance only, but no boundary scanner exists yet |
| `M0-CON-002` | **NOT RUN** — enforcement pending EP-01 | Eight-repo authority map present in governance text; no catalog/matrix validation exists yet |
| `M0-CON-003` | **NOT RUN** — enforcement pending EP-01 | No prohibited multi-tenant construct observed, but no negative scanner or mutation test exists yet |
| `M0-CON-004` | **NOT RUN** — enforcement pending EP-01 | No foreign-repo implementation observed, but no boundary scanner or mutation test exists yet |
| `M0-CON-005` | **NOT RUN** — enforcement pending EP-01 | No SQL/migrations/PgBouncer observed; governance text assigns authority to `ai-business-database`; not yet machine-enforced |

**Why `NOT RUN` and not `PASS`.** Each of `M0-CON-001..005` names its evidence as a *scanner plus mutation test*. Preflight observed the absence of violations; it did not prove the repository can *detect* one. `TEST_PLAN.md` Layer A requires two mutation tests — inject a tenant field, inject an implementation file — and both must fail the gate. Until EP-01 delivers those, `PASS` would be unsupported. `ACCEPTANCE_CRITERIA.md` treats `NOT RUN` as `FAIL` for milestone completion, which is the correct state: **M0 does not pass at EP-00, and is not claimed to.**

## 7. Unresolved findings

**Blocking:** none.

**Non-blocking, carried to EP-01:**

1. Scanner path-scoping is mandatory (§1.1). A root-wide scan flags the governing documents themselves.
2. `evidence/02-boundary.md` … `08-audit-verdict.md` remain `NOT RUN`.
3. Repository `README.md` must be authored — the seeded pack `README.md` was excluded as pack-specific.
4. `M0-CON-001..005` require scanners and mutation tests before any `PASS` claim.
5. AsyncAPI validator fidelity must be upgraded before the first AsyncAPI contract becomes active (§5.1).

## 8. Exit condition

`EP-00-PREFLIGHT.md` requires: *"A complete inventory exists and there is no unresolved ambiguity about what belongs in this repo for M0."*

**Met.** Repository identity, branch, and commit SHA are recorded; all 28 files are inventoried and hashed at a tagged baseline; all ten conflict searches executed with real exit codes; every category classified; no ambiguity remains. Ownership boundaries are unchanged — no material was found belonging to another of the frozen eight repositories.

**EP-01 through EP-06 have not been executed.**
