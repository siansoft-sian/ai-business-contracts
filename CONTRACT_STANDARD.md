# CONTRACT_STANDARD.md

## Purpose

Freeze the minimum contract conventions used by `ai-business-contracts` M0 so execution does not depend on ad-hoc naming or per-file interpretation.

## 1. Canonical formats

- Reusable data contracts: **JSON Schema Draft 2020-12**.
- HTTP interface contracts: **OpenAPI 3.1.x** when concrete HTTP contracts are introduced.
- Event/message interface contracts: **AsyncAPI 3.x** when concrete asynchronous interfaces are introduced.
- Catalog/compatibility metadata: YAML or JSON, with a JSON Schema used to validate the structure.

M0 requires the validation pipeline for all three contract families, but only the four foundation JSON Schemas are mandatory contract content at M0.

## 2. Contract identity

Each contract has:

- stable `contract_id` across compatible versions;
- semantic `version` (`MAJOR.MINOR.PATCH`);
- `type`;
- lifecycle state;
- exactly one owner;
- zero or more explicit consumers;
- canonical source path;
- compatibility mode;
- source checksum in built manifests.

Recommended JSON Schema `$id` form:

```text
urn:ai-business:contracts:<family>:<name>:v<major>
```

Example:

```text
urn:ai-business:contracts:common:error-envelope:v1
```

The major version is part of the schema identifier because incompatible generations may coexist. The exact release SemVer lives in contract metadata/catalog/release manifest.

## 3. File naming

```text
<name>.v<major>.schema.json
```

Examples:

```text
error-envelope.v1.schema.json
request-metadata.v1.schema.json
event-envelope.v1.schema.json
```

Do not overwrite a released major-generation source in an old release artifact. New releases are immutable snapshots.

## 4. Foundation error envelope

Minimum semantic shape:

```json
{
  "success": false,
  "error": {
    "code": "MACHINE_STABLE_CODE",
    "message": "Safe client-facing message",
    "details": {}
  },
  "request_id": "req_...",
  "correlation_id": "corr_..."
}
```

Rules:

- `error.code` is compatibility-sensitive.
- `error.message` is human-readable and is not the stable compatibility key.
- internal stack traces/provider errors/secrets never belong in the contract.
- `details` must be structured and safe to expose.
- request/correlation IDs are observability identifiers, not authorization inputs.

## 5. Request/correlation metadata

The common metadata contract may include:

- `request_id`;
- `correlation_id`;
- W3C `traceparent` / `tracestate` when propagated at an interface.

It must not contain bearer tokens, cookies, secrets, raw auth claims, personal data, or prohibited multi-tenant context.

## 6. Event envelope

Minimum semantics:

```json
{
  "event_id": "evt_...",
  "event_type": "business.entity.changed",
  "contract_id": "urn:ai-business:contracts:events:...:v1",
  "contract_version": "1.0.0",
  "producer": "ai-business-api",
  "occurred_at": "2026-08-07T10:00:00Z",
  "request_id": "req_...",
  "correlation_id": "corr_...",
  "payload": {}
}
```

Rules:

- `event_id` identifies the event occurrence, not the aggregate/business object.
- `event_type` is stable and version-governed.
- producer must be one of the frozen repository/service identifiers approved by governance.
- event-specific payload schemas extend/reference the envelope rather than embedding implementation details.
- direct database connection information, internal LangGraph state, auth secrets, and channel-provider secrets are forbidden.

## 7. Catalog structure

Each catalog entry must be equivalent to:

```yaml
contract_id: urn:ai-business:contracts:common:error-envelope:v1
version: 0.1.0
type: json-schema
lifecycle: active
owner: ai-business-contracts
consumers:
  - ai-business-api
  - ai-business-auth
source: contracts/schemas/common/error-envelope.v1.schema.json
compatibility: backward
```

The catalog schema must restrict repository names to the frozen eight-repository set.

## 8. Compatibility result schema

The compatibility tool must emit a machine-readable document equivalent to:

```json
{
  "baseline": "<ref-or-version>",
  "candidate": "<ref-or-version>",
  "result": "pass",
  "breaking": [],
  "review_required": [],
  "compatible": [],
  "checked_at_utc": "<timestamp>"
}
```

A non-empty `breaking` list fails the gate unless the candidate is an approved major-version transition. `review_required` blocks automatic approval until the designated contract owner records a decision.

## 9. Consumer lock standard

Minimum semantics:

```yaml
dependencies:
  ai-business-contracts:
    version: 0.1.0
    source: release
    manifest_sha256: <sha256>
    bundle_sha256: <sha256>
```

Consumers validate the lock in CI. The lock is not a runtime import mechanism.

## 10. Prohibited coupling

Shared contracts must never expose or require:

- SQL function bodies or migrations;
- PgBouncer internals/credentials;
- asyncpg pool objects;
- JWT verifier implementation;
- Casbin model/policy implementation;
- LangGraph node/state implementation;
- channel-provider SDK objects;
- React component models;
- Terraform/Kubernetes implementation resources.

A contract may represent an externally observable capability or message exchanged with the owning service, but not its internal implementation.
