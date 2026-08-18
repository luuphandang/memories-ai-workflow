# Proposed update

Target: `ai/repos/backend/architecture.md`

TypeOrmUnitOfWork.withTransaction is now reentrant: if called while a transaction is already active on the current async context (TypeOrmQueryRunnerContext), it joins that transaction (just runs the callback) instead of opening a second, independent connection/transaction. This lets a use case that calls another transactional use case (e.g. RegisterUseCase wrapping CreateAccountUseCase) get one atomic operation for free by wrapping the whole flow in its own outer withTransaction — the inner use case's own withTransaction call needs no change. Every repository already resolves its query runner through the same TypeOrmQueryRunnerContext, so this composes transparently across module boundaries.


