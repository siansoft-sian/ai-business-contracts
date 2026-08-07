# Contract Change Process

**Status:** skeleton at EP-01. EP-03 completes it alongside the compatibility
engine. `M0-CON-021` is not claimed until then.

## Contract-first

The contract changes before any implementation depends on the change. A
consumer repository never leads a contract change by shipping first.

## Stages

1. **Proposal** - what changes, why, and which consumers are affected.
2. **Owner review** - the single authoritative owner (`OWNERSHIP.md`,
   `CODEOWNERS`) reviews. Ownership is not shared.
3. **Compatibility check** - `scripts/check_compatibility.py` (EP-03) runs
   against the declared baseline and emits a machine-readable result with
   `compatible`, `breaking`, and `review_required` findings.
4. **Consumer impact** - listed explicitly from the catalog's `consumers`.
5. **Release** - versioned, immutable, checksummed (`RELEASES.md`).
6. **Deprecation** - if the change supersedes an existing contract
   (`DEPRECATION.md`).
7. **Retirement** - only after the deprecation window closes.

## Gate semantics

- A non-empty `breaking` list **fails** the gate unless the candidate is an
  approved major-version transition.
- `review_required` **blocks automatic approval** until the contract owner
  records a decision. Enum expansion and new response or event variants land
  here: they are additive but can break exhaustive consumers.
- An additive change is never assumed safe without this check.

## Emergency and security changes

An emergency change follows the same versioning and immutability rules. Speed
is obtained by shortening review latency, never by skipping the compatibility
gate or publishing a mutable artifact.

## To be completed in EP-03

- pull-request review requirements in full;
- the owner decision record format for `review_required`;
- major-version approval mechanics.
