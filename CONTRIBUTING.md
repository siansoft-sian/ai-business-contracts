# Contributing to ai-business-contracts

This repository is a platform boundary. Changes here alter the language other
repositories depend on, so the process is deliberately stricter than for an
ordinary service repository.

## Before you start

Read `README.md` for what belongs here, and `governance/OWNERSHIP.md` for who
owns what. If your change adds implementation code, it belongs in another
repository - the boundary scanners will reject it, and that rejection is
correct.

## Contract-first workflow

1. **Propose** the contract change and its consumer impact
   (`governance/CHANGE_PROCESS.md`).
2. **Change the contract source** under `contracts/`, and register or update
   the entry in `catalog/contract-catalog.yaml`. Every contract has a stable
   id, a semantic version, exactly one owner, and explicit consumers.
3. **Add or update examples.** Examples are executable validation fixtures,
   not decorative samples.
4. **Run the gates locally** before opening a pull request.
5. **Get owner review.** The `CODEOWNERS` owner must approve. A compatibility
   result of `review_required` blocks automatic approval until the owner
   records a decision.

## Running the checks

One command runs every blocking check. CI runs this same script, so a green
local gate and a green CI mean the same thing.

```bash
uv sync --locked --all-groups
./scripts/quality_gate.sh
```

While iterating, use `--skip-release` to omit bundle generation:

```bash
./scripts/quality_gate.sh --skip-release
```

The release stage needs a **committed** working tree, because the manifest
names a commit SHA and building over uncommitted edits would pin content that
commit does not contain. `--skip-release` is the supported way to run the gate
mid-change; it is recorded in `evidence/m0-summary.json`, and every acceptance
criterion depending on a skipped check is reported `not_run` rather than
assumed. Changes under `evidence/` do not count as uncommitted work, since the
gate writes there itself and nothing in a release is derived from it.

Individual checks can still be run directly during debugging — each script
under `scripts/` takes `--json` and exits `1` on any finding — but the gate is
what decides whether a change is ready.

## Rules that are not negotiable

- **No implementation code.** Validation and release tooling under `scripts/`
  and `tests/` is the only executable code permitted.
- **No multi-tenancy.** No tenant identifier, header, context, routing,
  authorization scope, or storage semantics in any contract.
- **No secrets or real personal data** in contracts, examples, or fixtures.
- **Never weaken a gate to make it pass.** If a check fails, fix the change or
  report the milestone as blocked. Adding an unconditional ignore, lowering a
  threshold, or narrowing a scanner's scope to dodge a finding is prohibited by
  `HARNESS.md` section 7 and EP-05.
- **Released artifacts are immutable.** Corrections require a new version.

## Versioning

Semantic versioning, with contract-specific meaning defined in
`governance/VERSIONING.md`. An additive change is not automatically safe:
enum expansion and new response or event variants can break exhaustive
consumers and are classified `review_required`.

## Test fixtures

Negative fixtures that contain prohibited constructs live in
`tests/fixtures/negative/` with a neutralising `.fixture` suffix, outside the
release surface. See that directory's `README.md` before adding one. Never
place a prohibited construct under `contracts/`, `catalog/`, `compatibility/`,
or `templates/`.
