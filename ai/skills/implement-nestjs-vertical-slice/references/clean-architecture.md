# Clean Architecture completion matrix

For each relevant row, record a concrete file or `not applicable` with a reason:

| Layer | Required evidence |
|---|---|
| Domain | Entity/value object, invariants, domain errors and repository contract |
| Application | Use case, input/output contract, ports and transaction boundary |
| Infrastructure | Adapter, mapper, ORM entity/external client and error translation |
| Wiring | Injection-token provider, module imports/providers/exports and public API |
| Persistence | Migration, foreign keys, uniqueness/indexes and rollback behavior |
| Presentation | Controller/DTO/validation/auth guard and stable response contract |
| Verification | Unit tests, adapter integration tests and relevant E2E tests |

Check imports against module boundaries. Other modules must consume public APIs or application contracts, never internal ORM entities or source paths.
