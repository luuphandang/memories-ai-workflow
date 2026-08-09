# Contract manifest

Place `openapi-contracts.json` at the repository worktree root:

```json
{
  "operations": [
    {
      "method": "post",
      "path": "/api/v1/auth/register",
      "source": "libs/modules/identity-access/src/presentation/http/auth.controller.ts",
      "handler": "register",
      "required_statuses": [201, 400, 403, 409, 429],
      "contract_test": "apps/api/test/openapi-contract.spec.ts"
    }
  ]
}
```

For each operation:

- `source` points to the controller containing the handler.
- `handler` is the controller method name.
- `required_statuses` lists every documented runtime outcome.
- `contract_test` points to a test that builds/exports the real OpenAPI document and asserts the operation.

The deterministic checker verifies that the handler has explicit Swagger response metadata for every status and that the declared contract test exists. The test itself must verify the generated document; reviewers must reject placeholder tests.
