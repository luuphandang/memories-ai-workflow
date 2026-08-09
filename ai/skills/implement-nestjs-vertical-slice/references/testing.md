# Testing checks

- Domain tests cover invariants and state transitions.
- Use-case tests cover happy path, authorization, failures and transaction behavior.
- Repository integration tests cover mapping, constraints and queries against PostgreSQL.
- Module tests resolve providers through Nest's container.
- E2E tests cover reachable HTTP behavior, guards, DTO validation and response safety.
- Regression tests fail before the fix and exercise the real boundary involved.

Use configured project commands. Do not substitute mocks for required infrastructure validation.
