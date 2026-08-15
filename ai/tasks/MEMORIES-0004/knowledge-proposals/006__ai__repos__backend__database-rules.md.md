# Proposed update

Target: `ai/repos/backend/database-rules.md`

Document the transaction-boundary convention for multi-statement aggregate-replace methods (e.g. 'save aggregate, then delete+reinsert child rows', seen in `TypeOrmProductRepository.saveWithVariantsAndCatalogLinks`/`TypeOrmCardTemplateRepository.saveWithCatalogLinks`): the repository never opens the transaction itself — it only checks `TypeOrmQueryRunnerContext.get()` via `repositoryFor()`-style accessors. The CALLING use case wraps the whole call in `UnitOfWork.withTransaction(...)` (see `SeedProductsUseCase.seedOne`, matching `CreateAccountUseCase`). Any such delete+reinsert method called without that wrapper is not atomic — verify with an e2e test forcing a mid-sequence unique-constraint violation (two rows sharing a unique key in one insert batch is a reliable, self-contained way to do this) and asserting the aggregate row was not committed.


