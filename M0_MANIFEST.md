# ai-business-contracts — M0 Execution Pack

**Milestone:** M0 — Platform Contract Foundation & Governance  
**Repository:** `ai-business-contracts`  
**Platform topology:** 8 independent repositories  
**Status of this pack:** Ready for execution; no acceptance item is pre-marked as passed.

## Pack contents

- `PROMPT.md` — authoritative implementation brief.
- `HARNESS.md` — execution rules and agent operating constraints.
- `ACCEPTANCE_CRITERIA.md` — measurable pass/fail contract for M0.
- `TEST_PLAN.md` — verification strategy mapped to acceptance criteria.
- `AUDITOR.md` — independent read-only audit prompt and verdict rules.
- `DELIVERY_REPORT.md` — final milestone delivery report template.
- `TARGET_REPOSITORY_TREE.md` — required M0 repository shape.
- `CONTRACT_STANDARD.md` — normative contract identifiers, formats, envelopes, catalog and lock conventions.
- `ARCHITECTURE_COMPLIANCE_MATRIX.md` — coverage of every frozen platform rule.
- `CROSS_REPO_COMPATIBILITY.md` — contracts-repo side of the platform compatibility gate.
- `execution-prompts/` — ordered prompts EP-00 through EP-06.
- `evidence/` — evidence report templates. These must be populated from real command output during execution.

## Frozen platform authority

The following architecture decisions are non-negotiable for this milestone:

1. `ai-business-contracts`
2. `ai-business-database`
3. `ai-business-auth`
4. `ai-business-api`
5. `ai-business-agent-runtime`
6. `ai-business-channel-gateway`
7. `ai-business-admin-web`
8. `ai-business-infrastructure`

The platform has **no multi-tenant architecture**. No production contract may define tenant identifiers, tenant headers, tenant contexts, tenant authorization scopes, tenant routing, or tenant storage semantics.

`ai-business-contracts` is the shared language between repositories. It owns versioned inter-repository interface contracts and their governance, but **never shared business implementation**.

## Milestone completion rule

This repository M0 passes only when:

- every criterion in `ACCEPTANCE_CRITERIA.md` is verified by evidence;
- the repository auditor returns `PASS`;
- the contracts-side compatibility artifact required by `CROSS_REPO_COMPATIBILITY.md` is produced; and
- no evidence is fabricated, inferred, or marked green without an executed check.

Platform M0 does **not** pass merely because this repository passes. Platform M0 additionally requires the other seven repository M0s and the platform cross-repository compatibility gate.
