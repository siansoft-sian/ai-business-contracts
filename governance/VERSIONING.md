# Versioning Policy

**Status:** complete. Supports `M0-CON-020`.

## Semantic versioning, with contract meaning

Every published contract carries `MAJOR.MINOR.PATCH`. The bump is decided by
what the change does to an existing consumer, never by how large the diff is.

| Bump | Meaning | The consumer test |
|---|---|---|
| `MAJOR` | incompatible change | data or usage the old contract accepted is now rejected |
| `MINOR` | backward-compatible capability or addition | old consumers keep working untouched |
| `PATCH` | clarification, metadata, or documentation | nothing consumer-visible moved at all |

The initial M0 contract foundation release is `0.1.0`.

## Change class to required bump

`scripts/check_compatibility.py` classifies a change; this table says what
version that classification demands. The two are meant to be read together: the
tool decides the class, the policy decides the bump.

| Change class | Class | Required bump |
|---|---|---|
| `contract-removed` | breaking | `MAJOR` |
| `field-removed`, `field-renamed` | breaking | `MAJOR` |
| `type-changed` (narrowing) | breaking | `MAJOR` |
| `optional-became-required`, `field-added-required` | breaking | `MAJOR` |
| `enum-value-removed` | breaking | `MAJOR` |
| `range-narrowed` | breaking | `MAJOR` |
| `pattern-changed` with a witness | breaking | `MAJOR` |
| `extensible-became-closed` | breaking | `MAJOR` |
| `enum-value-added` | review required | `MINOR` after owner decision |
| `pattern-changed` without a witness | review required | `MINOR` after owner decision |
| `field-added-optional` | compatible | `MINOR` |
| `contract-added` | compatible | `MINOR` |
| `type-changed` (widening, e.g. integer to number) | compatible | `MINOR` |
| `documentation-only` | compatible | `PATCH` |

`released-version-content-changed` and `duplicate-contract-version` are not
change classes to be versioned. They are defects: see `RELEASES.md`.

## Schema identity versus release version

The **major** generation lives in the schema identifier, because incompatible
generations coexist:

```text
urn:ai-business:contracts:<family>:<name>:v<major>
<name>.v<major>.schema.json
```

The exact release SemVer lives in `x-contract-version`, the catalog, and the
release manifest. A `MAJOR` bump therefore produces a **new file and a new
`$id`**, not an edit to the existing one. That is what allows a consumer on v1
and a consumer on v2 to be correct at the same time.

## Zero-major versions

While a contract is below `1.0.0` the compatibility rules still apply as
written. `0.x` is not a licence to break consumers silently: a breaking change
at `0.x` still requires the `MAJOR` treatment above and still fails the gate
without it. The only difference is that `0.x` signals the contract is young.

## Immutability

A released version is immutable. A correction produces a new version; it never
edits a published one. The compatibility engine enforces this directly: the
same `(contract_id, version)` with different content is reported as
`released-version-content-changed` and fails the gate.

## Consumer pinning

Production consumers pin a released version **and** an integrity hash. No
`main`, mutable branch, or floating range may be the sole production pin. See
`RELEASES.md`.
