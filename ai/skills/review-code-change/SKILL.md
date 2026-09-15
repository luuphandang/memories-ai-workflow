---
name: review-code-change
description: Perform independent, evidence-backed code review of a complete implementation diff. Use when Codex reviews a pull request, worktree, change cycle or implementation handoff and must derive a risk-based test matrix from effective requirements and diff impact, execute full or delta review passes, classify findings, and provide actionable remediation guidance without modifying source code.
---

# Review code change

1. Establish the review contract before inspecting results:
   - Read repository instructions, effective requirements, active change request, context lock and review mode.
   - Treat implementer handoff and prior validation as claims to verify, not proof.
   - Keep review read-only unless the user explicitly asks for fixes.
2. Inventory every changed and untracked implementation file plus direct dependencies. In a full review, use the complete diff; in a delta review, use the latest correction, affected diff and direct dependencies.
3. Build `test_matrix` before trusting existing tests. Derive cases independently from both effective requirements and diff/blast-radius analysis by following [test-matrix.md](references/test-matrix.md).
4. Complete the required passes in [review-passes.md](references/review-passes.md). Do not stop after the first defect; collect findings across all required passes and report once.
5. Retest prior findings against current code and current-cycle evidence. Never use an older cycle's passing result as proof for the current cycle. Give every finding in `findings` a stable `finding_id` (e.g. `repo:file:severity:short-slug`); when reporting `review_coverage.prior_findings`, reuse the same `finding_id` the finding had in the cycle that first raised it — the orchestrator's ledger (`ai/tasks/<id>/review-history/cycle-*.json`, listed in the review prompt) records which ids from the immediately preceding cycle must be retested here.
6. Classify findings and write remediation using [findings-and-verdicts.md](references/findings-and-verdicts.md). Give every blocking finding an outcome-focused approach, affected code locations, tests and objective `done_when` checks.
7. Validate the completed JSON artifact:

   ```bash
   python3 ai/skills/review-code-change/scripts/validate_review.py <review.json> --mode <full|delta> --fail-on blocker,major --history-dir ai/tasks/<id>/review-history
   ```

8. Return the requested review format. For this repository, return only JSON matching `ai/schemas/review.schema.json`.

Return `blocked` when required coverage cannot be completed. Return `changes_requested` only after completing coverage and collecting the full current finding set. Return `pass` only when the applicable gates are satisfied; a delta pass never replaces the final full review.
