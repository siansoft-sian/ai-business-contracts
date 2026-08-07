#!/usr/bin/env bash
#
# The single local entry point for every blocking repository validation.
#
# Design notes worth knowing before editing:
#
#   1. EVERY CHECK RUNS. The gate does not stop at the first failure. A gate
#      that aborts early makes fixing a red build an N-round guessing game, and
#      the evidence summary needs every exit code, not the first non-zero one.
#      The aggregate exit code is still the contract: 0 only if all passed.
#
#   2. CI CALLS THIS FILE. .github/workflows/ci.yml runs this script rather
#      than restating the checks, so CI and local runs cannot drift.
#      tests/test_quality_gate.py enforces that.
#
#   3. NO SILENT REDUCTION. --skip-release omits the release stage for local
#      iteration, but the omission is recorded in the evidence summary and
#      every criterion depending on a skipped check is reported not_run.
#      There is no flag that makes a failing check pass.
#
#   4. THE RELEASE STAGE REQUIRES A COMMITTED TREE. A manifest names a commit
#      SHA, so building from uncommitted edits would pin content that commit
#      does not contain. Use --skip-release while iterating.
#
# Usage:
#   scripts/quality_gate.sh [--skip-release]
#
# Exit codes:
#   0 - every executed check passed
#   1 - at least one check failed

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

DIST="$ROOT/dist"
RECORD="$DIST/gate-checks.tsv"
SKIP_RELEASE=0
SKIPPED=""

for arg in "$@"; do
  case "$arg" in
    --skip-release) SKIP_RELEASE=1 ;;
    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'quality_gate: unknown argument %s\n' "$arg" >&2; exit 2 ;;
  esac
done

mkdir -p "$DIST"
: > "$RECORD"

FAILED=0
declare -a SUMMARY_LINES=()

# run <name> <command...>
#
# Executes a check, streams its output, and appends one tab-separated record.
# The recorded command is the argv actually executed, so the evidence summary
# quotes a command a reader can re-run rather than a description of one.
run() {
  local name="$1"; shift
  # printf %q re-quotes each argument, so a recorded command with a pipeline or
  # an embedded space can be pasted back into a shell and run. Joining with a
  # plain "$*" would record something that looks runnable but is not.
  local command
  command="$(printf '%q ' "$@")"
  command="${command% }"
  printf '\n\033[1m==> %s\033[0m\n    %s\n' "$name" "$command"
  "$@"
  local code=$?
  printf '%s\t%s\t%s\n' "$name" "$code" "$command" >> "$RECORD"
  if [ "$code" -ne 0 ]; then
    FAILED=1
    SUMMARY_LINES+=("FAIL  $name (exit $code)")
  else
    SUMMARY_LINES+=("pass  $name")
  fi
  return 0
}

PY="uv run python"

# --- Stage 1: tooling quality -------------------------------------------
run ruff_format uv run ruff format --check .
run ruff_lint   uv run ruff check .
run mypy        uv run mypy

# --- Stage 2: tests ------------------------------------------------------
run pytest      uv run pytest -q

# --- Stage 3: contract validation ---------------------------------------
run validate_contracts $PY scripts/validate_contracts.py
run check_references   $PY scripts/check_references.py
run validate_examples  $PY scripts/validate_examples.py
run validate_catalog   $PY scripts/validate_catalog.py
run validate_matrix    $PY scripts/validate_matrix.py

# --- Stage 4: compatibility ---------------------------------------------
# Writes dist/compatibility-summary.json, which the release stage reads and
# refuses to publish over a failing verdict.
run check_compatibility $PY scripts/check_compatibility.py --output dist/compatibility-summary.json

# --- Stage 5: boundary scans --------------------------------------------
run check_no_multitenancy      $PY scripts/check_no_multitenancy.py
run check_no_implementation_code $PY scripts/check_no_implementation_code.py

# --- Stage 6: security ---------------------------------------------------
# detect-secrets-hook compares tracked files against the audited baseline and
# fails on any finding the baseline does not already account for. Findings are
# blocking; see SECURITY.md for the triage rules.
run secret_scan bash -c 'git ls-files -z | xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline'

# pip-audit resolves advisories over the network. An audit that cannot reach
# the advisory database has not been performed, and reporting it as passing
# would be the exact failure mode HARNESS.md section 7 forbids -- so its
# non-zero exit is recorded as a failure rather than tolerated.
run dependency_audit uv run pip-audit --progress-spinner=off --strict

# --- Stage 7: release artifacts -----------------------------------------
if [ "$SKIP_RELEASE" -eq 1 ]; then
  SKIPPED="build_bundle,verify_bundle,verify_consumer_lock"
  printf '\n\033[1m==> release stage SKIPPED\033[0m\n    %s\n' \
    "--skip-release given; every criterion depending on these is reported not_run"
else
  run build_bundle $PY scripts/build_bundle.py
  run verify_bundle $PY scripts/verify_bundle.py
  # Verifies the lock generated from this very release, which proves the
  # published metadata is sufficient for a consumer to construct a pin.
  run verify_consumer_lock $PY scripts/verify_consumer_lock.py \
    --lock dist/example-consumer-lock.yaml \
    --manifest dist/contract-manifest.json \
    --verify-manifest-digest
fi

# --- Stage 8: the gate's own record --------------------------------------
# Recorded last and always, because the summary must describe the run that
# actually happened, including a failing one.
printf '%s\t%s\t%s\n' "quality_gate" "$FAILED" "scripts/quality_gate.sh" >> "$RECORD"
if [ "$FAILED" -eq 0 ]; then
  SUMMARY_LINES+=("pass  quality_gate")
else
  SUMMARY_LINES+=("FAIL  quality_gate")
fi

$PY scripts/write_evidence_summary.py --checks "$RECORD" --skipped "$SKIPPED"
SUMMARY_CODE=$?
if [ "$SUMMARY_CODE" -ne 0 ]; then
  FAILED=1
  SUMMARY_LINES+=("FAIL  write_evidence_summary (exit $SUMMARY_CODE)")
fi

printf '\n\033[1m==> quality gate summary\033[0m\n'
for line in "${SUMMARY_LINES[@]}"; do printf '    %s\n' "$line"; done

if [ "$FAILED" -ne 0 ]; then
  printf '\n\033[1mquality_gate: FAIL\033[0m - see the failing checks above\n' >&2
  exit 1
fi
printf '\nquality_gate: PASS - every executed check exited 0\n'
exit 0
