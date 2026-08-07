# Evidence — Preflight & Conflict Inventory

EP-00 Status: **COMPLETE** (inventory recorded; re-executed and re-verified across three runs)

- Repository: `ai-business-contracts`
- Repository URL: `https://github.com/siansoft-sian/ai-business-contracts.git` (remote `origin`) — **unreachable at Run 3, see §D.2**
- Branch: `main`
- Baseline audited commit (Run 1): `13afef142f24b1bca5a5979cc7aaefc20d284ce0` (tag: `m0-ep00-baseline`)
- Re-execution audited commit (Run 2): `a29b4be5d6a71ea1f07b24c243922f995c112f75`
- Re-execution audited commit (Run 3): `f15a44caa99f4850281d9d4b2e6eef2dbfabd24a`
- Timestamp UTC — Run 1: `2026-08-07T16:27:25Z`
- Timestamp UTC — Run 2: `2026-08-07T16:55:17Z`
- Timestamp UTC — Run 3: `2026-08-07T17:26:14Z`
- Working-tree status at Run 3 observation: **NOT clean** — this document and `EVIDENCE_INDEX.md` had been reverted to their commit-A templates. See §D.1.
- Executed by: EP-00 per `execution-prompts/EP-00-PREFLIGHT.md`

> **No acceptance criterion is marked `PASS` in this document.** EP-00 *observes* the starting state; it does not *enforce* it. See §6. Neither Run 2 nor Run 3 changed this: neither added a scanner or a mutation test, so neither could upgrade any criterion.

## 0. Commit model

Evidence cannot describe the commit that contains it. EP-00 therefore anchors each run to an already-committed state:

```text
A  chore: bootstrap ai-business-contracts M0 governing pack   ← tag: m0-ep00-baseline
│                                                             ← Run 1 executed against THIS state
B  docs(evidence): record EP-00 preflight                     ← Run 1 output
│                                                             ← Run 2 executed against THIS state
C  docs(evidence): re-execute EP-00 preflight                 ← Run 2 output
│                                                             ← Run 3 executed against THIS state
D  docs(evidence): EP-00 preflight run 3                      ← Run 3 output (this revision)
│
HEAD
```

Run 1 searches, inventories, and hashes were executed against `m0-ep00-baseline`. Run 2 against commit `a29b4be`. Run 3 against commit `f15a44c`. **None was executed against the working tree.** Anchoring to a committed object rather than to `HEAD^` keeps every figure below reproducible after later commits — a property Run 3 depended on, since its working tree was not clean (§D.1).

**Why Run 2 exists.** Run 1 observed a repository that had no remote and no published tag, so `EP-00-PREFLIGHT.md` instruction 1 ("record repository URL") could not be satisfied at the time. Both facts have since changed. Run 2 re-executes the full instruction set against the current committed state rather than inheriting Run 1's figures. Run 1's observations are retained verbatim in Sections A and B: they are the only record of the true greenfield starting state, and EP-00 instruction 5 forbids deleting evidence of the initial state.

**Why Run 3 exists.** Two conditions, both regressions rather than progress:

1. This document had been **reverted in the working tree to its commit-A `NOT RUN` template**, discarding the Run 1 and Run 2 record from the checkout. The repository presented itself as having no preflight evidence at all.
2. Run 2 closed finding 6 by asserting that `m0-ep00-baseline` was published to `origin`, making §4's hash table reproducible from a fresh clone. `origin` is no longer reachable (§D.2), so that assertion is no longer verifiable and the finding is reopened.

Run 3 is pure observation plus one recovery action (`git restore`), recorded in §D.1. Sections A, B, C and §1, §3, §4, §5 are unchanged from the Run 2 revision.

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

## Section C — Run 2 re-execution (observation, against commit `a29b4be`)

Run 2 re-executes every EP-00 instruction against the current committed state. **No mutation was performed during Run 2** — it is pure observation.

### C.1 Identity and working-tree status (instruction 1)

```bash
$ git remote -v
$ git rev-parse --abbrev-ref HEAD
$ git rev-parse HEAD
$ git status --porcelain
$ git tag -l && git ls-remote --tags origin
$ git rev-parse HEAD origin/main
$ date -u +%Y-%m-%dT%H:%M:%SZ
```

| Field | Value | Exit |
|---|---|---:|
| Repository URL | `https://github.com/siansoft-sian/ai-business-contracts.git` | `0` |
| Branch | `main` | `0` |
| Commit SHA | `a29b4be5d6a71ea1f07b24c243922f995c112f75` | `0` |
| Working-tree status | clean (`git status --porcelain` produced no output) | `0` |
| Local tag | `m0-ep00-baseline` → `13afef14…` | `0` |
| Remote tag | `refs/tags/m0-ep00-baseline` → `13afef14…` | `0` |
| `HEAD` vs `origin/main` | identical (`a29b4be…` both) | `0` |

