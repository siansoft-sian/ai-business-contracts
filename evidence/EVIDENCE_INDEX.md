# Evidence Index

All evidence files are templates until commands are actually executed in the target repository.

| File | Purpose | Current status |
|---|---|---|
| `01-preflight.md` | starting repository state and conflict inventory | COMPLETE (inventory) — Run 1 @ `m0-ep00-baseline`, Run 2 @ `a29b4be`, Run 3 @ `f15a44c` |
| `02-boundary.md` | no-implementation/no-multitenancy enforcement | NOT RUN |
| `03-contract-validation.md` | schemas, examples, refs, catalog | NOT RUN |
| `04-compatibility.md` | compatible/breaking/review-required fixtures | NOT RUN |
| `05-quality-security.md` | local gate, CI, security/dependency scans | NOT RUN |
| `06-release-artifacts.md` | bundle/manifest/checksums/reproducibility | NOT RUN |
| `07-cross-repo-readiness.md` | platform matrix and consumer pinning | NOT RUN |
| `08-audit-verdict.md` | independent M0 audit | NOT RUN |

**Rule:** templates are not evidence. Replace placeholders only with real outputs from the target commit.

**Rule (added at EP-00 Run 3):** *committed* evidence is the only durable evidence. `01-preflight.md` was found reverted in the working tree to its `NOT RUN` template, losing the Run 1 and Run 2 record from the checkout; it was recoverable only because prior runs had been committed. Commit each evidence file as it is produced, and audit against committed blobs rather than the working tree. See `01-preflight.md` §D.1 and finding 9.
