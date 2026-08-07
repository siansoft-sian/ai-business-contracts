# Test-only negative fixtures

Every file here contains a construct the repository's boundary scanners must
reject. They exist to prove the gates **fail** when a violation is injected —
`TEST_PLAN.md` Layer A requires exactly that, and EP-00 recorded that
observing the absence of violations is not the same as detecting one.

## Why the `.fixture` suffix

Each file is named `<real-name>.fixture`. The suffix is load-bearing:

- `migration.sql.fixture` is **not** a `.sql` file, so the repository-wide
  file-family scan in `scripts/check_no_implementation_code.py` does not match
  it, and **no scanner exception or ignore-list is required**. EP-00 §1.3
  established that ignore-lists are how these gates rot.
- Tests rename each fixture to its real name at injection time, so the real
  extension and the real content are still exercised against the real scanner.

## Release exclusion

`tests/` lies outside the release surface (`_scope.CONTRACT_BEARING_PATHS`) by
construction, so these fixtures can never be scanned as contract source and
never enter a release bundle. `tests/test_no_multitenancy.py` asserts both
properties. EP-05 validates the bundle-level exclusion.

**Do not move these files into `contracts/`, `catalog/`, `compatibility/`, or
`templates/`.** That is what the mutation tests do, temporarily and under
`try`/`finally`.
