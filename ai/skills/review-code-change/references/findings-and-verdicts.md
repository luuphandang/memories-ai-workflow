# Findings and verdicts

Report only defects or risks supported by specific evidence. Classify severity by impact:

- `blocker`: security or data-loss risk, non-runnable implementation, or critical architectural failure.
- `major`: incorrect behavior, material regression, runtime failure, or missing test for a critical behavior.
- `minor`: lower-impact edge case or maintainability defect.
- `note`: optional improvement that does not fail acceptance.

Each finding must identify severity, repository, file and line when available, concise title, evidence and expected outcome. For every severity configured in `fail_on`, add:

```json
{
  "implementation_guidance": {
    "approach": "Explain the cause and a viable outcome-focused correction.",
    "code_locations": ["src/path.ts#symbol"],
    "tests": ["Add or update the regression test and name the scenario."],
    "done_when": ["State an objective observable completion condition."]
  }
}
```

Do not prescribe a single implementation when several designs satisfy the invariant. Make `done_when` independently verifiable.

Apply verdicts as follows:

- `blocked`: review coverage or required evidence is incomplete.
- `changes_requested`: coverage is complete and one or more configured blocking findings remain.
- `pass`: coverage is complete, no configured blocking finding remains, required matrix cases pass and core acceptance criteria are verified.

A pass means technically ready for the workflow's next gate, not user acceptance or task completion. A delta pass never authorizes final acceptance.