**Change since Run 1.** Run 1 recorded no repository URL because no remote existed. A remote now exists and `m0-ep00-baseline` is published to it, so the Run 1 hash table is now reproducible from a fresh clone — see §7 finding 6, now closed.

### C.2 Inventory (instruction 2)

```bash
$ git ls-tree -r --name-only a29b4be | wc -l
$ git ls-tree -r --name-only a29b4be | grep -Ec 'pyproject\.toml|requirements.*\.txt|package\.json|package-lock\.json|uv\.lock|poetry\.lock|Pipfile'
$ git ls-tree -r --name-only a29b4be | grep -c 'DS_Store'
```

| Check | Exit | Result |
|---|---:|---|
| tracked file count | `0` | `28` — unchanged from baseline |
| dependency manifests | `1` | `0` — still none declared |
| OS artifacts | `1` | `0` |

Directory probe for contract-bearing paths:

| Path | State |
|---|---|
| `contracts/` `catalog/` `compatibility/` `governance/` `templates/` `scripts/` `tests/` `dist/` `.github/` | **all ABSENT** |

Consistent with §B.3: these are EP-01/EP-02 deliverables and were deliberately not created.

### C.3 Commit B content verification

```bash
$ git diff --name-status 13afef14 a29b4be
```

| Exit | Result |
|---:|---|
| `0` | `M evidence/01-preflight.md`, `M evidence/EVIDENCE_INDEX.md` — 2 files, +290/−17 |

Commit B modified evidence records only. **No governing document, execution prompt, or `.gitignore` was altered after the baseline**, which is why 26 of the 28 blob hashes in §4 are identical across both runs.

### C.4 Secret-shaped pattern scan (new in Run 2)

Not performed in Run 1. This is a coarse pattern check, **not** a substitute for the `detect-secrets` gate that EP-05 must deliver.

```bash
$ git grep -n -I -E -i 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{32}|postgres(ql)?://[^ ]*:[^ ]*@' a29b4be
```

Exit `1` — **no match**. Recorded as an observation supporting `M0-CON-034`, which remains `NOT RUN` until the real scanner runs under EP-05.

### C.5 Toolchain re-inventory

| Tool | Version | Status | Δ vs Run 1 |
|---|---|---|---|
| `git` | 2.55.0 | present | — |
| `python3` | 3.12.2 | present | — |
| `pip3` | 25.2 | present | — |
| `uv` | 0.6.14 | present | — |
| `node` | v26.4.0 | present | — |
| `npm` | 11.17.0 | present | — |
| `docker` | 29.6.1 | present | — |
| `shasum` | 6.02 | present | — |
| `jq` | — | **absent** | — |
| `gitleaks` | — | **absent** | — |
| `trivy` | — | **absent** | — |

Unchanged. Git identity `siansoft <siansoft@gmail.com>`; `init.defaultBranch` still unset.

---

## Section D — Run 3 re-execution (observation, against commit `f15a44c`)

Run 3 re-executes every EP-00 instruction against the current committed state. Unlike Runs 1 and 2 it began with a **dirty working tree**, and that divergence is itself the principal finding.

### D.1 Identity, working-tree status, and the evidence revert (instruction 1)

EP-00 instruction 5 — *"do not delete evidence of the initial state before recording it"* — governs here. The pre-restore state was captured **before** any recovery action:

```bash
$ date -u +%Y-%m-%dT%H:%M:%SZ
$ git status --porcelain
$ git diff --stat
$ shasum -a 256 evidence/01-preflight.md evidence/EVIDENCE_INDEX.md README.md
$ git rev-parse HEAD
$ git rev-parse m0-ep00-baseline
$ git check-ignore -v .DS_Store
$ wc -l evidence/01-preflight.md
```

| Field | Value | Exit |
|---|---|---:|
| Repository URL | `https://github.com/siansoft-sian/ai-business-contracts.git` | `0` |
| Branch | `main` | `0` |
| Commit SHA | `f15a44caa99f4850281d9d4b2e6eef2dbfabd24a` | `0` |
| `HEAD` vs `origin/main` (local ref) | identical — `f15a44c…` both | `0` |
| Local tag | `m0-ep00-baseline` → `13afef14…` | `0` |
| Working-tree status | **NOT clean** — ` M evidence/01-preflight.md`, ` M evidence/EVIDENCE_INDEX.md`, `?? README.md` | `0` |
| `git diff --stat` | `2 files changed, 17 insertions(+), 490 deletions(-)` | `0` |
| `.DS_Store` on disk | present, 6148 bytes; ignored via `.gitignore:6` | `0` |

