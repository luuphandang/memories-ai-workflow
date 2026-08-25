#!/usr/bin/env python3
"""Deterministic check that an implementation handoff's acceptance evidence is
internally consistent and matches the authoritative artifacts it summarizes
(MEMORIES-0006 fix-request review cycle 15, finding #2).

`build_evidence_matrix.py` copies each acceptance criterion's `evidence` string
verbatim into `acceptance-evidence.json` and reports `passed: true` whenever a
non-empty string with `status: passed` exists -- it never checks whether facts
*inside* that string are true, or even mutually consistent with each other. An
`implementation.json` built across many incremental attempts can accumulate an
early attempt's numbers (e.g. "35 test cases") alongside a later attempt's
corrected numbers (e.g. "45 test cases") in the very same evidence paragraph
and still be reported as passing evidence, because nothing ever cross-checks
prose against ground truth.

This script requires evidence text to cite machine-checkable facts using an
explicit `[tag: value]` marker (e.g. `[unit-tests: 69 suites / 431 tests]`)
rather than free-form prose numbers, then:

  1. Rejects self-contradiction: the same tag must not appear twice with two
     different values anywhere across implementation.json's acceptance
     evidence and handoff_status text.
  2. Rejects drift from ground truth: for every tag this script knows how to
     compute independently (see GROUND_TRUTH below), the claimed value must
     equal the value freshly computed from the actual artifact.

Tags with no registered ground-truth computer are only checked for
self-consistency (#1) -- this keeps the script usable for facts that are true
by construction (e.g. an attempt number) without requiring every tag to have a
bespoke checker.

Usage:
    check_evidence_freshness.py <implementation.json> <repo-dir> <evidence-dir>

Exits 0 and prints a summary when every tracked tag is consistent and matches
ground truth. Exits 1 and lists every problem otherwise.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

TAG_PATTERN = re.compile(r"\[([a-z0-9-]+):\s*([^\]]+?)\s*\]")
UNIT_INVENTORY_PATTERN = re.compile(r"\b(\d+)\s+suites\s*/\s*(\d+)\s+tests\b", re.IGNORECASE)
ARCHITECTURE_INVENTORY_PATTERN = re.compile(
    r"\b(\d+)\s+modules\s*/\s*(\d+)\s+(?:deps|dependencies)\b", re.IGNORECASE
)
PROVENANCE_INVENTORY_PATTERN = re.compile(
    r"\b(\d+)\s+inputs\s*/\s*(\d+)\s+artifacts\b", re.IGNORECASE
)


def collect_tagged_text(implementation: dict) -> list[str]:
    texts: list[str] = []
    for criterion in implementation.get("acceptance_criteria", []):
        texts.append(criterion.get("evidence", ""))
    handoff_status = implementation.get("handoff_status") or {}
    for key in ("review_state", "acceptance_state"):
        value = handoff_status.get(key)
        if isinstance(value, str):
            texts.append(value)
    summary = implementation.get("summary")
    if isinstance(summary, str):
        texts.append(summary)
    return texts


def collect_tags(implementation: dict) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for text in collect_tagged_text(implementation):
        for name, value in TAG_PATTERN.findall(text):
            tags.setdefault(name, []).append(value)
    return tags


def collect_current_attempt_claims(implementation: dict, attempt: str) -> list[str]:
    """Return authoritative audit text explicitly attributed to the current attempt."""
    marker = re.compile(rf"\battempt\s+{re.escape(attempt)}\b", re.IGNORECASE)
    claims: list[str] = []
    for section in ("decisions", "validation_commands"):
        for entry in implementation.get(section, []):
            if not isinstance(entry, dict):
                continue
            text = "\n".join(value for value in entry.values() if isinstance(value, str))
            if marker.search(text):
                claims.append(text)
    for skill in implementation.get("applied_skills", []):
        if not isinstance(skill, dict):
            continue
        for check in skill.get("checks_completed", []):
            if isinstance(check, str) and marker.search(check):
                claims.append(check)
    return claims


def ground_truth_unit_tests(repo_dir: Path, evidence_dir: Path) -> str | None:
    log = evidence_dir / "logs" / "unit-test-run.log"
    if log.exists():
        text = log.read_text(encoding="utf-8")
        suites = re.search(r"Test Suites:\s*(\d+) passed,\s*\d+ total", text)
        tests = re.search(r"Tests:\s*(\d+) passed,\s*\d+ total", text)
        if suites and tests:
            return f"{suites.group(1)} suites / {tests.group(1)} tests"
    runtime_report = evidence_dir.parents[3] / "worktrees" / evidence_dir.parent.name / ".ai" / "validation" / "backend.json"
    if runtime_report.exists():
        report = json.loads(runtime_report.read_text(encoding="utf-8"))
        test_command = next((item for item in report.get("commands", []) if item.get("name") == "test"), None)
        if test_command and test_command.get("status") == "passed":
            text = test_command.get("output_tail", "")
            suites = re.search(r"Test Suites:\s*(\d+) passed,\s*\d+ total", text)
            tests = re.search(r"Tests:\s*(\d+) passed,\s*\d+ total", text)
            if suites and tests:
                return f"{suites.group(1)} suites / {tests.group(1)} tests"
    return None


def ground_truth_e2e_tests(repo_dir: Path, evidence_dir: Path) -> str | None:
    log = evidence_dir / "logs" / "e2e-full-run.log"
    if not log.exists():
        return None
    text = log.read_text(encoding="utf-8")
    suites = re.search(r"Test Suites:\s*(\d+) passed,\s*\d+ total", text)
    tests = re.search(r"Tests:\s*(\d+) passed,\s*\d+ total", text)
    if not suites or not tests:
        return None
    return f"{suites.group(1)} suites / {tests.group(1)} tests"


def ground_truth_characterization_tests(repo_dir: Path, evidence_dir: Path) -> str | None:
    log = evidence_dir / "characterization" / "legacy-run-output.txt"
    if not log.exists():
        return None
    text = log.read_text(encoding="utf-8")
    suites = re.search(r"Test Suites:\s*(\d+) passed,\s*\d+ total", text)
    tests = re.search(r"Tests:\s*(\d+) passed,\s*\d+ total", text)
    if not suites or not tests:
        return None
    return f"{suites.group(1)} suites / {tests.group(1)} tests"


def ground_truth_context_spec_cases(repo_dir: Path, evidence_dir: Path) -> str | None:
    spec = repo_dir / "libs" / "platform" / "context" / "test" / "runtime-context.service.spec.ts"
    if not spec.exists():
        return None
    text = spec.read_text(encoding="utf-8")
    count = len(re.findall(r"^\s*it\(", text, flags=re.MULTILINE))
    return str(count)


def ground_truth_characterization_baseline(repo_dir: Path, evidence_dir: Path) -> str | None:
    path = evidence_dir / "characterization-baseline.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^v(\d+)\s", text, flags=re.MULTILINE)
    return f"v{match.group(1)}" if match else None


def ground_truth_architecture(repo_dir: Path, evidence_dir: Path) -> str | None:
    path = evidence_dir / "logs" / "architecture.log"
    if not path.exists():
        return None
    match = re.search(r"(\d+) modules,\s*(\d+) dependencies cruised", path.read_text(encoding="utf-8"))
    return f"{match.group(1)} modules / {match.group(2)} dependencies" if match else None


def ground_truth_provenance_inventory(repo_dir: Path, evidence_dir: Path) -> str | None:
    path = evidence_dir / "provenance.json"
    if not path.exists():
        return None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return f"{len(manifest.get('inputs', []))} inputs / {len(manifest.get('artifacts', []))} artifacts"


def ground_truth_baseline_unit_tests(repo_dir: Path, evidence_dir: Path) -> str | None:
    path = evidence_dir / "characterization-baseline.md"
    if not path.exists():
        return None
    match = re.search(
        r"Current validated unit inventory:\s*\[unit-tests:\s*([^\]]+)\]",
        path.read_text(encoding="utf-8"),
    )
    return match.group(1).strip() if match else None


def task_state(evidence_dir: Path) -> dict:
    path = evidence_dir.parent / "state.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def ground_truth_implementation_attempt(repo_dir: Path, evidence_dir: Path) -> str | None:
    value = task_state(evidence_dir).get("implementation_attempt")
    return str(value) if value is not None else None


def ground_truth_implementation_cycle(repo_dir: Path, evidence_dir: Path) -> str | None:
    value = task_state(evidence_dir).get("implementation_cycle")
    return str(value) if value is not None else None


def ground_truth_change_cycle(repo_dir: Path, evidence_dir: Path) -> str | None:
    value = task_state(evidence_dir).get("change_cycle")
    return str(value) if value is not None else None


def ground_truth_resolved_review_cycles(repo_dir: Path, evidence_dir: Path) -> str | None:
    state = task_state(evidence_dir)
    value = state.get("review_cycle")
    if value is None:
        return None
    if state.get("status") == "reviewing":
        value = max(0, int(value) - 1)
    return str(value)


def ground_truth_review_state(repo_dir: Path, evidence_dir: Path) -> str | None:
    value = task_state(evidence_dir).get("status")
    return str(value) if value is not None else None


def ground_truth_acceptance_state(repo_dir: Path, evidence_dir: Path) -> str | None:
    value = (task_state(evidence_dir).get("user_acceptance") or {}).get("status")
    return str(value) if value is not None else None


def ground_truth_provenance_generated_at(repo_dir: Path, evidence_dir: Path) -> str | None:
    path = evidence_dir / "provenance.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8")).get("generated_at")
    return str(value) if value is not None else None


def ground_truth_head_revision(repo_dir: Path, evidence_dir: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def ground_truth_integration_state(repo_dir: Path, evidence_dir: Path) -> str | None:
    result = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo_dir, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        return None
    return "feature_worktree_only" if result.stdout.strip() else "clean_worktree"


GROUND_TRUTH = {
    "unit-tests": ground_truth_unit_tests,
    "e2e-tests": ground_truth_e2e_tests,
    "characterization-tests": ground_truth_characterization_tests,
    "context-spec-cases": ground_truth_context_spec_cases,
    "characterization-baseline": ground_truth_characterization_baseline,
    "architecture": ground_truth_architecture,
    "provenance-inventory": ground_truth_provenance_inventory,
    "baseline-unit-tests": ground_truth_baseline_unit_tests,
    "implementation-attempt": ground_truth_implementation_attempt,
    "implementation-cycle": ground_truth_implementation_cycle,
    "change-cycle": ground_truth_change_cycle,
    "resolved-review-cycles": ground_truth_resolved_review_cycles,
    "review-state": ground_truth_review_state,
    "acceptance-state": ground_truth_acceptance_state,
    "provenance-generated-at": ground_truth_provenance_generated_at,
    "head-revision": ground_truth_head_revision,
    "integration-state": ground_truth_integration_state,
}

MANDATORY_TAGS = frozenset(GROUND_TRUTH)


def freshness_errors(implementation: dict, repo_dir: Path, evidence_dir: Path) -> list[str]:
    errors: list[str] = []
    tags = collect_tags(implementation)
    current_attempt = ground_truth_implementation_attempt(repo_dir, evidence_dir)
    if current_attempt is not None:
        for text in collect_current_attempt_claims(implementation, current_attempt):
            for name, value in TAG_PATTERN.findall(text):
                tags.setdefault(name, []).append(value)
            if re.search(r"\bunit\b", text, re.IGNORECASE) or "--config jest.config.js" in text:
                for suites, tests in UNIT_INVENTORY_PATTERN.findall(text):
                    tags.setdefault("unit-tests", []).append(f"{suites} suites / {tests} tests")
            for modules, dependencies in ARCHITECTURE_INVENTORY_PATTERN.findall(text):
                tags.setdefault("architecture", []).append(
                    f"{modules} modules / {dependencies} dependencies"
                )
            for inputs, artifacts in PROVENANCE_INVENTORY_PATTERN.findall(text):
                tags.setdefault("provenance-inventory", []).append(
                    f"{inputs} inputs / {artifacts} artifacts"
                )

    for name in sorted(MANDATORY_TAGS - tags.keys()):
        errors.append(f"mandatory [{name}] fact is absent from current implementation evidence")

    for name, values in tags.items():
        distinct = sorted(set(values))
        if len(distinct) > 1:
            errors.append(
                f"[{name}] is claimed with {len(distinct)} different values in the same "
                f"implementation.json evidence/handoff text: {distinct} -- a stale/superseded "
                "claim must be removed, not left alongside the current one"
            )

    for name, compute in GROUND_TRUTH.items():
        truth = compute(repo_dir, evidence_dir)
        if truth is None:
            errors.append(f"[{name}] ground truth could not be computed from authoritative state")
            continue
        claimed = sorted(set(tags.get(name, [])))
        matches = claimed == [truth]
        if name == "review-state" and claimed == ["prepared"] and truth == "reviewing":
            matches = True
        if not matches:
            errors.append(
                f"[{name}] evidence claims {claimed} but the authoritative artifact currently "
                f"shows {truth!r}"
            )
    return errors


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: check_evidence_freshness.py <implementation.json> <repo-dir> <evidence-dir>")
        return 2
    implementation_path = Path(sys.argv[1]).resolve()
    repo_dir = Path(sys.argv[2]).resolve()
    evidence_dir = Path(sys.argv[3]).resolve()
    implementation = json.loads(implementation_path.read_text(encoding="utf-8"))

    tags = collect_tags(implementation)
    errors = freshness_errors(implementation, repo_dir, evidence_dir)

    if errors:
        print("Acceptance evidence freshness check FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Acceptance evidence freshness check PASSED: {len(tags)} tracked fact tag(s), no drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
