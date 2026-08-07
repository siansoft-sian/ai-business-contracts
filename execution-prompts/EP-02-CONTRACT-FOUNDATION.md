# EP-02 — Foundation Contract Model

## Objective

Create the minimum machine-readable contract primitives and catalog necessary to prove the contract platform.

## Instructions

Implement versioned schemas for:

1. error envelope;
2. request/correlation metadata;
3. event envelope;
4. contract metadata/catalog entry.

For each:

- use an explicit JSON Schema dialect;
- assign stable `$id` and version metadata;
- define additional-properties behavior intentionally;
- use synthetic examples;
- add passing and failing fixtures;
- keep business logic and implementation technology out of primitives;
- ensure no prohibited multi-tenant field/context/header exists.

Create `catalog/contract-catalog.yaml` and register every M0 primitive with one owner, explicit consumers, lifecycle state, source path, and compatibility mode.

## Exit condition

All schemas, examples, references, and catalog entries validate from a clean checkout.
