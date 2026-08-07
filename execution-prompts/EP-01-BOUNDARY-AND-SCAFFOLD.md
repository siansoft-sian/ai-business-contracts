# EP-01 — Boundary Cleanup & Repository Scaffold

## Objective

Make repository ownership enforceable before adding contract content.

## Instructions

1. Remove or relocate prohibited implementation content identified in EP-00.
2. Create the canonical directory shape from `TARGET_REPOSITORY_TREE.md`.
3. Add README/CONTRIBUTING/SECURITY/CODEOWNERS and governance skeletons.
4. Add automated scanners for:
   - prohibited multi-tenant constructs in contract-bearing paths;
   - prohibited implementation code/imports/file families;
   - SQL/migration/PgBouncer implementation ownership violations.
5. Add mutation tests proving each scanner fails on an injected violation.
6. Ensure test-only negative fixtures are excluded from release artifacts.

## Required evidence

- repository tree;
- scanner commands/results;
- mutation-test results;
- list of removed/relocated legacy conflicts.

## Exit condition

M0-CON-001..005 and M0-CON-010 are technically enforceable, not merely documented.
