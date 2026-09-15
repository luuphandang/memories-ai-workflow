#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TAG_PATTERN = re.compile(r"\[([a-z0-9-]+):\s*([^\]]+?)\s*\]")
TEST_LEVEL_RANK = {"static": 0, "unit": 1, "integration": 2, "contract": 2, "e2e": 3, "manual": 3}
PASSED_SUMMARY = re.compile(r"Tests:\s*\d+ passed", re.IGNORECASE)


def evidence_test_level(evidence: str) -> str | None:
    for name, value in TAG_PATTERN.findall(evidence):
        if name == "test-level" and value in TEST_LEVEL_RANK:
            return value
    return None


def real_infra_artifact_reason(infra: list[str], evidence_dir: Path | None) -> str | None:
    """Return a failure reason, or None if the required real-infra artifact is present."""
    required = [item for item in infra if item != "none"]
    if not required or evidence_dir is None:
        return None
    if "browser" in required:
        matrix_path = evidence_dir / "fidelity-matrix.json"
        if not matrix_path.is_file():
            return "requires real-browser fidelity evidence but fidelity-matrix.json is missing"
        try:
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "fidelity-matrix.json is not valid JSON"
        if not any(entry.get("status") == "passed" for entry in matrix.get("entries", [])):
            return "fidelity-matrix.json has no passed entry"
    non_browser = [item for item in required if item != "browser"]
    if non_browser:
        log_path = evidence_dir / "logs" / "e2e-full-run.log"
        if not log_path.is_file() or not log_path.read_text(encoding="utf-8").strip():
            return f"requires real infra ({', '.join(non_browser)}) but evidence/logs/e2e-full-run.log is missing/empty"
        if not PASSED_SUMMARY.search(log_path.read_text(encoding="utf-8")):
            return f"requires real infra ({', '.join(non_browser)}) but e2e-full-run.log has no passing test summary"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic acceptance-evidence coverage")
    parser.add_argument("execution_plan", type=Path)
    parser.add_argument("implementation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="ai/tasks/<id>/evidence directory; when given, criteria with evidence_requirements "
        "are also checked for a matching [test-level: X] tag and, if requires_real_infra is "
        "declared, a real-infra artifact (e2e-full-run.log or fidelity-matrix.json).",
    )
    args = parser.parse_args()
    plan = json.loads(args.execution_plan.read_text(encoding="utf-8"))
    implementation = json.loads(args.implementation.read_text(encoding="utf-8"))
    handoff = {item["criterion"]: item for item in implementation.get("acceptance_criteria", [])}
    planned_criteria = [
        criterion
        for slice_item in plan["slices"]
        for criterion in slice_item["acceptance_criteria"]
    ]
    rows = []
    missing = []
    for slice_item in plan["slices"]:
        slice_evidence = handoff.get(f"slice:{slice_item['id']}")
        requirements = slice_item.get("evidence_requirements", {})
        for criterion in slice_item["acceptance_criteria"]:
            evidence = handoff.get(criterion) or slice_evidence
            row = {
                "criterion": criterion,
                "slice": slice_item["id"],
                "status": evidence.get("status") if evidence else "missing",
                "evidence": evidence.get("evidence", "") if evidence else "",
                "coverage": "criterion" if handoff.get(criterion) else ("slice" if slice_evidence else "missing"),
            }
            rows.append(row)
            if not evidence or not evidence.get("evidence") or evidence.get("status") != "passed":
                missing.append(criterion)
                continue
            requirement = requirements.get(criterion)
            if requirement is None:
                continue
            level = evidence_test_level(evidence.get("evidence", ""))
            min_level = requirement["min_test_level"]
            if level is None or TEST_LEVEL_RANK[level] < TEST_LEVEL_RANK[min_level]:
                row["status"] = "insufficient_test_level"
                missing.append(
                    f"{criterion} (requires min_test_level={min_level}, evidence declares "
                    f"[test-level: {level or 'none'}])"
                )
                continue
            infra_reason = real_infra_artifact_reason(requirement.get("requires_real_infra", []), args.evidence_dir)
            if infra_reason:
                row["status"] = "insufficient_real_infra_evidence"
                missing.append(f"{criterion} ({infra_reason})")
    output = {"passed": not missing, "rows": rows, "missing": missing}
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