**The revert is exactly a checkout of commit A.** The pre-restore working-tree digests were not arbitrary — they reproduce the §4 baseline table row-for-row:

| File | Working-tree SHA-256 (pre-restore) | Matches |
|---|---|---|
| `evidence/01-preflight.md` | `02bff1ea53adf18210efb44a2b6489a537fdd7480e38e83a3b968335f05656d8` | §4 baseline row — the unmodified `NOT RUN` template at commit A |
| `evidence/EVIDENCE_INDEX.md` | `3b5d37370f30be42f28a12887b89670a09b1a82aadf676036c9d87432eb4f978` | §4 baseline row |
| `README.md` (untracked) | `e6283f0fc91470a08ac7579f23617f4070e8f6a447b62676af0196d9326ece27` | pack `README.md`, never committed (§B.1) |

`wc -l` confirms the magnitude: **37 lines in the working tree against 510 at `f15a44c`.** The Run 1 and Run 2 record — every command, exit code, and hash — was absent from the checkout. Per `HARNESS.md` §7 and `EVIDENCE_INDEX.md`'s own rule, *templates are not evidence*: the repository was presenting itself as having no preflight record.

**Recovery action (the only mutation in Run 3):**

```bash
$ git restore evidence/01-preflight.md evidence/EVIDENCE_INDEX.md
```

| Command | Exit | Post-condition |
|---|---:|---|
| `git restore` (2 files) | `0` | digests returned to `050e2933…` and `6e9c8198…` — byte-identical to `f15a44c` (§D.7) |
| `git status --porcelain` (after) | `0` | `?? README.md` only |

Untracked `README.md` was **not** removed or committed. It is the pack README, classified `replace` at §B.1; authoring the repository README remains an EP-01 deliverable (finding 3).

### D.2 Remote reachability — finding 6 reopened

```bash
$ git remote -v
$ git ls-remote --heads --tags origin
```

| Command | Exit | Result |
|---|---:|---|
| `git remote -v` | `0` | `origin https://github.com/siansoft-sian/ai-business-contracts.git` (fetch + push) |
| `git ls-remote --heads --tags origin` | `128` | `remote: Repository not found.` / `fatal: repository '…/ai-business-contracts.git/' not found` |

`origin/main` still resolves **locally** to `f15a44c` — a stale remote-tracking ref proving a fetch or push succeeded at some earlier point. It is not evidence that the remote is reachable now.

**Cause is indeterminate and is not guessed here.** GitHub returns `Repository not found` both for a deleted/renamed repository and for a private repository accessed without credentials. This session is non-interactive and the claude.ai GitHub connector is unauthenticated, so the two cannot be distinguished. `gh` is installed (§D.6) but was deliberately not used to probe: the recorded decision for this run was to state the ambiguity rather than resolve it.

**Consequence.** Run 2 closed finding 6 on the basis that `m0-ep00-baseline` was published to `origin`, making §4's hash table reproducible by an auditor from a fresh clone. That reproducibility cannot currently be demonstrated. **Finding 6 is reopened** (§7). The §4 table remains internally verifiable from the local object store — §4.1 and §D.7 both reproduce it — but *local* verification is weaker than the fresh-clone property Run 2 claimed.

### D.3 Inventory (instruction 2)

```bash
$ git ls-tree -r --name-only f15a44c | wc -l
$ git ls-tree -r --name-only f15a44c | grep -Ec 'pyproject\.toml|requirements.*\.txt|package\.json|package-lock\.json|uv\.lock|poetry\.lock|Pipfile'
$ git ls-tree -r --name-only f15a44c | grep -c 'DS_Store'
$ git ls-tree -r --name-only f15a44c | grep -Ec '^(contracts|catalog|compatibility|governance|templates|scripts|tests|dist|\.github)/'
$ git diff --name-status a29b4be f15a44c
```

| Check | Exit | Result | Δ vs Run 2 |
|---|---:|---|---|
| tracked file count | `0` | `28` | unchanged |
| dependency manifests | `1` | `0` — still none declared | unchanged |
| OS artifacts tracked | `1` | `0` | unchanged |
| files under contract-bearing paths | `1` | `0` | unchanged |
| `a29b4be` → `f15a44c` | `0` | `M evidence/01-preflight.md`, `M evidence/EVIDENCE_INDEX.md` (+216/−16) | commit C touched evidence only |

