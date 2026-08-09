---
name: verify-openapi-contract
description: Implement or review HTTP API changes whose Swagger/OpenAPI contract must match runtime behavior, including request schemas, success responses, validation errors, authorization failures, conflicts, rate limits, and generated clients. Use whenever a task adds or changes controllers, public endpoints, Swagger decorators, OpenAPI export, API error envelopes, or API-client generation.
---

# Verify an OpenAPI contract

1. Enumerate every reachable HTTP outcome for each changed operation before coding. Include framework/global behavior such as validation, authentication, authorization, conflicts and throttling.
2. Create or update `<worktree>/openapi-contracts.json` using [manifest.md](references/manifest.md). Treat it as the minimum public contract, not a substitute for decorators or tests.
3. Ensure request DTOs, successful response DTOs and the real global error envelope are represented in Swagger. A runtime exception filter does not add OpenAPI metadata by itself.
4. Add explicit response metadata for every status in the manifest. Reuse one shared error DTO when the runtime envelope is shared.
5. Add a contract test that builds or exports the real OpenAPI document and asserts the operation path, method, request schema, success schema and every required response status. Runtime E2E tests alone are insufficient.
6. Run `scripts/check_openapi_contract.py <worktree>` before completion.
7. Record the checker and generated-document test as acceptance evidence. Do not mark an OpenAPI criterion passed merely because DTO decorators or a global exception filter exist.

If an outcome is deliberately undocumented, record the product decision in the effective requirements; do not silently remove it from the manifest.
