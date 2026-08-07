# Deprecation & Retirement Policy

**Status:** complete. Supports `M0-CON-021`.

## Lifecycle states

A contract is in exactly one state. The catalog records it and
`scripts/validate_catalog.py` validates it.

```text
draft ──▶ active ──▶ deprecated ──▶ retired
```

| State | Meaning | May a consumer depend on it? |
|---|---|---|
| `draft` | not yet consumable; shape may change without ceremony | no |
| `active` | published and supported | yes |
| `deprecated` | still supported, replacement announced | yes, but migration has started |
| `retired` | no longer supported | no |

The progression is one-directional. A retired contract is not revived; a
replacement is published under a new identifier.

## Deprecation

Deprecating announces intent to remove. It does not remove anything: a
deprecated contract keeps working for its published consumers for the whole
window.

Entering `deprecated` requires metadata, and the catalog validator rejects the
state without it:

```yaml
lifecycle: deprecated
deprecation:
  deprecated_at: 2026-08-01
  replaced_by: urn:ai-business:contracts:common:example:v2
  earliest_retirement: 2027-02-01
```

`replaced_by` is omitted only when the capability is withdrawn entirely rather
than superseded. That is a stronger statement than a replacement and should be
rare.

The same validator rejects deprecation metadata on an `active` contract: an
active contract with a deprecation date is a contradiction, and silently
tolerating it would let a half-finished deprecation look complete.

## The deprecation window

**Minimum six months** between `deprecated_at` and `earliest_retirement`, so a
consumer on an ordinary release cadence can migrate without an emergency.

The window may be shortened only for a security withdrawal, and only with the
owner's recorded decision naming every affected consumer and the reason
migration cannot wait.

## Retirement preconditions

All of these must hold before a contract moves to `retired`:

1. the deprecation window has elapsed;
2. `earliest_retirement` has passed;
3. no consumer listed in the catalog still depends on the version;
4. the replacement, if any, is `active`;
5. the owner has recorded the retirement decision.

Condition 3 is the substantive one. The catalog's `consumers` list is what
makes it checkable rather than a matter of belief, which is why an empty
consumer list must mean "genuinely nothing consumes this" and not "we did not
look".

## Retirement is a breaking change

Removing a contract from the supported set is breaking, and gets the full
`MAJOR` treatment from `VERSIONING.md`. The compatibility engine reports it as
`contract-removed`, which fails the gate unless the transition is declared.

## Immutability still applies

Deprecating or retiring never edits an already-published release artifact. The
lifecycle change is expressed in a new release of the catalog. The old release
keeps saying what it always said, which is what makes a pinned consumer's view
stable.