Directory probe (working tree and git tree agree):

| Path | State |
|---|---|
| `contracts/` `catalog/` `compatibility/` `governance/` `templates/` `scripts/` `tests/` `dist/` `.github/` | **all ABSENT** |

Consistent with §B.3 and §C.2: these are EP-01/EP-02 deliverables, deliberately not created. **No contract-bearing path exists in this repository at Run 3.**

### D.4 Conflict searches (instruction 3)

The same ten patterns from §1, re-executed against `f15a44c`.

| # | Category | Exit | Lines | Files | Δ vs Run 2 |
|---|---|---:|---:|---:|---|
| C1 | Multi-tenant constructs | `0` | 42 | 15 | +6 lines |
| C2 | Foreign-repo implementation (FastAPI/runtime) | `0` | 9 | 6 | +1 line |
| C3 | SQL / migrations / DB drivers / PgBouncer | `0` | 24 | 12 | +1 line |
| C4 | Auth / JWT / Casbin | `0` | 8 | 5 | +1 line |
| C5 | LangGraph | `0` | 20 | 11 | +1 line |
| C6 | Channel adapters / webhooks | `0` | 6 | 3 | +1 line |
| C7 | React / frontend | `0` | 2 | 1 | +1 line |
| C8 | Deployment / IaC | `0` | 4 | 3 | unchanged |
| C9 | Existing schemas / CI / tests / release metadata | `0` | 2 | 1 | +1 line |
| C10 | Prohibited file types | `1` | 0 | 0 | unchanged |

**C10 remains exit `1` — zero `.sql`, `.tf`, `.tsx`, `.ts`, `.js`, `.py`, `.yaml`, `.toml`, or `.env` files are tracked.** All 28 tracked files are `.md` plus `.gitignore`.

#### D.4.1 Every match is outside contract-bearing scope — verified, not assumed

Run 2 asserted this by inspection. Run 3 verifies it mechanically: the union of all files matched by C1–C9 was intersected against the contract-bearing prefixes.

```bash
$ for pat in <C1..C9 patterns>; do git grep -l -I -E -i "$pat" f15a44c; done \
    | sed 's|^f15a44c:||' | sort -u \
    | grep -E '^(contracts|catalog|compatibility|governance|templates)/'
```

Exit `1` — **no match.** The 17 files matched across all nine categories are: 11 root governing `.md` documents, 5 execution prompts, and `evidence/01-preflight.md`. Not one lies in a contract-bearing path, because none exists (§D.3).

#### D.4.2 Self-matching is compounding, as §1.3 predicted

The §1.3 warning was that `evidence/` is a false-positive source that *grows every time evidence is written*. Run 3 is the second consecutive confirmation, and the C7/C9 series makes it unambiguous:

| Category | Run 1 (`13afef14`) | Run 2 (`a29b4be`) | Run 3 (`f15a44c`) |
|---|---:|---:|---:|
| C7 React / frontend | 0 | 1 | 2 |
| C9 Schemas / CI / tests | 0 | 1 | 2 |

Both C7 matches at `f15a44c` are the evidence file quoting its own pattern:

```text
evidence/01-preflight.md:253  | C7 | React / frontend | `from 'react'\|useState\|…` | `1` | 0 | 0 |
evidence/01-preflight.md:301  evidence/01-preflight.md:155  | C7 | React / frontend | …
```

Line 301 is Run 2 *quoting Run 1's row* — a second-order match. The growth is not linear in contract content, which is zero; it is linear in evidence written. `evidence/01-preflight.md` alone now accounts for 12 of the 42 C1 matches.

> **Binding input to EP-01, restated and now twice-confirmed.** The multi-tenancy and implementation-boundary scanners must be **path-scoped to contract-bearing paths** (`contracts/`, `catalog/`, `compatibility/`, `templates/`). `evidence/`, `execution-prompts/`, and the root governing documents must be outside the scanned scope **by construction**, not by an ignore-list. An ignore-list would require a new exception on every evidence write — a gate that weakens monotonically as the milestone progresses, which `HARNESS.md` §7 and EP-05 both forbid.

#### D.4.3 C1 per-file classification (multi-tenancy)

All 42 C1 matches at `f15a44c`, by file:

```bash
$ git grep -c -I -E -i 'tenant' f15a44c
```

