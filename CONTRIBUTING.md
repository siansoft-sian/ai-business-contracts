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

```bash
uv venv && uv pip install pytest ruff mypy
uv run pytest
python3 scripts/check_no_multitenancy.py
python3 scripts/check_no_implementation_code.py
```

From EP-05 a single `scripts/quality_gate.sh` runs every blocking check, and
CI calls the same scripts rather than a divergent reimplementation.

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
