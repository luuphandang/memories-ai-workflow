# Risk-driven test matrix

Build the matrix before reading test results as pass evidence. Use two independent discovery lanes:

1. Requirement lane: map every effective acceptance criterion, invariant and active user correction to observable behavior.
2. Diff-impact lane: inspect every changed symbol, caller/callee, state transition, contract, persistence boundary and adjacent behavior that can regress.

Use explicit source labels such as `requirement: AC3` and `diff-impact: src/orders/create.ts#createOrder`. A full review must contain both lanes. A delta review must contain diff-impact cases plus corrected-behavior and regression cases.

Cover these case families when applicable:

- happy path and expected state transition;
- validation/error path and failure cleanup;
- boundary values, empty state and pagination/range limits;
- regression of adjacent behavior and prior findings;
- authorization, privilege and sensitive-data boundaries;
- concurrency, retry, idempotency and transaction rollback;
- API, database, event, client and backward compatibility;
- accessibility, responsive states and browser behavior for UI changes.

Each `test_matrix` entry must include:

```json
{
  "id": "TM-001",
  "sources": ["requirement: AC3", "diff-impact: src/orders/create.ts#createOrder"],
  "target": "Order creation transaction",
  "test_level": "integration",
  "scenario": "Payment persistence fails after the order row is inserted",
  "expected_result": "The transaction rolls back and no partial order remains",
  "status": "passed",
  "evidence": "tests/orders/create-order.spec.ts:88; command ... passed"
}
```

Use only `passed`, `failed`, `missing` or `not_applicable`:

- Mark `passed` or `failed` only with concrete current-cycle evidence.
- Mark an absent or insufficient test `missing`; do not infer coverage from a neighboring test.
- Use `not_applicable` only with a specific reason.
- Set `validation_assessment.passed` to false whenever a required case is `missing` or `failed`.

Do not copy the implementer's test list as the matrix. First derive expected cases, then reconcile them against the actual tests and results.
