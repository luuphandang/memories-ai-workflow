#!/usr/bin/env python3
"""Generate/regenerate the official design-system violation baseline for one repo.

Manual operator command, not run automatically by any pipeline -- creating an "official"
baseline is a deliberate act that should be reviewed before commit, not a side effect of a
task run. Run after ai/tools/source-analysis is built and check_design_system_usage.py's
classification has been reviewed as trustworthy for the target repo (see
workflow_issue.md #2's ordering: metrics -> AST rewrite (#3) -> baseline -> delta gate).

Usage:
  generate_baseline.py <repo-name> <frontend-worktree> [--output <path>]

<repo-name> is the ai/repos/<repo-name> this baseline belongs to (its own technical-debt
ledger); <frontend-worktree> is the actual directory to scan. Default output:
ai/repos/<repo-name>/baselines/design-system.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "bin"))
from lib.ai_common import AI_ROOT, skill_manifest  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_design_system_usage import RULESET_VERSION, compute_violations, run_analyzer  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repo", help="ai/repos/<repo> this baseline belongs to")
    parser.add_argument("worktree", type=Path, help="frontend worktree path to scan")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    output = args.output or (AI_ROOT / "repos" / args.repo / "baselines" / "design-system.json")
    analysis = run_analyzer(args.worktree)
    violations = compute_violations(analysis)
    baseline = {
        "repo": args.repo,
        "ruleset_version": RULESET_VERSION,
        # Covers the Python-wrapper skill directory only; the AST analyzer lives outside it
        # at ai/tools/source-analysis and is not included in this hash (see check comment).
        "implementation_hash": skill_manifest("establish-frontend-design-system")["sha256"],
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "violations": [
            {**item, "first_seen": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}
            for item in violations
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}: {len(violations)} violation(s) at ruleset_version={RULESET_VERSION}")
    for item in violations:
        print(f"  - {item['fingerprint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
