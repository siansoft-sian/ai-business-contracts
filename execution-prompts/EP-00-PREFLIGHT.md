# EP-00 — Preflight & Conflict Inventory

## Objective

Establish the exact starting state before modifying `ai-business-contracts`.

## Instructions

1. Record repository URL/name, branch, commit SHA, and working-tree status.
2. Inventory all files and dependencies.
3. Search for:
   - multi-tenant constructs;
   - implementation code that belongs to another repo;
   - SQL/migrations/database drivers/PgBouncer config;
   - auth/JWT/Casbin implementation;
   - LangGraph implementation;
   - channel adapters/webhook handlers;
   - React/frontend source;
   - deployment/IaC;
   - existing contract schemas, versioning policy, release metadata, CI, tests.
4. Classify each conflict as `remove`, `migrate-to-owner-repo`, `replace`, or `retain`.
5. Do not delete evidence of the initial state before recording it.

## Required output

Populate `evidence/01-preflight.md` with actual commands and findings.

## Exit condition

A complete inventory exists and there is no unresolved ambiguity about what belongs in this repo for M0.
