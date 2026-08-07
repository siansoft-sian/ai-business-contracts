# Compatibility Policy

**Status:** skeleton at EP-01. EP-03 implements the checker, the fixtures, and
the normative rules. `M0-CON-024` through `M0-CON-029` are not claimed until
then.

## Baseline

The checker compares a candidate against a declared baseline release or ref.
Where no prior release exists, curated fixtures under `fixtures/` prove the
engine before the first publication.

## Result document

The checker emits a machine-readable result:

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

A non-empty `breaking` list fails the gate unless the candidate is an approved
major-version transition. `review_required` blocks automatic approval until the
contract owner records a decision.

## Classification

**Breaking** unless proven otherwise: removing or renaming a published
operation, message, schema, field, or required response; an incompatible type
change; a newly required input without a compatible transition; narrowing an
allowed value set; changed identifier semantics; changed error-code semantics
relied on by consumers; making an extensible payload closed in a way that
rejects previously valid data.

**Compatible:** adding an optional property; adding optional response metadata
a client may ignore; documentation-only change; adding a new independent
contract id.

**Review required:** an additive change is not automatically safe. Enum
expansion and new response or event variants can break consumers that match
exhaustively, so they are surfaced for an explicit owner decision rather than
auto-approved.

## Fixtures

```text
fixtures/compatible/    known-safe changes
fixtures/breaking/      known-breaking changes, one per mandatory class
```

Each mandatory class in `TEST_PLAN.md` Layer D gets a fixture, so the engine is
proven in both directions rather than asserted.
