# Evidence Index

All evidence files are templates until commands are actually executed in the target repository.

| File | Purpose | Initial status |
|---|---|---|
| `01-preflight.md` | starting repository state and conflict inventory | NOT RUN |
| `02-boundary.md` | no-implementation/no-multitenancy enforcement | NOT RUN |
| `03-contract-validation.md` | schemas, examples, refs, catalog | NOT RUN |
| `04-compatibility.md` | compatible/breaking/review-required fixtures | NOT RUN |
| `05-quality-security.md` | local gate, CI, security/dependency scans | NOT RUN |
| `06-release-artifacts.md` | bundle/manifest/checksums/reproducibility | NOT RUN |
| `07-cross-repo-readiness.md` | platform matrix and consumer pinning | NOT RUN |
| `08-audit-verdict.md` | independent M0 audit | NOT RUN |

**Rule:** templates are not evidence. Replace placeholders only with real outputs from the target commit.
