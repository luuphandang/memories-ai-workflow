Memory publish summary for {{task_id}} (change cycle {{change_cycle}}):

- Published: {{published_count}} entr(y/ies) — {{published_categories}}
- Superseded: {{superseded_count}} prior entr(y/ies)
- Errors: {{error_count}}

This is an operator-facing summary only (printed by `ai/bin/memory-publish`), not a
prompt fed to Claude or Codex — neither agent calls `memory-publish` or reads its output.
