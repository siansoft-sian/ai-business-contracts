# Compatibility Policy

How a change to a published contract is classified, and what each class means.
The engine is `scripts/check_compatibility.py`; this document is the rule it
implements.

## The three classes

Every difference between a baseline and a candidate lands in exactly one class.
The boundary between them is drawn by **what can be proven**, not by what feels
safe.

| Class | Meaning | Effect on the gate |
|---|---|---|
| `breaking` | demonstrated to reject data or usage the baseline accepted | fails, unless covered by a declared major-version transition |
| `review_required` | cannot be shown safe | blocks automatic approval until the owner records a decision |
| `compatible` | proven not to affect existing consumers | passes |

The asymmetry is deliberate. A change is never called compatible because
nothing disproved it; it is called compatible only when the structure shows it
harmless. Everything else is escalated rather than waved through.

## Breaking

Decidable from structure, so reported without hedging:

| Change | Why it breaks |
|---|---|
| `contract-removed` | every consumer of it breaks |
| `field-removed` | consumers reading the field break |
| `field-renamed` | a rename is a removal to every existing consumer |
| `type-changed` | data written for the baseline is rejected |
| `field-added-required` | documents written for the baseline omit it |
| `optional-became-required` | documents that omitted it are rejected |
| `enum-value-removed` | data carrying the removed value is rejected |
| `range-narrowed` | values inside the old bounds are rejected |
| `extensible-became-closed` | documents carrying tolerated extra fields are rejected |
| `unresolvable-reference` | the candidate cannot be interpreted from a clean checkout |
| `duplicate-contract-version` | a version must identify exactly one artifact |
| `released-version-content-changed` | released artifacts are immutable |

## Review required

An additive change is **not** automatically safe.

- **`enum-value-added`** — a consumer matching the field exhaustively has no
  branch for the new value. Additive on the wire, breaking in the consumer.
- **new response or event variant** — same reasoning; a consumer switching over
  a closed set of variants meets one it cannot handle.
- **`pattern-changed` with no counter-example** — see below.

These do not fail the gate. They stop automatic approval until the owner
records a decision naming the consumers checked. See
`governance/CHANGE_PROCESS.md`.

## Deciding an undecidable change

Regular-expression strictness cannot be decided in general: there is no
mechanical way to ask whether one pattern accepts everything another does.

Rather than guess, the engine looks for a **witness**. It tests the values the
baseline itself declares valid — its `examples` — against the candidate
pattern:

- a declared-valid value the candidate rejects **proves** the tightening. The
  finding is `breaking` and carries the failing value as `witness`;
- no such value means the change cannot be shown safe, so it is
  `review_required`. Never `compatible`.

This makes every breaking verdict on a pattern a demonstration rather than an
opinion, and it means a genuine loosening is not misclassified as a break.

Numeric and length bounds are decidable, so narrowing them is reported as
`range-narrowed` without needing a witness.

## Major-version transitions

A breaking change is permitted when it is **declared**: every breaking finding
must be covered by a major-version increase on its contract. The engine then
reports `approved_major_transition: true` and the verdict is `pass`.

The findings remain listed. An approved break is declared, not hidden, and a
reader of the result document can always see what changed.

## Baseline

`baseline.yaml` declares the release a candidate is compared against.

No release has been published yet, so there is nothing to compare and the
engine reports `no-baseline` — not `pass`. A pass would read as "compared and
found compatible", which would be false, and a gate that reports success when
it did not run is worse than one that reports nothing.

The engine is proven meanwhile by the curated pairs under `fixtures/`, which
cover every mandatory case in both directions:

```text
fixtures/compatible/        changes proven harmless
fixtures/breaking/          changes proven to break, one per mandatory class
fixtures/review-required/   changes that cannot be shown safe
```

Each fixture is a `baseline/` and `candidate/` pair with a `README.md` stating
what it demonstrates and the class expected. `tests/test_compatibility.py`
asserts the class for each, and fails if a mandatory case loses its fixture.

## Result document

The engine emits the document defined by
`urn:ai-business:contracts:common:compatibility-result:v1`, published in a
release as `compatibility-summary.json`. Because the shape is itself a
governed contract, a reader validates what it consumes rather than trusting the
producer.

## Not yet covered

Operation and message removal for HTTP and event-interface artifacts is not
exercised, because `contracts/openapi/` and `contracts/asyncapi/` hold no
artifacts yet. `TEST_PLAN.md` gates that case on those directories being
non-empty. Fixtures must be added with the first such contract, and this
document updated, before it can be considered covered.
