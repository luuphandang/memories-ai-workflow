# Independent review request — AI token optimization workflow

Review the recent AI orchestration changes in this repository. Do not modify any
file. Return findings only after completing the whole review.

## Goal

Verify that the workflow reduces token consumption without weakening implementation,
validation, review, security, acceptance-evidence, or user-acceptance gates.

## Files in scope

- `ai/bin/lib/ai_common.py`
- `ai/bin/run-claude`
- `ai/bin/run-task`
- `ai/bin/validate`
- `ai/bin/run-codex-review`
- `ai/bin/request-fixes`
- `ai/bin/metrics`
- `ai/bin/ai`
- `ai/bin/README.md`
- `ai/config/codex/review.config.toml`
- `ai/tests/agent_gate_pipeline.py`
- `ai/tests/fakes/fake_claude.py`
- `user_manual.md`

Inspect the actual Git diff for these files and the directly dependent schemas,
templates, fixtures, and lifecycle scripts. Preserve unrelated existing workspace
changes and do not treat them as part of this implementation.

## Intended behavior to verify

1. Each Claude implementation session handles one runnable execution-plan slice.
2. Sessions are bounded by `AI_MAX_TURNS`; context warning and breach thresholds are
   recorded from `AI_WARN_CONTEXT_TOKENS` and `AI_MAX_CONTEXT_TOKENS`.
3. A compact per-slice context bundle encourages progressive disclosure.
4. Completed slice evidence and handoff information survive later slice sessions.
5. Quick validation runs between slices; full validation is mandatory before review.
6. Validation and delivery-gate failures create concise fix requests referencing the
   complete artifact instead of embedding excessive output.
7. Safe corrections may use delta review; sensitive changes automatically escalate
   to full review.
8. Delta pass is followed by a final full review before report/user acceptance.
9. Codex reasoning effort is selected according to risk.
10. Metrics include normal input, cache creation/read, output, turns, cost, review
    mode, and per-slice totals when the underlying CLI exposes them.
11. Interrupted sessions resume only for the same slice; ordinary slice transitions
    start fresh sessions.
12. Existing commands remain backward compatible where documented.

## Required review passes

- Trace `run-task` state transitions for multi-slice success, quick-validation
  failure, implementation failure, review correction, delta pass, final-full-review
  failure, interruption/resume, and max-attempt exhaustion.
- Check execution-plan status selection and dependency handling, including completed
  plans receiving post-review corrections.
- Check whether partial-slice handoffs can pass or accidentally bypass final delivery
  gates.
- Check that full validation cannot be confused with quick or dry-run evidence.
- Check delta-review safety classification and whether its reduced coverage can allow
  regressions to pass.
- Check CLI argument compatibility with real Claude Code and Codex CLIs.
- Check metric extraction and aggregation for missing, null, cached, and legacy usage
  fields.
- Check documentation against actual behavior.
- Run deterministic tests that are safe and relevant; do not call real AI services.

## Output format

Write the review in Vietnamese using this structure:

1. Verdict: `PASS`, `CHANGES_REQUESTED`, or `BLOCKED`.
2. Findings ordered by severity: blocker, major, minor, note.
3. For every finding include file, line, concrete evidence, impact, and expected fix.
4. Test/inspection coverage completed.
5. Residual risks and any behavior that could not be verified.

Do not implement fixes. Do not commit, push, change branches, modify worktrees, read
secrets, or call Claude/Codex recursively.
