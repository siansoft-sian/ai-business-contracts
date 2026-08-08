# Evidence — Release Artifacts & Reproducibility

Status: **PASS**

- Repository: `ai-business-contracts`
- Commit SHA: `ead4b16a0e25ca0bd8c4868f48b567ae297daae7`
- Timestamp UTC: `2026-08-08T16:20:00Z` (run A) / `2026-08-08T16:20:19Z` (run B,
  independent clean checkout)
- Execution prompt: `execution-prompts/EP-05-QUALITY-CI-AND-BUNDLE.md`

Gate and security evidence is in [`05-quality-security.md`](05-quality-security.md).

## Commands executed

```text
# Run A — in place, at a clean tree
rm -rf dist && mkdir -p dist
./scripts/quality_gate.sh

# Run B — independent clean checkout of the same commit
git clone --no-hardlinks . <tmp>/clean2
cd <tmp>/clean2 && git checkout ead4b16
uv sync --locked --all-groups
./scripts/quality_gate.sh

diff /tmp/sumsA <tmp>/clean2/dist/SHA256SUMS
```

## Exit codes

| Command | Exit code |
|---|---:|
| `./scripts/quality_gate.sh` (run A) | `0` |
| `uv sync --locked --all-groups` (clean checkout) | `0` |
| `./scripts/quality_gate.sh` (run B, clean checkout) | `0` |
| `diff` of the two `SHA256SUMS` | `0` (identical) |
| `uv run python scripts/build_bundle.py` | `0` |
| `uv run python scripts/verify_bundle.py` | `0` |
| `uv run python scripts/verify_consumer_lock.py --lock dist/example-consumer-lock.yaml --manifest dist/contract-manifest.json --verify-manifest-digest` | `0` |

## Results

### 1. Reproducibility is byte-level, from a commit

`TEST_PLAN.md` Layer E asks for build → record → delete `dist/` → rebuild →
compare. That was done twice: within one checkout, and across two independent
checkouts on different paths. `SHA256SUMS` is identical in every case.

```text
run A:  4d2609873d8d7a37f0dafaec12e2f7ca851eb8082a5969d45452cafcf533377d  ai-business-contracts-0.1.0.tar.gz
        b521f2b0838a9da02827eb6ebfb3ffb50341a77f19304ca66a90c5f086a04ba4  compatibility-summary.json
        15534a2d8e162ea449994a2429e615e27373d7edfcc72ad84f1e822b495a6c5d  contract-manifest.json

run B:  4d2609873d8d7a37f0dafaec12e2f7ca851eb8082a5969d45452cafcf533377d  ai-business-contracts-0.1.0.tar.gz
        b521f2b0838a9da02827eb6ebfb3ffb50341a77f19304ca66a90c5f086a04ba4  compatibility-summary.json
        15534a2d8e162ea449994a2429e615e27373d7edfcc72ad84f1e822b495a6c5d  contract-manifest.json
```

Five inputs that would otherwise vary per machine and per run are pinned:

| Input | Normal value | What is used | Why it matters |
|---|---|---|---|
| Member mtime | file mtime | commit time | a checkout's mtimes are its clone time |
| gzip header | build time + source filename | `mtime=0`, no filename | header bytes change the digest without changing contents |
| Owner / group | building user | `0` / `""` | the artifact would otherwise name whoever built it |
| Permissions | umask-dependent | `0o644` | a different umask would change the archive |
| Member order | filesystem order | sorted by archive path | ordering must be a property of content |

And `built_at_utc` in the manifest is the **commit time**, not the wall clock.
This is the load-bearing choice. A wall-clock build timestamp would make the
manifest differ on every rebuild, so the manifest's own digest — the value a
consumer pins as `manifest_sha256` — could never be verified by rebuilding.
What a consumer needs to know is which source produced the artifact, and that
is a property of the commit.

`tests/test_bundle.py` asserts each of these directly rather than comparing
file listings: a listing comparison would pass even while the archive embedded
the building user.

### 2. Bundle contents and exclusions — `M0-CON-037`

