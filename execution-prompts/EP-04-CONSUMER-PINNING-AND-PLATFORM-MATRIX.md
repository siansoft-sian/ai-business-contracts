# EP-04 — Consumer Pinning & Cross-Repository Matrix

## Objective

Prepare `ai-business-contracts` for safe consumption by the other repositories without implementation imports.

## Instructions

1. Create the language-neutral consumer lock template with exact version + integrity metadata.
2. Create `compatibility/platform-m0-matrix.yaml` listing all eight repositories exactly once.
3. Encode frozen authority notes, especially:
   - business authority = `ai-business-api`;
   - authentication = `ai-business-auth`;
   - DB/stored-function contracts = `ai-business-database`;
   - LangGraph implementation = `ai-business-agent-runtime` only;
   - channel adapters = `ai-business-channel-gateway`;
   - admin web has no direct DB/PgBouncer/LangGraph access;
   - central observability infrastructure = `ai-business-infrastructure`.
4. Add negative tests for version mismatch, checksum mismatch, unknown required contract ID, and incorrect authority declaration.
5. Do not add consumer runtime SDKs.

## Exit condition

The contracts repository can provide deterministic inputs to the future platform M0 compatibility gate.
