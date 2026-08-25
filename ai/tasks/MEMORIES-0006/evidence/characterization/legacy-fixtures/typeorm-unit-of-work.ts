import { AsyncLocalStorage } from 'node:async_hooks';

import { UnitOfWork } from '@memories/shared/kernel';
import { Injectable } from '@nestjs/common';
import { DataSource, QueryRunner } from 'typeorm';

/**
 * AsyncLocalStorage-backed so concurrent requests each see only their own active transaction's
 * QueryRunner. A plain mutable field (the original scaffolded shape) would be a shared singleton
 * across every concurrent request: one request's `withTransaction` call would silently overwrite
 * another's in-flight QueryRunner, corrupting whichever transaction started first. This had never
 * been exercised by any real repository until the confirm-upload/outbox work needed it for real.
 */
@Injectable()
export class TypeOrmQueryRunnerContext {
  private static readonly storage = new AsyncLocalStorage<QueryRunner>();

  run<TResult>(queryRunner: QueryRunner, callback: () => Promise<TResult>): Promise<TResult> {
    return TypeOrmQueryRunnerContext.storage.run(queryRunner, callback);
  }

  get(): QueryRunner | undefined {
    return TypeOrmQueryRunnerContext.storage.getStore();
  }
}

@Injectable()
export class TypeOrmUnitOfWork implements UnitOfWork {
  constructor(
    private readonly dataSource: DataSource,
    private readonly context: TypeOrmQueryRunnerContext,
  ) {}

  async withTransaction<TResult>(work: () => Promise<TResult>): Promise<TResult> {
    // Reentrant: a use case that calls another use case which itself opens its own
    // `withTransaction` (e.g. `RegisterUseCase` wrapping `CreateAccountUseCase` for atomic
    // self-registration) must not open a second, independent connection/transaction that could
    // commit or roll back on its own — it joins the already-active one and lets the outer call
    // own commit/rollback, exactly like every real nested-unit-of-work pattern.
    if (this.context.get()) {
      return work();
    }

    const queryRunner = this.dataSource.createQueryRunner();
    // `connect()` checks a connection out of the pool — once it resolves, that connection MUST
    // be released no matter what happens next, so everything from here on is wrapped in a
    // try/finally. `startTransaction()` used to run BEFORE this try/finally: if it rejected
    // (e.g. the connection dropped between connect() and BEGIN), the checked-out connection was
    // never released, leaking it from the pool — repeated failures during a degraded database
    // could exhaust the pool entirely and prevent any recovery.
    await queryRunner.connect();
    try {
      await queryRunner.startTransaction();
      try {
        const result = await this.context.run(queryRunner, work);
        await queryRunner.commitTransaction();
        return result;
      } catch (error) {
        // Only reached once `startTransaction()` has actually succeeded, so a transaction is
        // genuinely active here — calling `rollbackTransaction()` for a failure that happened
        // before any transaction started would itself be an invalid operation.
        await queryRunner.rollbackTransaction();
        throw error;
      }
    } finally {
      await queryRunner.release();
    }
  }
}