35 files. Top-level entries: `README.md`, `catalog/`, `compatibility/`,
`contracts/`, `governance/`, `templates/`.

Governance ships with the contracts deliberately: contracts without the rules
governing how they change are a snapshot, not a contract.

Excluded and asserted excluded: `tests/`, `scripts/`, `dist/`, `evidence/`,
`execution-prompts/`, `.git`, `.github`, `.venv`, `__pycache__` and the other
tool caches, `.env` and credential-shaped filenames, and compiled or key
suffixes.

`compatibility/fixtures/` is excluded specifically. Those fixtures are curated
proofs of the compatibility engine, and several deliberately contain invalid or
breaking contract source. Shipping them would put artifacts into a release that
this repository's own validators exist to reject. The rest of `compatibility/`
— `policy.md`, `platform-m0-matrix.yaml`, `baseline.yaml` — is published, and a
test asserts both halves.

**The exclusion rule is proven able to fail.** Asserting that today's bundle
happens to contain no test files says almost nothing. Five parametrised tests
repack the bundle with an injected member — a test file, a negative fixture,
`.env`, a `__pycache__` entry, and a tooling script — and assert the verifier
rejects each.

### 3. The verifier is independent of the builder

`_release.py` states inclusion **positively** (which directories are published).
`verify_bundle.py` states exclusion **negatively and separately** (what may
never appear, in terms of what the material *is*). A verifier that reused the
builder's own path selection could only ever confirm the builder agreed with
itself, and would pass unchanged if the selection rule were wrong.

Beyond exclusions, `verify_bundle.py` checks and is proven able to fail on:
a tampered archive breaking `bundle_sha256`; an edited manifest breaking its
recorded checksum; a falsified `source_sha256`; a manifest entry the catalog
does not declare; a catalogued source missing from the archive; a missing
manifest; archive members carrying ownership or escaping paths.

### 4. The manifest identifies commit and per-contract checksums — `M0-CON-038`

```json
{
  "repository": "ai-business-contracts",
  "version": "0.1.0",
  "commit_sha": "ead4b16a0e25ca0bd8c4868f48b567ae297daae7",
  "built_at_utc": "2026-08-08T16:19:48Z",
  "bundle_sha256": "4d2609873d8d7a37f0dafaec12e2f7ca851eb8082a5969d45452cafcf533377d",
  "governance_version": "1",
  "compatibility_result": "no-baseline"
}
```

All 8 catalogued contracts are published, each with stable ID, version, type,
lifecycle, owner, consumers, source path, and `source_sha256` — the real digest
of the source, asserted by test against a recomputation.

The manifest validates against `urn:ai-business:contracts:common:release-manifest:v1`,
the contract defined in EP-04 *before* the generator existed. The release
tooling therefore produces a document conforming to an existing contract rather
than defining the shape by accident.

`compatibility_result` is `no-baseline`, carried through from the compatibility
summary. `build_bundle.py` refuses to publish over a `fail` verdict —
`test_build_refuses_a_failing_compatibility_verdict` asserts it exits `1` and
writes no manifest.

### 5. Published metadata is sufficient for a consumer — `M0-CON-041`

This is the criterion that trailed EP-04, and it is now proven rather than
asserted.

`build_bundle.py` emits `dist/example-consumer-lock.yaml` filled in from
nothing but the release's own artifacts. `verify_consumer_lock.py` then
verifies that lock against that release, including hashing the manifest file
and comparing it to the lock's `manifest_sha256`:

```text
verify_consumer_lock: PASS - lock verified against release 0.1.0
```

If a field a consumer needs were missing from the manifest or the checksums,
this round trip could not complete. That is the difference between publishing
metadata and publishing metadata that *works*.

The EP-04 finding that a fabricated manifest with a matching self-digest would
pass is now closed: `SHA256SUMS` exists and is the outer record a release is
identified by. Without it a consumer could only check a manifest against
itself.

## Artifacts / hashes

