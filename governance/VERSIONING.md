# Versioning Policy

**Status:** skeleton at EP-01. EP-03 completes the normative detail and the
machine checks behind it. `M0-CON-020` is not claimed until then.

## Semantic versioning, with contract meaning

Every published contract carries a semantic version `MAJOR.MINOR.PATCH`.

| Bump | Meaning for a contract |
|---|---|
| `MAJOR` | incompatible contract change; consumers must act |
| `MINOR` | backward-compatible capability or addition |
| `PATCH` | clarification, metadata, or bug fix with no consumer-visible semantic change |

The initial M0 contract foundation release is `0.1.0`.

## Schema identity versus release version

The **major** generation is part of the schema identifier, because
incompatible generations may coexist:

```text
urn:ai-business:contracts:<family>:<name>:v<major>
<name>.v<major>.schema.json
```

The exact release SemVer lives in contract metadata, the catalog, and the
release manifest - not in the `$id`.

## Immutability

Released artifacts are immutable. A correction produces a new version; it never
edits a published release. See `RELEASES.md`.

## Consumer pinning

Production consumers pin a released version **and** an integrity hash. No
`main`, mutable branch, or floating range may be the sole production pin.

## To be completed in EP-03

- exact classification rules per change class;
- major-version transition approval;
- the relationship between catalog `compatibility` mode and permitted bumps.
