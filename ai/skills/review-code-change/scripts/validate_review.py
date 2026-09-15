#!/usr/bin/env python3
"""Validate semantic review gates that are stricter than JSON shape validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


FULL_PASSES = {"requirements", "diff", "architecture", "behavior", "tests", "security", "regression"}
DELTA_PASSES = {"diff", "behavior", "tests", "regression"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--mode", choices=("full", "delta"), required=True)
    parser.add_argument("--fail-on", default="blocker,major")
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="ai/tasks/<id>/review-history directory; when given, verify the most recent "
        "prior cycle's blocking findings each have a matching finding_id in this review's "
        "review_coverage.prior_findings",
    )
    args = parser.parse_args()

    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: cannot read review JSON: {exc}")
        return 1

    errors: list[str] = []
    fail_on = {item.strip() for item in args.fail_on.split(",") if item.strip()}
    coverage = review.get("review_coverage") or {}
    completed = set(coverage.get("review_passes") or [])
    required = FULL_PASSES if args.mode == "full" else DELTA_PASSES
    missing_passes = sorted(required - completed)
    if missing_passes:
        errors.append("missing review passes: " + ", ".join(missing_passes))

    incomplete_files = [item.get("file", "<unknown>") for item in coverage.get("changed_files", []) if item.get("status") != "reviewed"]
    if incomplete_files:
        errors.append("changed files not reviewed: " + ", ".join(incomplete_files))
    if any(item.get("status") == "not_reviewed" for item in coverage.get("risk_areas", [])):
        errors.append("one or more risk areas were not reviewed")
    if any(item.get("status") == "not_verified" for item in coverage.get("prior_findings", [])):
        errors.append("one or more prior findings were not verified")
    if args.history_dir is not None and args.history_dir.is_dir():
        ledgers = sorted(args.history_dir.glob("cycle-*.json"))
        if ledgers:
            prior_ledger = json.loads(ledgers[-1].read_text(encoding="utf-8"))
            reported_ids = {
                item.get("finding_id") for item in coverage.get("prior_findings", []) if item.get("finding_id")
            }
            missing_ids = sorted(
                item["finding_id"]
                for item in prior_ledger.get("findings", [])
                if item.get("finding_id") not in reported_ids
            )
            if missing_ids:
                errors.append("prior findings ledger missing retest for: " + ", ".join(missing_ids))
    if coverage.get("completion_statement") is not True:
        errors.append("review coverage is not declared complete")

    matrix = review.get("test_matrix") or []
    if not matrix:
        errors.append("test matrix is empty")
    ids = [case.get("id") for case in matrix]
    if len(ids) != len(set(ids)):
        errors.append("test matrix IDs are not unique")
    sources = "\n".join(str(source).lower() for case in matrix for source in case.get("sources", []))
    if args.mode == "full" and not any(token in sources for token in ("requirement:", "acceptance:", "ac:")):
        errors.append("full review matrix has no requirement-derived case")
    if "diff-impact:" not in sources:
        errors.append("test matrix has no diff-impact-derived case")
    unresolved_cases = [case.get("id", "<unknown>") for case in matrix if case.get("status") in {"failed", "missing"}]
    evidence_gaps = [case.get("id", "<unknown>") for case in matrix if case.get("status") in {"passed", "failed", "not_applicable"} and not str(case.get("evidence", "")).strip()]
    if evidence_gaps:
        errors.append("matrix cases lack evidence: " + ", ".join(evidence_gaps))
    if unresolved_cases and (review.get("validation_assessment") or {}).get("passed") is True:
        errors.append("validation is marked passed while matrix has failed/missing cases: " + ", ".join(unresolved_cases))

    blocking = [finding for finding in review.get("findings", []) if finding.get("severity") in fail_on]
    for finding in blocking:
        guidance = finding.get("implementation_guidance") or {}
        if not str(guidance.get("approach", "")).strip() or not guidance.get("code_locations") or not guidance.get("tests") or not guidance.get("done_when"):
            errors.append(f"blocking finding lacks complete implementation guidance: {finding.get('title', '<untitled>')}")

    verdict = review.get("verdict")
    if verdict == "pass" and blocking:
        errors.append("pass verdict contains blocking findings")
    if verdict == "pass" and unresolved_cases:
        errors.append("pass verdict contains failed or missing matrix cases")
    if errors and verdict != "blocked":
        errors.append("incomplete review must use blocked verdict")

    if errors:
        for error in errors:
            print(f"INVALID: {error}")
        return 1
    print(f"Review artifact PASSED ({args.mode}, {len(matrix)} matrix cases, {len(review.get('findings', []))} findings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
