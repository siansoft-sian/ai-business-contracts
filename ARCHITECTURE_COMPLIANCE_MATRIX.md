# ARCHITECTURE_COMPLIANCE_MATRIX.md

This matrix proves that every frozen platform rule has a deliberate place in the `ai-business-contracts` M0 pack.

| Frozen rule | M0 treatment | Enforcement/reference |
|---|---|---|
| Exactly 8 repositories | Preserved verbatim | `PROMPT.md`, `CROSS_REPO_COMPATIBILITY.md`, catalog/matrix validation |
| Platform is not multi-tenant | No tenant semantics in published contracts | `PROMPT.md`, `HARNESS.md`, M0-CON-003, negative mutation test |
| Independent repo M0 packs | Contracts repo owns its complete pack | root M0 files + `execution-prompts/` + `evidence/` |
| Platform M0 requires all 8 M0s + compatibility gate | Contracts M0 is only one component | `M0_MANIFEST.md`, `CROSS_REPO_COMPATIBILITY.md` |
| Contracts repo is shared language only | Contract source/governance/tooling only | M0-CON-001/004, boundary scanner |
| API is business authority | Contracts describe interfaces, not business decisions | `PROMPT.md`, cross-repo matrix |
| LangGraph is runtime implementation detail | No LangGraph schema/internal graph objects in M0 contracts | boundary scanner + governance |
| Agent nodes never access business DB directly | No contract suggests/permits direct DB agent access | authority matrix; agent/runtime DB coupling rejected |
| Database repo owns PostgreSQL/Sqitch/stored functions/roles/PgBouncer/DB contracts/migrations | Kept outside contracts repo | M0-CON-005, `PROMPT.md` |
| FastAPI runtime uses asyncpg pool through PgBouncer | Recorded as frozen DB/API boundary, not implemented here | `PROMPT.md`, cross-repo authority notes |
| Migrations bypass PgBouncer and connect directly to PostgreSQL | Recorded as frozen database rule | `PROMPT.md`, cross-repo authority notes |
| Authentication separate from authorization | Auth = `ai-business-auth`; business authz = `ai-business-api` | `PROMPT.md`, matrix validation |
| Channel gateway owns verification/normalization/dedup/delivery | No channel adapter implementation here | authority map + boundary scan |
| Admin web never accesses DB/PgBouncer/LangGraph | Contracts-only consumption model | matrix validation |
| Infrastructure owns IaC/central OTel/Prometheus/Grafana/env | No deployment resources here | authority map + boundary scan |
| Service instrumentation stays in services | No runtime observability initialization here | boundary scan |
| No implementation imports between repos | Versioned release bundle + lock/hash pinning | M0-CON-023/036/041/042 |
