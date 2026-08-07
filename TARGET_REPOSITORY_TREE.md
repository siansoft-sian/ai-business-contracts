# TARGET_REPOSITORY_TREE.md

This is the required M0-level repository shape. Equivalent naming is acceptable only when the same responsibilities and gates remain explicit.

```text
ai-business-contracts/
├── README.md
├── M0_MANIFEST.md
├── PROMPT.md
├── HARNESS.md
├── ACCEPTANCE_CRITERIA.md
├── TEST_PLAN.md
├── AUDITOR.md
├── DELIVERY_REPORT.md
├── CROSS_REPO_COMPATIBILITY.md
├── execution-prompts/
│   ├── EP-00-PREFLIGHT.md
│   ├── EP-01-BOUNDARY-AND-SCAFFOLD.md
│   ├── EP-02-CONTRACT-FOUNDATION.md
│   ├── EP-03-GOVERNANCE-AND-COMPATIBILITY.md
│   ├── EP-04-CONSUMER-PINNING-AND-PLATFORM-MATRIX.md
│   ├── EP-05-QUALITY-CI-AND-BUNDLE.md
│   └── EP-06-EVIDENCE-AUDIT-DELIVERY.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CODEOWNERS
├── pyproject.toml
├── .gitignore
├── .editorconfig
├── contracts/
│   ├── openapi/
│   │   └── .gitkeep
│   ├── asyncapi/
│   │   └── .gitkeep
│   ├── schemas/
│   │   ├── common/
│   │   │   ├── error-envelope.v1.schema.json
│   │   │   ├── request-metadata.v1.schema.json
│   │   │   └── contract-metadata.v1.schema.json
│   │   └── events/
│   │       └── event-envelope.v1.schema.json
│   └── examples/
│       ├── common/
│       └── events/
├── catalog/
│   └── contract-catalog.yaml
├── compatibility/
│   ├── policy.md
│   ├── platform-m0-matrix.yaml
│   └── fixtures/
│       ├── compatible/
│       └── breaking/
├── governance/
│   ├── CONTRACT_POLICY.md
│   ├── VERSIONING.md
│   ├── CHANGE_PROCESS.md
│   ├── DEPRECATION.md
│   ├── OWNERSHIP.md
│   └── RELEASES.md
├── templates/
│   └── consumer-contract-lock.yaml
├── scripts/
│   ├── validate_contracts.py
│   ├── validate_examples.py
│   ├── validate_catalog.py
│   ├── check_references.py
│   ├── check_compatibility.py
│   ├── check_no_multitenancy.py
│   ├── check_no_implementation_code.py
│   ├── build_bundle.py
│   ├── write_evidence_summary.py
│   └── quality_gate.sh
├── tests/
│   ├── test_schema_validity.py
│   ├── test_examples.py
│   ├── test_catalog.py
│   ├── test_references.py
│   ├── test_compatibility.py
│   ├── test_no_multitenancy.py
│   └── test_no_implementation_code.py
├── dist/                         # generated, normally git-ignored
│   └── .gitkeep
├── evidence/                     # generated M0 execution evidence
│   └── .gitkeep
└── .github/
    └── workflows/
        ├── ci.yml
        └── release.yml
```

## Notes

- `contracts/openapi/` and `contracts/asyncapi/` may be empty at M0 if no concrete service/event API is ready, but their validation pipeline must be ready and must validate any artifact added later.
- The four M0 foundation JSON Schemas are required because they prove cataloging, references, examples, versioning, and compatibility before business contracts arrive.
- No `src/app`, FastAPI, React, LangGraph, SQL, Terraform, provider adapter, or shared runtime package should appear in this repository.
- `dist/` contains reproducible release output, never hand-edited source.
