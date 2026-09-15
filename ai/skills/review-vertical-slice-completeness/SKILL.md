---
name: review-vertical-slice-completeness
description: Review an implementation for end-to-end vertical-slice completeness and evidence. Use for independent code review when requirements may span domain, application, persistence, dependency injection, migrations, presentation, frontend integration or tests, especially before declaring a Jira implementation technically ready.
---

# Review vertical-slice completeness

1. Read effective requirements, execution plan, required skills, handoff, deterministic checks and the complete diff.
2. Build an evidence matrix using [evidence-matrix.md](references/evidence-matrix.md).
3. Trace all changed contracts to runtime implementations and all acceptance criteria to tests or verified evidence.
4. Apply [review-gates.md](references/review-gates.md); never infer completeness from file names or compilation alone.
5. Run `scripts/build_evidence_matrix.py <execution-plan.json> <implementation.json> --evidence-dir ai/tasks/<id>/evidence` to identify handoff coverage gaps before returning a verdict. When a slice declares `evidence_requirements` for a criterion, evidence claiming less than the required `min_test_level`, or missing a real-infra artifact for a declared `requires_real_infra`, is reported as missing even if its status is `passed`.
6. Return concrete findings for missing layers, wiring, migrations, constraints, security cases or reachable tests.

Pass only when every effective criterion is covered and all required runtime paths are wired and validated.
