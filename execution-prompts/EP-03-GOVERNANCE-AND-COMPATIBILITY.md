# EP-03 — Governance, Versioning & Compatibility Engine

## Objective

Turn contract changes into a controlled, reviewable compatibility process.

## Instructions

1. Complete governance docs for versioning, ownership, change workflow, deprecation, retirement, and immutable releases.
2. Implement `check_compatibility` with machine-readable output.
3. Add fixtures for every mandatory compatible/breaking/review-required case in `TEST_PLAN.md`.
4. Require major-version/change approval for incompatible published changes.
5. Treat enum expansion/new variants as `review_required` when exhaustive consumers may break.
6. Reject unresolved references and duplicate `(contract_id, version)`.
7. Define initial release baseline behavior: if no prior release exists, prove the checker using curated fixtures and mark the first published baseline explicitly.

## Exit condition

Compatibility behavior is deterministic, tested, and produces structured results usable by CI and the platform gate.