| File | Matches | Classification |
|---|---:|---|
| `PROMPT.md` | 11 | prohibition prose |
| `evidence/01-preflight.md` | 12 | prohibition prose / self-record |
| `TEST_PLAN.md` | 5 | prohibition prose |
| `HARNESS.md` | 3 | prohibition prose |
| `ACCEPTANCE_CRITERIA.md`, `ARCHITECTURE_COMPLIANCE_MATRIX.md`, `AUDITOR.md`, `CONTRACT_STANDARD.md`, `CROSS_REPO_COMPATIBILITY.md`, `DELIVERY_REPORT.md`, `M0_MANIFEST.md` | 1 each | prohibition prose |
| `execution-prompts/EP-00, EP-01, EP-02, EP-05` | 1 each | prohibition prose |

**42 of 42 are governance prose forbidding the construct. Zero are tenant identifiers, headers, contexts, scopes, routing, or storage semantics.** The entire +6 delta versus Run 2 originates from this document.

This is an observation of absence, not a `PASS` — see §6.

### D.5 Secret-shaped pattern scan

```bash
$ git grep -n -I -E -i 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{32}|postgres(ql)?://[^ ]*:[^ ]*@' f15a44c
```

Exit `1` — **no match**, unchanged from Run 2. This is a hand-written grep, **not** the `detect-secrets` gate EP-05 must deliver. `M0-CON-034` stays `NOT RUN` (finding 8).

### D.6 Toolchain re-inventory

| Tool | Version | Status | Δ vs Run 2 |
|---|---|---|---|
| `git` | 2.55.0 | present | — |
| `python3` | 3.12.2 | present | — |
| `pip3` | 25.2 | present | — |
| `uv` | 0.6.14 | present | — |
| `node` | v26.4.0 | present | — |
| `npm` | 11.17.0 | present | — |
| `docker` | 29.6.1 | present | — |
| `shasum` | 6.02 | present | — |
| `gh` | 2.96.0 | present | **newly recorded** (not inventoried in Runs 1–2) |
| `jq` | — | **absent** | — |
| `gitleaks` | — | **absent** | — |
| `trivy` | — | **absent** | — |

Git identity `siansoft <siansoft@gmail.com>`; `init.defaultBranch` still unset. The `detect-secrets` / `pip-audit` substitution recorded in §5 stands — `gitleaks` and `trivy` remain absent across all three runs.

### D.7 Blob hashes at `f15a44c`

```bash
git ls-tree -r --name-only f15a44c |
while IFS= read -r file; do
    hash="$(git show "f15a44c:$file" | shasum -a 256 | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$file"
done
```

Exit `0`. 28 files hashed, then diffed against a freshly recomputed `m0-ep00-baseline` table.

**26 of 28 blobs are byte-identical to the §4 baseline table** — independently reproducing §4.1's result a second time, and confirming that no governing document, execution prompt, or `.gitignore` has been altered since commit A. The two that differ are the evidence files touched by commits B and C:

| Artifact | SHA-256 at `f15a44c` | Note |
|---|---|---|
| `evidence/01-preflight.md` § | `050e2933aa3addaff9236c7c0084d72120dffd8507c043da469e884cb5c9f737` | Run 2 revision |
| `evidence/EVIDENCE_INDEX.md` | `6e9c8198deaf85bbfa5d46bd1ec499a609cc479710d8afe66e6f7eb5af69eac4` | Run 2 status row |

§ Same self-reference constraint as §4 and §4.2: this is the digest of the document **as Run 3 observed it**, before Section D was written. The revision you are reading is introduced in commit D and is deliberately **not** self-hashed. A document cannot contain its own digest.

The `050e2933…` value is also the post-restore verification target in §D.1: after `git restore`, the working-tree file hashed to exactly this, proving the recovery was byte-exact rather than approximate.

---

## 1. Conflict searches — Run 1 (executed against `m0-ep00-baseline`)

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

### 1.2 Conflict searches — Run 2 (executed against `a29b4be`)

Identical patterns, re-executed against the current committed state.

| # | Category | Exit | Lines | Files | Δ vs Run 1 |
|---|---|---:|---:|---:|---|
| C1 | Multi-tenant constructs | `0` | 36 | 15 | +6 lines, +1 file |
| C2 | Foreign-repo implementation (FastAPI/runtime) | `0` | 8 | 6 | +2 lines, +1 file |
| C3 | SQL / migrations / DB drivers / PgBouncer | `0` | 23 | 12 | +4 lines, +1 file |
| C4 | Auth / JWT / Casbin | `0` | 7 | 5 | +3 lines |
| C5 | LangGraph | `0` | 19 | 11 | +2 lines |
| C6 | Channel adapters / webhooks | `0` | 5 | 3 | +2 lines |
| C7 | React / frontend | `0` | 1 | 1 | **exit flipped `1` → `0`** |
| C8 | Deployment / IaC | `0` | 4 | 3 | +2 lines, +1 file |
| C9 | Existing schemas / CI / tests / release metadata | `0` | 1 | 1 | **exit flipped `1` → `0`** |
| C10 | Prohibited file types | `1` | 0 | 0 | unchanged |

