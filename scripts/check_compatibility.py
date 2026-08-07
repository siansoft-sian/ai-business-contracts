#!/usr/bin/env python3
"""Classify the difference between a baseline and a candidate contract set.

Every difference lands in exactly one of three classes, and the boundary
between them is drawn by *what can be proven*, not by what feels safe:

``breaking``
    Demonstrated to reject data or usage the baseline accepted. Either
    structurally decidable (a removed field cannot come back) or proven by
    counter-example (a value the baseline's own examples declare valid which
    the candidate rejects).

``review_required``
    Cannot be shown safe. Additive changes live here, because
    ``HARNESS.md`` section 6 is explicit that additive is not automatically
    safe: enum expansion and new variants break a consumer that matches
    exhaustively. So does an undecidable change, such as a rewritten regex
    with no counter-example.

``compatible``
    Proven not to affect existing consumers.

The asymmetry is deliberate. A change is never called compatible because
nothing disproved it; it is called compatible only when the structure shows it
harmless. Anything else is escalated rather than waved through.

Regex strictness is undecidable in general, so a changed ``pattern`` is tested
against the values the baseline itself declares valid. A failing witness earns
a breaking verdict and is cited in the finding; no witness means
``review_required``, never ``compatible``.

Exit codes:
    0 - pass, review_required, or no-baseline
    1 - fail (an unapproved breaking change)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from _contracts import (
    ContractLoadError,
    load_schemas,
    load_yaml,
    schema_by_id,
)
from _scope import repo_root

CHECK_NAME = "check_compatibility"

BASELINE_PATH = "compatibility/baseline.yaml"

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

#: Type changes that do not reject previously valid data. Everything else is
#: breaking: widening is the exception, not the rule.
WIDENING_TYPE_CHANGES: frozenset[tuple[str, str]] = frozenset({("integer", "number")})


@dataclass
class Finding:
    """One classified difference."""

    contract_id: str
    change: str
    location: str
    detail: str
    witness: str | None = None

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["witness"] is None:
            del data["witness"]
        return data


@dataclass
class Result:
    """The comparison verdict, shaped by compatibility-result.v1."""

    baseline: str | None
    candidate: str
    breaking: list[Finding] = field(default_factory=list)
    review_required: list[Finding] = field(default_factory=list)
    compatible: list[Finding] = field(default_factory=list)
    approved_major_transition: bool = False
    no_baseline: bool = False

    @property
    def result(self) -> str:
        if self.no_baseline:
            return "no-baseline"
        if self.breaking and not self.approved_major_transition:
            return "fail"
        if self.review_required:
            return "review_required"
        return "pass"

    def as_document(self, checked_at_utc: str) -> dict[str, Any]:
        return {
            "baseline": self.baseline,
            "candidate": self.candidate,
            "result": self.result,
            "breaking": [f.as_dict() for f in self.breaking],
            "review_required": [f.as_dict() for f in self.review_required],
            "compatible": [f.as_dict() for f in self.compatible],
            "approved_major_transition": self.approved_major_transition,
            "checked_at_utc": checked_at_utc,
        }


# --- schema walking -------------------------------------------------------


def _properties(node: dict[str, Any]) -> dict[str, Any]:
    props = node.get("properties")
    return props if isinstance(props, dict) else {}


def _required(node: dict[str, Any]) -> set[str]:
    req = node.get("required")
    return set(req) if isinstance(req, list) else set()


def _examples(node: dict[str, Any]) -> list[Any]:
    ex = node.get("examples")
    return list(ex) if isinstance(ex, list) else []


def _resolve_local(document: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Follow a same-document ``$ref`` one hop, so $defs are compared by value."""
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return node
    target: Any = document
    for raw in ref[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(target, dict) or token not in target:
            return node
        target = target[token]
    return target if isinstance(target, dict) else node


def _compare_node(
    contract_id: str,
    pointer: str,
    base_doc: dict[str, Any],
    cand_doc: dict[str, Any],
    base: dict[str, Any],
    cand: dict[str, Any],
    out: Result,
) -> None:
    """Compare one schema node, recursing into properties."""
    base = _resolve_local(base_doc, base)
    cand = _resolve_local(cand_doc, cand)

    _compare_type(contract_id, pointer, base, cand, out)
    _compare_enum(contract_id, pointer, base, cand, out)
    _compare_bounds(contract_id, pointer, base, cand, out)
    _compare_pattern(contract_id, pointer, base, cand, out)
    _compare_extensibility(contract_id, pointer, base, cand, out)
    _compare_properties(contract_id, pointer, base_doc, cand_doc, base, cand, out)


def _compare_type(
    contract_id: str, pointer: str, base: dict[str, Any], cand: dict[str, Any], out: Result
) -> None:
    base_type, cand_type = base.get("type"), cand.get("type")
    if base_type is None or cand_type is None or base_type == cand_type:
        return
    if (
        isinstance(base_type, str)
        and isinstance(cand_type, str)
        and (base_type, cand_type) in WIDENING_TYPE_CHANGES
    ):
        out.compatible.append(
            Finding(
                contract_id,
                "type-changed",
                pointer,
                f"type widened from {base_type!r} to {cand_type!r}; every previously "
                "valid value remains valid",
            )
        )
        return
    out.breaking.append(
        Finding(
            contract_id,
            "type-changed",
            pointer,
            f"type changed from {base_type!r} to {cand_type!r}; data written for the baseline is rejected",
        )
    )


def _compare_enum(
    contract_id: str, pointer: str, base: dict[str, Any], cand: dict[str, Any], out: Result
) -> None:
    base_enum, cand_enum = base.get("enum"), cand.get("enum")
    if not isinstance(base_enum, list) or not isinstance(cand_enum, list):
        return
    removed = [v for v in base_enum if v not in cand_enum]
    added = [v for v in cand_enum if v not in base_enum]
    for value in removed:
        out.breaking.append(
            Finding(
                contract_id,
                "enum-value-removed",
                pointer,
                f"allowed value {value!r} was removed; data carrying it is now rejected",
                witness=str(value),
            )
        )
    if added:
        out.review_required.append(
            Finding(
                contract_id,
                "enum-value-added",
                pointer,
                f"allowed values {added!r} were added. Additive, but a consumer that "
                "matches this field exhaustively has no branch for them, so the owner "
                "must confirm no such consumer exists",
            )
        )


def _compare_bounds(
    contract_id: str, pointer: str, base: dict[str, Any], cand: dict[str, Any], out: Result
) -> None:
    """Numeric and length bounds. Narrowing is decidable, so it is breaking."""
    narrowings: tuple[tuple[str, Callable[[float, float], bool], str], ...] = (
        ("minimum", lambda b, c: c > b, "raised"),
        ("exclusiveMinimum", lambda b, c: c > b, "raised"),
        ("minLength", lambda b, c: c > b, "raised"),
        ("minItems", lambda b, c: c > b, "raised"),
        ("maximum", lambda b, c: c < b, "lowered"),
        ("exclusiveMaximum", lambda b, c: c < b, "lowered"),
        ("maxLength", lambda b, c: c < b, "lowered"),
        ("maxItems", lambda b, c: c < b, "lowered"),
    )
    for keyword, is_narrower, verb in narrowings:
        base_value, cand_value = base.get(keyword), cand.get(keyword)
        if isinstance(base_value, (int, float)) and isinstance(cand_value, (int, float)):
            if is_narrower(base_value, cand_value):
                out.breaking.append(
                    Finding(
                        contract_id,
                        "range-narrowed",
                        pointer,
                        f"{keyword} {verb} from {base_value} to {cand_value}; values the "
                        "baseline accepted are now rejected",
                    )
                )
        elif base_value is None and isinstance(cand_value, (int, float)):
            out.breaking.append(
                Finding(
                    contract_id,
                    "range-narrowed",
                    pointer,
                    f"{keyword} of {cand_value} was introduced where the baseline had no "
                    "bound; previously valid values are now rejected",
                )
            )


def _compare_pattern(
    contract_id: str, pointer: str, base: dict[str, Any], cand: dict[str, Any], out: Result
) -> None:
    """A changed regex, decided by counter-example where one exists.

    Regex strictness is undecidable in general, so the baseline's own declared
    examples are used as witnesses. A value the baseline calls valid which the
    candidate rejects proves the tightening. Absent such a value the change is
    escalated, never assumed safe.
    """
    base_pattern, cand_pattern = base.get("pattern"), cand.get("pattern")
    if cand_pattern is None or base_pattern == cand_pattern:
        return

    try:
        compiled = re.compile(cand_pattern)
    except re.error as exc:
        out.breaking.append(
            Finding(contract_id, "pattern-changed", pointer, f"candidate pattern is invalid: {exc}")
        )
        return

    witnesses = [str(v) for v in _examples(base) if isinstance(v, (str, int, float))]
    rejected = [w for w in witnesses if not compiled.search(w)]

    if rejected:
        out.breaking.append(
            Finding(
                contract_id,
                "pattern-changed",
                pointer,
                f"pattern tightened from {base_pattern!r} to {cand_pattern!r}; a value the "
                "baseline declares valid is now rejected",
                witness=rejected[0],
            )
        )
        return

    if base_pattern is None:
        detail = (
            f"pattern {cand_pattern!r} was introduced where the baseline had none. No "
            "declared example disproves it, but any undeclared value not matching it is "
            "now rejected"
        )
    else:
        detail = (
            f"pattern changed from {base_pattern!r} to {cand_pattern!r}. No declared "
            "example is rejected, but regex strictness cannot be decided in general, so "
            "this cannot be shown safe"
        )
    out.review_required.append(Finding(contract_id, "pattern-changed", pointer, detail))


def _compare_extensibility(
    contract_id: str, pointer: str, base: dict[str, Any], cand: dict[str, Any], out: Result
) -> None:
    base_additional = base.get("additionalProperties")
    cand_additional = cand.get("additionalProperties")
    if base_additional is not False and cand_additional is False:
        out.breaking.append(
            Finding(
                contract_id,
                "extensible-became-closed",
                pointer,
                "payload changed from extensible to closed; documents carrying fields the "
                "baseline tolerated are now rejected",
            )
        )


def _compare_properties(
    contract_id: str,
    pointer: str,
    base_doc: dict[str, Any],
    cand_doc: dict[str, Any],
    base: dict[str, Any],
    cand: dict[str, Any],
    out: Result,
) -> None:
    base_props, cand_props = _properties(base), _properties(cand)
    if not base_props and not cand_props:
        return

    base_required, cand_required = _required(base), _required(cand)
    removed = sorted(set(base_props) - set(cand_props))
    added = sorted(set(cand_props) - set(base_props))

    # Exactly one removal against exactly one addition is unambiguously a
    # rename. It is still breaking -- a consumer reading the old name breaks
    # either way -- but reporting it as one finding rather than a removal plus
    # an unrelated "compatible" addition keeps the verdict honest.
    renamed_pair = (len(removed), len(added)) == (1, 1)

    for name in removed:
        here = f"{pointer}/properties/{name}"
        if renamed_pair:
            out.breaking.append(
                Finding(
                    contract_id,
                    "field-renamed",
                    here,
                    f"property {name!r} was renamed to {added[0]!r}; consumers reading the "
                    "old name break, so a rename is a removal to every existing consumer",
                )
            )
        else:
            out.breaking.append(
                Finding(
                    contract_id,
                    "field-removed",
                    here,
                    f"property {name!r} was removed; consumers reading it break",
                )
            )

    for name in added:
        here = f"{pointer}/properties/{name}"
        if renamed_pair:
            # Already accounted for by the rename finding above.
            continue
        if name in cand_required:
            out.breaking.append(
                Finding(
                    contract_id,
                    "field-added-required",
                    here,
                    f"required property {name!r} was added; documents written for the "
                    "baseline omit it and are now rejected",
                )
            )
        else:
            out.compatible.append(
                Finding(
                    contract_id,
                    "field-added-optional",
                    here,
                    f"optional property {name!r} was added; existing consumers are unaffected",
                )
            )

    for name in sorted(set(base_props) & set(cand_props)):
        here = f"{pointer}/properties/{name}"
        if name not in base_required and name in cand_required:
            out.breaking.append(
                Finding(
                    contract_id,
                    "optional-became-required",
                    here,
                    f"property {name!r} became required; documents that omitted it are now rejected",
                )
            )
        _compare_node(contract_id, here, base_doc, cand_doc, base_props[name], cand_props[name], out)


# --- contract-set comparison ---------------------------------------------


def _major(version: str) -> int | None:
    match = SEMVER.match(version)
    return int(match.group(1)) if match else None


def _documentation_only(base: dict[str, Any], cand: dict[str, Any]) -> bool:
    """Whether two contracts differ only in human-readable prose.

    ``x-contract-version`` is ignored: any published change carries a version
    bump, so counting it as a difference would mean no change could ever be
    classified documentation-only.
    """

    prose_keys = {"description", "title", "$comment"}

    def strip(node: Any) -> Any:
        if isinstance(node, dict):
            return {
                key: strip(value)
                for key, value in node.items()
                if key not in prose_keys and key != "x-contract-version"
            }
        if isinstance(node, list):
            return [strip(item) for item in node]
        return node

    def prose(node: Any) -> list[Any]:
        collected: list[Any] = []
        if isinstance(node, dict):
            for key, value in sorted(node.items()):
                if key in prose_keys:
                    collected.append(value)
                else:
                    collected.extend(prose(value))
        elif isinstance(node, list):
            for item in node:
                collected.extend(prose(item))
        return collected

    # Both conditions matter. Equal stripped forms alone would also be true
    # when nothing changed but the version, and reporting that as a
    # documentation change would be false.
    return strip(base) == strip(cand) and prose(base) != prose(cand)


def compare(baseline_root: Path, candidate_root: Path) -> Result:
    """Compare two contract sets and classify every difference."""
    base_schemas = load_schemas(baseline_root)
    cand_schemas = load_schemas(candidate_root)
    base_by_id = schema_by_id(base_schemas)
    cand_by_id = schema_by_id(cand_schemas)

    result = Result(baseline=str(baseline_root.name), candidate=str(candidate_root.name))

    # Duplicate (contract_id, version) inside the candidate.
    seen: dict[tuple[str, str], int] = {}
    for document in cand_schemas.values():
        key = (str(document.get("$id")), str(document.get("x-contract-version")))
        seen[key] = seen.get(key, 0) + 1
    for (contract_id, version), count in seen.items():
        if count > 1:
            result.breaking.append(
                Finding(
                    contract_id,
                    "duplicate-contract-version",
                    "#",
                    f"({contract_id}, {version}) is declared by {count} schemas; a version "
                    "must identify exactly one artifact",
                )
            )

    # Unresolvable references in the candidate.
    for path, document in cand_schemas.items():
        for ref in _iter_refs(document):
            target = ref.partition("#")[0]
            if target and target not in cand_by_id:
                result.breaking.append(
                    Finding(
                        str(document.get("$id") or path.name),
                        "unresolvable-reference",
                        "#",
                        f"{ref!r} names {target!r}, which the candidate set does not declare",
                    )
                )

    majors_bumped: list[bool] = []

    for contract_id, (_, base_doc) in sorted(base_by_id.items()):
        if contract_id not in cand_by_id:
            result.breaking.append(
                Finding(
                    contract_id,
                    "contract-removed",
                    "#",
                    "contract is no longer published; every consumer of it breaks",
                )
            )
            continue

        cand_doc = cand_by_id[contract_id][1]
        base_version = str(base_doc.get("x-contract-version", ""))
        cand_version = str(cand_doc.get("x-contract-version", ""))

        # Immutability: a released version's content must never change.
        if base_version == cand_version and base_doc != cand_doc:
            result.breaking.append(
                Finding(
                    contract_id,
                    "released-version-content-changed",
                    "#",
                    f"version {base_version} was published with different content; released "
                    "artifacts are immutable and a correction requires a new version",
                )
            )

        if _documentation_only(base_doc, cand_doc):
            result.compatible.append(
                Finding(
                    contract_id,
                    "documentation-only",
                    "#",
                    "only description or title text changed; no consumer-visible semantics moved",
                )
            )

        before = len(result.breaking)
        _compare_node(contract_id, "#", base_doc, cand_doc, base_doc, cand_doc, result)
        introduced_breaking = len(result.breaking) > before

        base_major, cand_major = _major(base_version), _major(cand_version)
        if introduced_breaking:
            majors_bumped.append(
                base_major is not None and cand_major is not None and cand_major > base_major
            )

    for contract_id in sorted(set(cand_by_id) - set(base_by_id)):
        result.compatible.append(
            Finding(
                contract_id,
                "contract-added",
                "#",
                "new independent contract; no existing consumer is affected",
            )
        )

    result.approved_major_transition = bool(majors_bumped) and all(majors_bumped)
    return result


def _iter_refs(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_iter_refs(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_refs(item))
    return found


def load_baseline_declaration(root: Path) -> dict[str, Any]:
    """Read the declared baseline release, if the repository has one."""
    path = root / BASELINE_PATH
    if not path.is_file():
        return {}
    document = load_yaml(path)
    return document if isinstance(document, dict) else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", type=Path, help="baseline contract set directory")
    parser.add_argument("--candidate", type=Path, help="candidate contract set directory")
    parser.add_argument("--root", type=Path, default=repo_root(), help="repository root")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON")
    parser.add_argument("--output", type=Path, help="also write the JSON document to this path")
    parser.add_argument(
        "--checked-at",
        default=None,
        help="UTC timestamp to stamp (default: now). Fixed values keep output reproducible.",
    )
    return parser


def _now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checked_at = args.checked_at or _now_utc()

    if bool(args.baseline) != bool(args.candidate):
        print("--baseline and --candidate must be given together", file=sys.stderr)
        return 2

    if args.baseline and args.candidate:
        try:
            result = compare(args.baseline, args.candidate)
        except ContractLoadError as exc:
            print(f"{CHECK_NAME}: FAIL - {exc}", file=sys.stderr)
            return 1
    else:
        # No explicit pair: compare the working tree against the declared
        # baseline release. Until a release exists there is nothing to compare,
        # and that is reported as its own verdict rather than as a pass.
        declaration = load_baseline_declaration(args.root)
        baseline_release = declaration.get("baseline_release")
        if not baseline_release:
            result = Result(
                baseline=None,
                candidate=str(declaration.get("first_published_baseline") or "working-tree"),
                no_baseline=True,
            )
        else:
            print(
                f"{CHECK_NAME}: baseline release {baseline_release!r} is declared but "
                "release artifacts are not available in this milestone",
                file=sys.stderr,
            )
            return 2

    document = result.as_document(checked_at)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        verdict = document["result"]
        counts = (
            f"{len(result.breaking)} breaking, "
            f"{len(result.review_required)} review-required, "
            f"{len(result.compatible)} compatible"
        )
        if verdict == "no-baseline":
            print(
                f"{CHECK_NAME}: NO BASELINE - no prior release exists, so nothing was "
                "compared. The engine is proven by the fixtures under compatibility/fixtures/; "
                f"the first published baseline will be {document['candidate']}."
            )
        elif verdict == "fail":
            print(f"{CHECK_NAME}: FAIL - {counts}", file=sys.stderr)
            for finding in result.breaking:
                witness = f" [witness: {finding.witness!r}]" if finding.witness else ""
                print(f"  {finding.location}: [{finding.change}] {finding.detail}{witness}", file=sys.stderr)
        else:
            print(f"{CHECK_NAME}: {verdict.upper()} - {counts}")
            for finding in result.review_required:
                print(f"  {finding.location}: [{finding.change}] {finding.detail}")

    return 1 if document["result"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
