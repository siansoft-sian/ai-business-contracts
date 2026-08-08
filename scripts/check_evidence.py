#!/usr/bin/env python3
"""Check evidence-report integrity (``TEST_PLAN.md`` Layer G).

Evidence is the only thing a milestone verdict rests on, and it is the one
artifact in this repository that nothing else validates. Everything else --
schemas, catalog, matrix, bundle -- has a checker. Until this script existed,
an evidence file could be truncated, reverted to its template, or left claiming
a commit that never existed, and every gate would still pass. EP-00 finding 9
recorded exactly that happening.

What is verified, per ``TEST_PLAN.md`` Layer G:

- every evidence report has a status, and no blocking report is ``NOT RUN``;
- each records a commit that exists in this repository and is reachable from
  ``HEAD`` -- a commit nobody can check out is not evidence;
- each records a UTC timestamp, the commands run, and exit codes;
- quoted artifact digests match the files, **for reports recorded at the
  current HEAD**. A digest recorded at an earlier commit describes a different
  artifact and is a historical record, not a re-checkable claim; conflating the
  two would either produce false failures or silently verify nothing;
- the independent audit verdict exists, names an ancestor commit, and carries
  no unresolved blocking finding;
- the delivery report is complete, and its overall verdict is *derivable*:
  it may not claim ``PASS`` while any criterion row reads ``FAIL`` or
  ``NOT RUN``.

The audit-verdict and delivery-report checks are structural. This script does
not decide that the audit passed -- that is the auditor's judgement, and a gate
asserting it would be the circular evidence ``AUDITOR.md`` section 7 rejects.
It checks that a completed verdict for this commit exists and is internally
consistent with the criterion statuses it reports.

Exit codes:
    0 - evidence is complete and internally consistent
    1 - at least one defect (blocking)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from _release import sha256_file
from _scope import Violation, build_parser, report

CHECK_NAME = "check_evidence"

EVIDENCE_DIR = "evidence"
INDEX_PATH = "evidence/EVIDENCE_INDEX.md"
AUDIT_PATH = "evidence/08-audit-verdict.md"
DELIVERY_PATH = "DELIVERY_REPORT.md"
CRITERIA_PATH = "ACCEPTANCE_CRITERIA.md"

#: Every report that must be populated for the milestone to be deliverable.
REQUIRED_REPORTS: tuple[str, ...] = (
    "01-preflight.md",
    "02-boundary.md",
    "03-contract-validation.md",
    "04-compatibility.md",
    "05-quality-security.md",
    "06-release-artifacts.md",
    "07-cross-repo-readiness.md",
    "08-audit-verdict.md",
)

STATUS_LINE = re.compile(r"^(?:EP-\d+ )?Status:\s*\*\*(?P<status>[^*]+)\*\*", re.MULTILINE)
COMMIT_SHA = re.compile(r"\b[0-9a-f]{40}\b")
UTC_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z\b")
FENCED_BLOCK = re.compile(r"^```", re.MULTILINE)
EXIT_MENTION = re.compile(r"\bexit\b", re.IGNORECASE)

#: A hash row: ``| `path` | `sha256` |``. Paths are backticked in every report.
HASH_ROW = re.compile(r"^\|\s*`(?P<path>[^`]+)`\s*\|\s*`(?P<digest>[0-9a-f]{64})`\s*\|", re.MULTILINE)

#: Placeholder text a populated report must no longer contain.
PLACEHOLDERS: tuple[str, ...] = ("<sha>", "<timestamp>", "<exact commands>", "<PASS|FAIL>", "<version>")

VERDICT_LINE = re.compile(r"^Verdict:\s*(?P<verdict>PASS|FAIL)\s*$", re.MULTILINE)
CRITERION_ID = re.compile(r"\bM0-CON-\d{3}\b")


def _defect(path: str, pattern: str, detail: str, line: int = 0) -> Violation:
    return Violation(path=path, line=line, pattern=pattern, detail=detail)


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    except OSError:
        return 1, ""
    return completed.returncode, completed.stdout.strip()


def commit_is_reachable(root: Path, sha: str) -> bool:
    """Return whether ``sha`` exists and is HEAD or an ancestor of it.

    Reachability rather than mere existence: an evidence file naming a commit
    on an abandoned branch describes a state the delivered history does not
    contain.
    """
    exists, _ = _git(root, "cat-file", "-e", f"{sha}^{{commit}}")
    if exists != 0:
        return False
    code, _ = _git(root, "merge-base", "--is-ancestor", sha, "HEAD")
    return code == 0


def head_sha(root: Path) -> str:
    _, sha = _git(root, "rev-parse", "HEAD")
    return sha


def check_report(root: Path, relative: str, text: str, head: str) -> tuple[list[Violation], int]:
    """Check one evidence report. Returns defects and verified-digest count."""
    defects: list[Violation] = []

    status = STATUS_LINE.search(text)
    if status is None:
        defects.append(_defect(relative, "no-status", "no '**Status:**' line; the report is unpopulated"))
    elif "NOT RUN" in status.group("status").upper():
        defects.append(
            _defect(
                relative,
                "not-run",
                f"status is {status.group('status').strip()!r}; ACCEPTANCE_CRITERIA.md treats "
                "NOT RUN as FAIL for milestone completion",
            )
        )

    for placeholder in PLACEHOLDERS:
        if placeholder in text:
            defects.append(
                _defect(relative, "placeholder", f"still contains the template placeholder {placeholder!r}")
            )

    shas = COMMIT_SHA.findall(text)
    if not shas:
        defects.append(_defect(relative, "no-commit", "records no full commit SHA"))
    else:
        for sha in sorted(set(shas)):
            if not commit_is_reachable(root, sha):
                defects.append(
                    _defect(
                        relative,
                        "unreachable-commit",
                        f"records commit {sha[:12]} which is not reachable from HEAD; evidence "
                        "must describe a state that can be checked out",
                    )
                )

    if not UTC_TIMESTAMP.search(text):
        defects.append(_defect(relative, "no-timestamp", "records no UTC timestamp"))
    if not FENCED_BLOCK.search(text):
        defects.append(_defect(relative, "no-commands", "records no commands"))
    if not EXIT_MENTION.search(text):
        defects.append(_defect(relative, "no-exit-codes", "records no exit codes"))

    # A digest is re-checkable only against the commit it was recorded at.
    verified = 0
    if head and head in shas:
        for match in HASH_ROW.finditer(text):
            artifact = root / match.group("path")
            if not artifact.is_file():
                continue
            actual = sha256_file(artifact)
            if actual != match.group("digest"):
                defects.append(
                    _defect(
                        relative,
                        "hash-mismatch",
                        f"records {match.group('digest')[:16]}... for {match.group('path')} "
                        f"but the file hashes to {actual[:16]}...",
                        line=text[: match.start()].count("\n") + 1,
                    )
                )
            else:
                verified += 1

    return defects, verified


def check_audit_verdict(root: Path) -> list[Violation]:
    """Structural checks on the independent audit output."""
    path = root / AUDIT_PATH
    if not path.is_file():
        return [_defect(AUDIT_PATH, "missing-audit", "no independent audit verdict was recorded")]

    text = path.read_text(encoding="utf-8")
    defects: list[Violation] = []

    verdict = VERDICT_LINE.search(text)
    if verdict is None:
        defects.append(
            _defect(AUDIT_PATH, "no-verdict", "no 'Verdict: PASS|FAIL' line in the AUDITOR.md output format")
        )
    elif verdict.group("verdict") != "PASS":
        defects.append(
            _defect(AUDIT_PATH, "audit-failed", "the independent audit returned FAIL; M0 does not pass")
        )

    # Every criterion must appear, so none can be quietly omitted from the audit.
    audited = set(CRITERION_ID.findall(text))
    for criterion in sorted(declared_criteria(root) - audited):
        defects.append(
            _defect(AUDIT_PATH, "criterion-not-audited", f"{criterion} does not appear in the audit")
        )

    return defects


def declared_criteria(root: Path) -> set[str]:
    """Return every criterion ID declared in ACCEPTANCE_CRITERIA.md."""
    path = root / CRITERIA_PATH
    if not path.is_file():
        return set()
    return {
        line.split("|")[1].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("| M0-CON-")
    }


def check_delivery_report(root: Path) -> list[Violation]:
    """The delivery verdict must be derivable from the criterion statuses."""
    path = root / DELIVERY_PATH
    if not path.is_file():
        return [_defect(DELIVERY_PATH, "missing-report", "no delivery report")]

    text = path.read_text(encoding="utf-8")
    defects: list[Violation] = []

    for placeholder in PLACEHOLDERS:
        if placeholder in text:
            defects.append(
                _defect(DELIVERY_PATH, "placeholder", f"still contains the placeholder {placeholder!r}")
            )

    claims_pass = re.search(r"verdict:\s*`?PASS`?", text, re.IGNORECASE) is not None
    has_failure = re.search(r"\b(FAIL|NOT RUN)\b", text) is not None
    if claims_pass and has_failure:
        defects.append(
            _defect(
                DELIVERY_PATH,
                "underivable-verdict",
                "claims an overall PASS while reporting FAIL or NOT RUN; the final verdict must "
                "follow from the criterion statuses, not stand beside them",
            )
        )

    missing = declared_criteria(root) - set(CRITERION_ID.findall(text))
    for criterion in sorted(missing):
        defects.append(_defect(DELIVERY_PATH, "criterion-omitted", f"{criterion} is not accounted for"))

    return defects


def check_index(root: Path) -> list[Violation]:
    """The index must not still advertise a report as NOT RUN."""
    path = root / INDEX_PATH
    if not path.is_file():
        return [_defect(INDEX_PATH, "missing-index", "no evidence index")]

    defects = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        # | file | purpose | current status |  ->  cells[1..3]
        if len(cells) < 4:
            continue
        # Only the status column decides. The other cells legitimately mention
        # criteria that were NOT RUN at the EP the row describes, and reading
        # those as a report status would flag accurate history as a defect.
        if "NOT RUN" in cells[3].upper():
            defects.append(
                Violation(
                    path=INDEX_PATH,
                    line=number,
                    pattern="index-not-run",
                    detail=f"index records {cells[1]} as NOT RUN",
                )
            )
    return defects


def scan(root: Path) -> tuple[list[Violation], int]:
    """Return every evidence defect under ``root``, and the digests verified."""
    defects: list[Violation] = []
    verified = 0
    head = head_sha(root)

    for name in REQUIRED_REPORTS:
        relative = f"{EVIDENCE_DIR}/{name}"
        path = root / relative
        if not path.is_file():
            defects.append(_defect(relative, "missing-report", "required evidence report is absent"))
            continue
        report_defects, report_verified = check_report(root, relative, path.read_text(encoding="utf-8"), head)
        defects += report_defects
        verified += report_verified

    defects += check_index(root)
    defects += check_audit_verdict(root)
    defects += check_delivery_report(root)
    return defects, verified


def main(argv: list[str] | None = None) -> int:
    args = build_parser(__doc__.splitlines()[0]).parse_args(argv)
    violations, verified = scan(args.root)
    return report(
        CHECK_NAME,
        args.root,
        violations,
        args.as_json,
        pass_message=(
            f"{len(REQUIRED_REPORTS)} reports populated with reachable commits, commands, and "
            f"exit codes; {verified} recorded artifact digest(s) re-verified at HEAD; audit "
            "verdict PASS; delivery verdict derivable"
        ),
        fail_noun="evidence defect",
    )


if __name__ == "__main__":
    sys.exit(main())