| Artifact | SHA-256 |
|---|---|
| `dist/ai-business-contracts-0.1.0.tar.gz` | `4d2609873d8d7a37f0dafaec12e2f7ca851eb8082a5969d45452cafcf533377d` |
| `dist/contract-manifest.json` | `15534a2d8e162ea449994a2429e615e27373d7edfcc72ad84f1e822b495a6c5d` |
| `dist/SHA256SUMS` | `2846eca5595f25574dcbb37875704734b787df0f5543c8a1ffab8f6bbe823dd8` |
| `dist/compatibility-summary.json` | `b521f2b0838a9da02827eb6ebfb3ffb50341a77f19304ca66a90c5f086a04ba4` |
| `dist/example-consumer-lock.yaml` | `35a5dc913712c53e687a38a5e97c56e34d98ba324f0237d23621c7099a581595` |
| `evidence/m0-summary.json` | `be66b16bbb54864cd8d44bf4a382da0e5a07473f64455c58b3131c579e456b0a` |

All five `CROSS_REPO_COMPATIBILITY.md` required outputs are present. `dist/` is
git-ignored; the artifacts are reproducible from commit
`ead4b16a0e25ca0bd8c4868f48b567ae297daae7` by running the gate.

## Acceptance criteria supported

| ID | Status | Basis |
|---|---|---|
| `M0-CON-036` | PASS | Bundle, manifest, checksums, compatibility summary, and M0 summary generated; identical `SHA256SUMS` across two independent checkouts |
| `M0-CON-037` | PASS | 35 members, contract and governance artifacts only; five injection tests prove the exclusion rule rejects |
| `M0-CON-038` | PASS | Manifest carries `commit_sha` and a real `source_sha256` per contract; validated against `release-manifest.v1` |
| `M0-CON-041` | PASS | Lock generated from the release verifies against it, manifest digest included |
| `M0-CON-022` | PASS (reaffirmed) | Immutability machine-enforced by `released-version-content-changed`; release workflow checks tag against manifest version |
| `M0-CON-042` | PASS (reaffirmed) | Fail-closed verification exercised inside the gate against real artifacts, not only fixtures |

## Unresolved findings

**1. The first clean-checkout run was not fully reproducible.** At `c6807dd`
the bundle and manifest matched byte for byte but `compatibility-summary.json`
did not: its `checked_at_utc` came from the wall clock, and `SHA256SUMS` covers
that file — so a release's own checksum record differed on every rebuild,
leaving nothing stable to verify a republished release against. Fixed at
`ead4b16`: the gate now stamps the summary from the commit time, matching what
`build_bundle.py` already did for `built_at_utc`. The wall-clock time the gate
actually ran is still recorded in `evidence/m0-summary.json`, where a real
execution timestamp belongs. **Resolved; the run above is post-fix.**

**2. No release has been published, so immutability is untested in the field.**
`baseline_release` is still `null`, `compatibility_result` is `no-baseline`,
and no tag exists. The rule is machine-enforced by the compatibility engine and
the release workflow checks tag/manifest agreement, but neither has run against
a real published release. **Expected at M0; the first publication of `0.1.0`
converts this from enforced-in-principle to enforced-in-practice.**

**3. `governance_version` is a constant.** It is `"1"` in `_release.py` and
nothing enforces that it is bumped when a governance rule changes in a way that
alters how a release must be interpreted. A gate can currently tell *which*
generation a release claims, but cannot tell whether the claim is accurate.
**Non-blocking; no governance change has occurred since the constant was
introduced.**

**4. The bundle's root file set is a judgement call.** `README.md` ships;
`CONTRACT_STANDARD.md` and `CROSS_REPO_COMPATIBILITY.md` do not, on the grounds
that they are inputs to this milestone rather than outputs of this repository.
A consumer wanting the normative URN and envelope conventions must read them in
the repository rather than in the bundle. **Non-blocking; recorded so the audit
can disagree.**

**5. `dist/gate-checks.tsv` is an intermediate, not an artifact.** It is written
by the gate and consumed by `write_evidence_summary.py`, is not in
`SHA256SUMS`, and is not published. Its content is reproduced in
`evidence/m0-summary.json`, which is the durable record. **Non-blocking.**
