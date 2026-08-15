#!/usr/bin/env python3
"""Forward-test deterministic skill checks against isolated raw fixtures."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "skill-checks"


def check(script: Path, fixture: str, expected: int) -> None:
    result = subprocess.run([sys.executable, str(script), str(FIXTURES / fixture)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.returncode != expected:
        raise AssertionError(f"{script.name} on {fixture}: expected {expected}, got {result.returncode}\n{result.stdout}")


def main() -> None:
    nest = ROOT / "skills" / "implement-nestjs-vertical-slice" / "scripts"
    auth = ROOT / "skills" / "implement-auth-security-change" / "scripts" / "check_auth_invariants.py"
    design = ROOT / "skills" / "establish-frontend-design-system" / "scripts" / "check_design_system_usage.py"
    migration = ROOT / "skills" / "migrate-prototype-nextjs-page" / "scripts" / "check_prototype_migration.py"
    fidelity = ROOT / "skills" / "review-frontend-ui-fidelity" / "scripts" / "check_fidelity_matrix.py"
    provenance = ROOT / "skills" / "validate-evidence-provenance" / "scripts" / "check_provenance.py"
    invariants = ROOT / "skills" / "design-database-invariants" / "scripts" / "check_invariant_matrix.py"
    review = ROOT / "skills" / "review-code-change" / "scripts" / "validate_review.py"
    check(nest / "check_port_bindings.py", "missing-provider", 1)
    check(nest / "check_module_wiring.py", "missing-provider", 1)
    check(auth, "weak-auth-uniqueness", 1)
    check(nest / "check_port_bindings.py", "complete-slice", 0)
    check(nest / "check_module_wiring.py", "complete-slice", 0)
    check(auth, "complete-slice", 0)
    check(design, "frontend-design-fail", 1)
    check(design, "frontend-design-pass", 0)
    check(migration, "frontend-migration-fail", 1)
    check(migration, "frontend-migration-pass", 0)
    check(fidelity, "fidelity-fail/matrix.json", 1)
    check(fidelity, "fidelity-pass/matrix.json", 0)
    check(provenance, "provenance-fail/provenance.json", 1)
    check(provenance, "provenance-pass/provenance.json", 0)
    check(invariants, "invariant-fail.json", 1)
    check(invariants, "invariant-pass.json", 0)
    check_review_fixture(review)
    check_handoff_fixture()
    print("Skill gate fixtures PASSED")


def check_review_fixture(checker: Path) -> None:
    artifact = {
        "verdict": "pass",
        "review_coverage": {
            "review_passes": ["requirements", "diff", "architecture", "behavior", "tests", "security", "regression"],
            "changed_files": [{"file": "src/example.ts", "status": "reviewed"}],
            "risk_areas": [{"area": "authorization", "status": "not_applicable"}],
            "prior_findings": [],
            "completion_statement": True,
        },
        "test_matrix": [{
            "id": "TM-1",
            "sources": ["requirement: AC1", "diff-impact: src/example.ts#run"],
            "status": "passed",
            "evidence": "unit test passed",
        }],
        "validation_assessment": {"passed": True, "missing": []},
        "findings": [],
    }
    with tempfile.TemporaryDirectory(prefix="review-skill-") as temporary:
        path = Path(temporary) / "review.json"
        path.write_text(json.dumps(artifact), encoding="utf-8")
        result = subprocess.run([sys.executable, str(checker), str(path), "--mode", "full"], check=False)
        if result.returncode != 0:
            raise AssertionError("review checker rejected a complete artifact")
        artifact["test_matrix"][0]["status"] = "missing"
        artifact["test_matrix"][0]["evidence"] = ""
        path.write_text(json.dumps(artifact), encoding="utf-8")
        result = subprocess.run([sys.executable, str(checker), str(path), "--mode", "full"], check=False)
        if result.returncode != 1:
            raise AssertionError("review checker accepted a pass with missing coverage")


def check_handoff_fixture() -> None:
    checker = ROOT / "skills" / "verify-implementation-handoff" / "scripts" / "check_handoff.py"
    with tempfile.TemporaryDirectory(prefix="handoff-skill-") as temporary:
        root = Path(temporary)
        repo = root / "worktrees" / "TEST-1" / "backend"
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Fixture"], cwd=repo, check=True)
        (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
        (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (repo / "new.txt").write_text("new\n", encoding="utf-8")
        task_dir = root / "ai" / "tasks" / "TEST-1"
        task_dir.mkdir(parents=True)
        (task_dir / "task.yaml").write_text(
            "worktrees:\n  - repo: backend\n    path: worktrees/TEST-1/backend\n",
            encoding="utf-8",
        )
        handoff = {"repositories": [{"name": "backend", "changed_files": ["tracked.txt", "new.txt"]}]}
        (task_dir / "implementation.json").write_text(json.dumps(handoff), encoding="utf-8")
        result = subprocess.run([sys.executable, str(checker), str(task_dir)], check=False)
        if result.returncode != 0:
            raise AssertionError("handoff checker rejected exact paths")
        handoff["repositories"][0]["changed_files"][1] = "new.txt (annotated)"
        (task_dir / "implementation.json").write_text(json.dumps(handoff), encoding="utf-8")
        result = subprocess.run([sys.executable, str(checker), str(task_dir)], check=False)
        if result.returncode != 1:
            raise AssertionError("handoff checker accepted an annotated path")


if __name__ == "__main__":
    main()