### 1.3 Critical finding — the evidence file matches its own searches

**Every additional match in Run 2 originates from `evidence/01-preflight.md` itself.** No new match originates from a contract-bearing path, because no contract-bearing path exists (§C.2). The delta is entirely an artifact of Run 1 having *documented* the patterns it searched for.

The two exit-code flips make this unmistakable. C7 and C9 matched **nothing** at baseline; at `a29b4be` each matches exactly one line, and in both cases that line is the row in the Run 1 results table recording the pattern:

```text
evidence/01-preflight.md:155  | C7 | React / frontend | `from 'react'\|useState\|…` | `1` | 0 | 0 |
evidence/01-preflight.md:157  | C9 | Existing schemas / CI / … | `$schema\|^openapi:\|…` | `1` | 0 | 0 |
```

Both rows *record the absence* of the construct, and by doing so become a positive match for it.

**Consequence — §1.1's path-scoping requirement is now strictly broader than first stated.** Run 1 identified the governing root documents as the false-positive source. Run 2 shows `evidence/` is a second and growing source: every future evidence file that quotes a scanner pattern or a violation it detected will match that scanner. An evidence directory that records more will trip more gates.

> **Binding input to EP-01.** The multi-tenancy and implementation-boundary scanners must be **path-scoped to contract-bearing paths** (`contracts/`, `catalog/`, `compatibility/`, `templates/`). `evidence/`, `execution-prompts/`, and the root governing documents must be **outside the scanned scope by construction** — not by an ignore-list bolted onto a root-wide scan. The distinction matters: an ignore-list is a weakened gate that grows an exception every time evidence is written, and `HARNESS.md` §7 and EP-05 both forbid obtaining green by weakening a gate. Path scoping is a correctly-drawn boundary and does not reduce enforcement strength over the paths that carry contracts.

### 1.4 Line-by-line classification of C1 (multi-tenancy)

Because no-multi-tenancy is the strictest platform rule, all 36 C1 matches at `a29b4be` were inspected individually rather than counted:

```bash
$ git grep -n -I -E -i 'tenant' a29b4be
$ git grep -c -I -E -i 'tenant' a29b4be
```

| File | Matches | Classification |
|---|---:|---|
| `PROMPT.md` | 11 | prohibition prose |
| `evidence/01-preflight.md` | 6 | prohibition prose / self-record |
| `TEST_PLAN.md` | 5 | prohibition prose |
| `HARNESS.md` | 3 | prohibition prose |
| `ACCEPTANCE_CRITERIA.md` | 1 | prohibition prose |
| `ARCHITECTURE_COMPLIANCE_MATRIX.md` | 1 | prohibition prose |
| `AUDITOR.md` | 1 | prohibition prose |
| `CONTRACT_STANDARD.md` | 1 | prohibition prose |
| `CROSS_REPO_COMPATIBILITY.md` | 1 | prohibition prose |
| `DELIVERY_REPORT.md` | 1 | prohibition prose |
| `M0_MANIFEST.md` | 1 | prohibition prose |
| `execution-prompts/EP-00,01,02,05` | 4 | prohibition prose |

**36 of 36 are governance prose that forbids the construct. Zero are tenant identifiers, headers, contexts, scopes, routing, or storage semantics.** No schema, example, catalog entry, or contract artifact exists that could carry one.

This is an *observation of absence*, not a `PASS`. It does not demonstrate the repository can detect an injected tenant field — see §6.

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
| `evidence/` templates (9 files) | `replace` | This file replaced in commit B, extended in C and D; the other 7 remain `NOT RUN` |
| pack `README.md` | `replace` | Repo `README.md` is an EP-01 deliverable |
| `.DS_Store` | `remove` | Not committed; gitignored |

### 2.1 Items added by Run 3

| Item | Classification | Action |
|---|---|---|
| `evidence/01-preflight.md` reverted to the commit-A template in the working tree (§D.1) | `replace` | **Restored** via `git restore` to the `f15a44c` blob (`050e2933…`, verified byte-exact), then extended with Section D |
| `evidence/EVIDENCE_INDEX.md` reverted to the commit-A template | `replace` | Restored to `6e9c8198…`, then status row updated for Run 3 |
| Untracked pack `README.md` present on disk (`e6283f0f…`) | `replace` | **No action in EP-00.** Left untracked and unstaged; authoring the repository `README.md` is an EP-01 deliverable (finding 3) |
| `.DS_Store` on disk (6148 bytes) | `remove` | Still uncommitted; confirmed ignored by `.gitignore:6` |
| `origin` unreachable (§D.2) | — | Not a repository-content conflict. Recorded as reopened finding 6; no remote action attempted |

