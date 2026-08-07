# Contract Policy

**Status:** complete. The foundation primitives are defined in
`contracts/schemas/`, registered in `catalog/contract-catalog.yaml`, and
governed by `VERSIONING.md`, `CHANGE_PROCESS.md`, `DEPRECATION.md`, and
`RELEASES.md`.

## What is a contract

A contract is a machine-validatable interface definition that more than one
repository depends on. Prose alone is not a contract.

| Family | Format |
|---|---|
| reusable data contracts | JSON Schema Draft 2020-12 |
| HTTP interfaces | OpenAPI 3.1.x |
| event/message interfaces | AsyncAPI 3.x |
| catalog and compatibility metadata | YAML or JSON, validated by a JSON Schema |

## Every contract has

- a stable `contract_id`, unchanged across compatible versions;
- a semantic `version`;
- a `type`;
- a lifecycle state;
- exactly one owner;
- zero or more explicit consumers;
- a canonical source path;
- a compatibility mode;
- a source checksum in built manifests.

## Design rules

- Prefer explicit schemas over prose-only contracts.
- Every schema reference resolves from a clean checkout.
- Examples are executable validation fixtures, not decorative samples.
- Error codes are stable identifiers; messages are client-safe but are not
  compatibility keys.
- Date and time fields use explicit RFC-3339 semantics with stated timezone
  rules.
- Identifiers declare format and constraints rather than relying on
  undocumented convention.
- The unknown/additional-fields policy is explicit per schema.
- Contracts describe externally observable interfaces, never internal
  implementation.

## Prohibited content

Contracts must never contain secrets, credentials, bearer tokens, connection
strings, or realistic personal data. They must never expose SQL function
bodies, connection-pool objects, JWT verifier internals, policy-engine
implementation, agent graph state, channel SDK objects, frontend component
models, or infrastructure resources.

The platform is **not multi-tenant**: no contract defines a tenant identifier,
tenant header, tenant context, tenant-scoped authorization, tenant routing, or
tenant-scoped storage.

Both prohibitions are machine-enforced on the release surface - see
`OWNERSHIP.md`, "Enforcement".

## Where the rules live

| Question | Document |
|---|---|
| What version does this change require? | `VERSIONING.md` |
| How does a change get reviewed and released? | `CHANGE_PROCESS.md` |
| How is a contract withdrawn? | `DEPRECATION.md` |
| What does a release contain, and what is immutable? | `RELEASES.md` |
| Who owns and consumes each contract? | `OWNERSHIP.md`, `catalog/contract-catalog.yaml` |
| How is a change classified? | `compatibility/policy.md` |
