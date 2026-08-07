# EP-05 — Quality Gate, CI, Security & Release Bundle

## Objective

Make M0 reproducible and releaseable.

## Instructions

1. Implement a single local `scripts/quality_gate.sh` entry point.
2. Make CI call the same scripts/checks, not a divergent reimplementation.
3. Include lint, format, static typing, tests, schema/reference/example/catalog validation, compatibility, boundary scans, multi-tenant scan, secret scan, and dependency vulnerability audit.
4. Implement deterministic bundle/manifest generation.
5. Generate:
   - contract bundle;
   - manifest;
   - SHA256 checksums;
   - compatibility summary;
   - machine-readable M0 evidence summary.
6. Validate release exclusions: no secrets, caches, virtualenv, unrelated implementation, or test-only negative fixtures.
7. Do not make a red gate green by lowering thresholds or adding unconditional ignores.

## Exit condition

A clean checkout can run the gate and reproduce validated release artifacts.
