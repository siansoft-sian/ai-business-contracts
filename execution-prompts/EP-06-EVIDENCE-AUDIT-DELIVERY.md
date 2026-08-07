# EP-06 — Evidence, Independent Audit & Delivery

## Objective

Close M0 with verifiable evidence rather than implementation claims.

## Instructions

1. Run the full quality gate against the exact delivery commit.
2. Record UTC timestamp, commit SHA, commands, exit codes, and relevant output.
3. Build and hash release artifacts.
4. Populate every evidence report under `evidence/`.
5. Run `AUDITOR.md` in a read-only independent pass.
6. Resolve findings by creating a new implementation iteration, then re-run the full audit; never edit the auditor verdict to force a pass.
7. Complete `DELIVERY_REPORT.md` strictly from evidence.
8. If any blocking criterion is failed or not run, final result is `FAIL`.

## Exit condition

`AUDITOR.md` returns PASS, all M0 criteria pass, and the final delivery report references complete evidence for the tested commit.
