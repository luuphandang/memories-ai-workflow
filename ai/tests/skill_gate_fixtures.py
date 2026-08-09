#!/usr/bin/env python3
"""Forward-test deterministic skill checks against isolated raw fixtures."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


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
    print("Skill gate fixtures PASSED")


if __name__ == "__main__":
    main()
