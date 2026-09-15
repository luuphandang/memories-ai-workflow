#!/usr/bin/env python3
"""Report repeated raw visual values and page-local root token blocks.

AST-scoped via ai/tools/source-analysis (ts-morph for TS/TSX, PostCSS for CSS) instead of
plain-text regex, so a color literal's context (styling vs. token-definition vs.
business-data, e.g. a named swatch/palette catalog) is known before it counts toward the
raw-color-repetition rule -- a hex value repeated across a mock/fixture catalog (typed
business data) is not the same defect as one hand-copied across component styles. See
ai/tools/source-analysis/src/design-system.ts for the classifier.

Two modes:
  - no `--baseline`: report every current violation (used to inspect state, or before an
    official baseline exists).
  - `--baseline <path>`: delta gate -- fail only on a violation absent from the baseline or
    whose occurrence count increased; baseline debt that didn't grow is reported but not
    failed. A `ruleset_version` mismatch always fails and asks for a regenerated baseline.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess

ANALYSIS_ROOT = Path(__file__).resolve().parents[3] / "tools" / "source-analysis"
CLI_ENTRY = ANALYSIS_ROOT / "dist" / "cli.js"
RULESET_VERSION = "1"
COUNTED_CONTEXTS = {"styling", "unknown"}


def run_analyzer(root: Path) -> dict:
    if not CLI_ENTRY.is_file():
        raise SystemExit(
            f"Missing {CLI_ENTRY}.\nNext: (cd {ANALYSIS_ROOT} && npm install && npm run build)"
        )
    result = subprocess.run(
        ["node", str(CLI_ENTRY), "design-system", str(root)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"source-analysis design-system analyzer failed:\n{result.stdout}")
    return json.loads(result.stdout)


def compute_violations(analysis: dict) -> list[dict]:
    """Current violations as {fingerprint, rule, detail, count?}, deterministically ordered."""
    counts = Counter(
        entry["value"] for entry in analysis["color_entries"] if entry["context"] in COUNTED_CONTEXTS
    )
    violations: list[dict] = []
    for value, count in sorted(counts.items()):
        if count >= 4:
            violations.append({
                "fingerprint": f"repeated-color:{value}",
                "rule": "raw-color-repetition",
                "detail": f"raw color repeated >= 4 times: {value} ({count})",
                "count": count,
            })
    for block in sorted(analysis["root_blocks"], key=lambda item: item["file"]):
        violations.append({
            "fingerprint": f"root-block:{block['file']}",
            "rule": "page-local-root-block",
            "detail": f"page-local :root token block: {block['file']}",
        })
    return violations


def run_delta_gate(violations: list[dict], baseline_path: Path) -> int:
    if not baseline_path.is_file():
        print(f"Design-system usage FAILED\n- baseline file not found: {baseline_path} (run generate_baseline.py)")
        return 1
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if baseline.get("ruleset_version") != RULESET_VERSION:
        print(
            "Design-system usage FAILED\n"
            f"- baseline ruleset_version {baseline.get('ruleset_version')!r} does not match "
            f"current {RULESET_VERSION!r}; regenerate with generate_baseline.py"
        )
        return 1

    baseline_by_fp = {item["fingerprint"]: item for item in baseline.get("violations", [])}
    current_fps = {v["fingerprint"] for v in violations}
    errors: list[str] = []
    for v in violations:
        prior = baseline_by_fp.get(v["fingerprint"])
        if prior is None:
            errors.append(f"new violation: {v['detail']}")
        elif "count" in v and v["count"] > prior.get("count", 0):
            errors.append(f"occurrence increased ({prior.get('count')} -> {v['count']}): {v['detail']}")
    resolved = sorted(fp for fp in baseline_by_fp if fp not in current_fps)

    if errors:
        print("Design-system usage FAILED (delta gate)")
        print("\n".join(f"- {item}" for item in errors))
        return 1
    print(
        f"Design-system usage PASSED (delta gate): {len(violations)} baseline violation(s) "
        f"carried, {len(resolved)} resolved"
    )
    if resolved:
        print("Resolved since baseline (consider regenerating): " + ", ".join(resolved))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="frontend worktree path (never pass a monorepo root spanning backend)")
    parser.add_argument("--baseline", type=Path, default=None, help="ai/repos/<repo>/baselines/design-system.json")
    args = parser.parse_args()

    analysis = run_analyzer(args.root)
    violations = compute_violations(analysis)

    if args.baseline is not None:
        return run_delta_gate(violations, args.baseline)

    if violations:
        print("Design-system usage FAILED")
        print("\n".join(f"- {v['detail']}" for v in violations))
        return 1
    print("Design-system usage PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
