{{#if memory_available}}
Persistent memory is ready for this task ({{memory_item_count}} item(s) recalled from
prior accepted work). Read `ai/tasks/{{task_id}}/memory/recall.md` for a normalized
summary before re-deriving context that may already be captured there. If anything in
it conflicts with `ai/shared/`, `ai/repos/`, or `ai/domains/`, the canonical files win.
{{else}}
Persistent memory is unavailable or disabled for this task ({{memory_reason}}). Use
normal repository discovery (CodeGraph if ready, otherwise grep/read) instead.
{{/if}}