**No item required `migrate-to-owner-repo` in any of the three runs.** No material belonging to another of the frozen eight repositories was found at `13afef14`, `a29b4be`, or `f15a44c`.

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

### 4.1 Re-verification of the Run 1 hash table

The Run 1 table above was independently recomputed from the tagged baseline using the same command. **All 28 hashes reproduced exactly.** The Run 1 record is therefore verified, not merely asserted.

### 4.2 Blob hashes at `a29b4be` (Run 2)

```bash
git ls-tree -r --name-only a29b4be |
while IFS= read -r file; do
    hash="$(git show "a29b4be:$file" | shasum -a 256 | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$file"
done
```

Exit code: `0`. 28 files hashed. **26 of 28 are byte-identical to the baseline table in §4** — consistent with §C.3, which shows commit B touched only two files. The two that differ:

| Artifact | SHA-256 at `a29b4be` | Note |
|---|---|---|
| `evidence/01-preflight.md` ‡ | `003951e2f5460fb3e00b1964e22097c9b2a3f7017b5704afdcfe902584cc4129` | populated by commit B |
| `evidence/EVIDENCE_INDEX.md` | `b7d4e5c252a81435b3deac351d4b3987d614b4e681ca12e72000e4741cf39f31` | status row updated by commit B |

‡ Same self-reference constraint as before: this is the hash of the document **as Run 2 observed it**, before the Run 2 content was added. The revision you are reading is introduced in commit C and is deliberately **not** self-hashed. A document cannot contain its own digest.

## 5. Recorded decisions (inputs to EP-01 and later)

| Decision | Value |
|---|---|
| Repository location | Sibling directory `/Users/alifaraj/Downloads/ai-business-contracts`; execution pack left pristine |
| Scope of this run | **EP-00 only.** EP-01…EP-06 await separate authorization |
| Initial release version | `0.1.0` per `HARNESS.md` §5 (no prior repository history exists to conflict with it) |
| Validation toolchain | Pure Python via `uv`: `jsonschema`, `openapi-spec-validator`, `PyYAML`, `detect-secrets`, `pip-audit`, `ruff`, `mypy`, `pytest`. No npm, no brew binaries — one toolchain, one lockfile, CI reproduces it exactly |
| Secret scan | `detect-secrets` (supersedes absent `gitleaks`) |
| Dependency vulnerability scan | `pip-audit` (supersedes absent `trivy`) |
| Scanner scoping | Multi-tenancy and implementation-boundary scanners **must be path-scoped to contract-bearing paths** — see §1.1 and the strengthened form in §1.3 |
| Baseline tag publication | `m0-ep00-baseline` pushed to `origin`; the Run 1 hash table is now reproducible from a fresh clone (§C.1) |
| Repository URL | `https://github.com/siansoft-sian/ai-business-contracts.git` — recorded in Run 2; unavailable at Run 1 because no remote existed |

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

**Run 2 does not change any status above.** Re-running an observation more carefully produces better-characterised observation, not enforcement. Run 2 added no scanner, no mutation test, and no contract artifact; `M0-CON-001..005` therefore remain `NOT RUN`. Two specific temptations are recorded as rejected:

- The line-by-line C1 classification (§1.4) proves *no tenant construct is present*. It does not prove the repository *detects* one. `M0-CON-003` stays `NOT RUN`.
- The secret-shaped pattern scan (§C.4) returned no match. It is a hand-written grep, not `detect-secrets` under a gate. `M0-CON-034` stays `NOT RUN`.

`M0-CON-010` is likewise `NOT RUN`: §C.2 confirms every canonical directory is still absent.

**Run 3 does not change any status above either.** Run 3 added no scanner, no mutation test, and no contract artifact — it restored a reverted evidence file and re-observed. Three further temptations are recorded as rejected:

- §D.4.1 proves *mechanically* that no C1–C9 match lies in a contract-bearing path. It proves this only because **no contract-bearing path exists** (§D.3). An empty set trivially contains no violation; that is not detection. `M0-CON-003` and `M0-CON-004` stay `NOT RUN`.
- §D.7 reproduces 26 of 28 baseline blob hashes exactly. That is integrity verification of governance documents, not the release-manifest checksum machinery `M0-CON-038` requires. It stays `NOT RUN`.
- §D.1 shows the evidence chain was restorable byte-exact from git. Recoverability is not enforcement; no criterion is upgraded by it.

