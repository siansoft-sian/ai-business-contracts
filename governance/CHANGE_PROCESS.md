# Contract Change Process

**Status:** complete. Supports `M0-CON-021`.

## Contract-first

The contract changes before any implementation depends on the change. A
consumer repository never leads a contract change by shipping first, because
then the contract is documenting an accident rather than governing an
interface.

## The seven stages

### 1. Proposal

Open a pull request describing what changes, why, and which consumers are
affected. The affected consumers come from the catalog's `consumers` list, so
this is a lookup rather than a guess.

### 2. Owner review

The single authoritative owner (`OWNERSHIP.md`, enforced by `CODEOWNERS`)
reviews. Ownership is not shared and not delegated per-change.

### 3. Compatibility check

`scripts/check_compatibility.py` runs against the declared baseline and emits
the result document defined by
`urn:ai-business:contracts:common:compatibility-result:v1`.

| Verdict | Meaning | Effect |
|---|---|---|
| `pass` | no breaking finding, or every one is covered by a declared `MAJOR` bump | may merge |
| `review_required` | nothing proven breaking, but something cannot be shown safe | **blocks automatic approval** until the owner records a decision |
| `fail` | at least one unapproved breaking finding | blocked |
| `no-baseline` | no prior release exists; nothing was compared | may merge, but confers no compatibility guarantee |

### 4. Consumer impact

For a `MAJOR` change, every consumer in the catalog is notified before release,
with the replacement contract identified.

### 5. Release

Versioned, immutable, checksummed. See `RELEASES.md`.

### 6. Deprecation

If the change supersedes an existing contract, the old one moves to
`deprecated` with metadata naming the replacement. See `DEPRECATION.md`.

### 7. Retirement

Only after the deprecation window closes and no listed consumer still depends
on the version. See `DEPRECATION.md`.

## The owner decision record for `review_required`

`review_required` exists because additive changes are not automatically safe.
Enum expansion and new variants break a consumer that matches exhaustively, and
a rewritten regex cannot be proven safe in general.

Resolving one requires the owner to state, in the pull request, a decision in
this form:

```text
Compatibility decision
  finding:  <change class> at <location> in <contract_id>
  decision: accept | reject
  basis:    which consumers were checked, and what makes the change safe for them
  reviewer: <owner>
```

"No consumer matches exhaustively" is a claim about specific consumers and must
name them. An empty or generic basis is not a decision.

## Major-version approval

An incompatible change to a published contract requires:

1. a `MAJOR` bump on that contract, producing a new `$id` and a new file;
2. the previous generation kept until its deprecation window closes;
3. the breaking findings **listed** in the compatibility result, not suppressed.

The engine reports `approved_major_transition: true` only when every breaking
finding is covered by a `MAJOR` increase. The findings still appear in the
result: an approved break is declared, not hidden.

## Emergency and security changes

An emergency change follows the same versioning and immutability rules. Speed
comes from shortening review latency, never from skipping the compatibility
gate, publishing a mutable artifact, or merging with an unresolved
`review_required`.

If a published contract must change because it leaks something unsafe, the
correction is a new version and the unsafe version is deprecated immediately
with an accelerated retirement. The released artifact is still not edited.

## What may never be done

- weaken, narrow, or add an unconditional ignore to a gate so a change passes;
- resolve `review_required` by re-running until it disappears;
- edit a released artifact;
- merge a `fail` verdict without the `MAJOR` treatment.

`HARNESS.md` section 7 and EP-05 both forbid obtaining a green result by
lowering the bar. A gate that cannot fail is not a gate.