`M0-CON-010` remains `NOT RUN` at Run 3: §D.3 confirms all nine canonical directories are still absent in both the working tree and the git tree.

## 7. Unresolved findings

**Blocking:** none.

**Non-blocking, carried to EP-01:**

1. Scanner path-scoping is mandatory (§1.1); Run 2 widened it (§1.3) and Run 3 confirmed it a second time (§D.4.2): `evidence/` is a false-positive source that **grows every time evidence is written**, now demonstrably including second-order matches where one run quotes another's table. Scoping must be positive (scan only contract-bearing paths), not an ignore-list.
2. `evidence/02-boundary.md` … `08-audit-verdict.md` remain `NOT RUN`.
3. Repository `README.md` must be authored — the seeded pack `README.md` was excluded as pack-specific and is still present untracked at Run 3 (§D.1). Note `M0-CON-001` names the README as evidence, so this blocks that criterion.
4. `M0-CON-001..005` require scanners and mutation tests before any `PASS` claim.
5. AsyncAPI validator fidelity must be upgraded before the first AsyncAPI contract becomes active (§5.1).
6. **REOPENED at Run 3.** Run 2 closed this on the basis that `m0-ep00-baseline` was published to `origin`, making §4's hash table reproducible from a fresh clone. `git ls-remote origin` now exits `128` with `Repository not found` (§D.2), so that property cannot currently be demonstrated. Cause is indeterminate — deleted, renamed, or private-without-credentials are indistinguishable from the error. **Action required before delivery:** confirm the remote's true state and re-publish `m0-ep00-baseline` if needed. `M0-CON-043` expects evidence an auditor can reproduce; a local-only anchor is weaker than what Run 2 claimed.

**Carried to EP-05 (recorded so they are not lost):**

7. `jq`, `gitleaks`, and `trivy` are absent from the toolchain across all three runs. The §5 decision substitutes `detect-secrets` and `pip-audit`; that substitution must be implemented and evidenced, not assumed.
8. The §C.4 / §D.5 secret grep is a coarse observation, not a gate. It must not be cited as satisfying `M0-CON-034`.

**New at Run 3, carried to every subsequent EP:**

9. **Evidence held only in the working tree is not durable.** This document was found reverted to its commit-A template — 37 lines against 510, with the entire Run 1 and Run 2 record absent from the checkout (§D.1). An ordinary `git restore`/`git checkout` is sufficient to erase it, and recovery was possible only because commits B and C already existed. **Only committed evidence is evidence.** EP-01 through EP-06 must commit each evidence file as it is produced rather than accumulating it in an uncommitted tree, and the EP-06 auditor must verify evidence against committed blobs rather than the working tree.

## 8. Exit condition

`EP-00-PREFLIGHT.md` requires: *"A complete inventory exists and there is no unresolved ambiguity about what belongs in this repo for M0."*

**Met, and re-verified across three runs.** Repository identity, URL, branch, commit SHA, and working-tree status are recorded at each anchor — including Run 3's *non-clean* tree and its recovery (§D.1). All 28 files are inventoried and hashed at three committed anchors, with the Run 1 table independently reproduced byte-for-byte twice (§4.1, §D.7). All ten conflict searches were executed three times with real exit codes; every C1 match was classified individually (§1.4, §D.4.3); Run 3 additionally verified *mechanically* that no match falls inside a contract-bearing path (§D.4.1). Every category is classified (§2, §2.1). Ownership boundaries are unchanged across all three runs — no material was found belonging to another of the frozen eight repositories, and no `migrate-to-owner-repo` action was required at any anchor.

Two differences between runs are fully explained and neither is repository drift:

1. **Evidence self-matching** (§1.3, §D.4.2) — the document matches its own recorded patterns, now confirmed to compound across runs. This converts into a binding scanner-design constraint for EP-01 rather than a defect.
2. **Evidence revert and remote loss** (§D.1, §D.2) — both are regressions in the *record*, not in repository content. The 26 unchanged governance blobs (§D.7) prove no contract-bearing or governing material was altered. Both are carried as findings 9 and 6.

**Residual ambiguity:** none about repository content. One ambiguity remains about the *environment* — the state of `origin` (finding 6) — which does not affect what belongs in this repository for M0 but does affect auditor reproducibility and must be resolved before delivery.

**EP-01 through EP-06 have not been executed.** No acceptance criterion is claimed as `PASS` anywhere in this document.
