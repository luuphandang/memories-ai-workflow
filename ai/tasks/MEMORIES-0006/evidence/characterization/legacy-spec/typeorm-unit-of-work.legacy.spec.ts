// [LEGACY origin/master@c8ca980672459e9eccbb03396a9c246448d1ead6]
// MEMORIES-0006 fix-request-review-002 finding #3 — reproducible characterization.
//
// Imports the frozen, byte-identical `TypeOrmQueryRunnerContext`/`TypeOrmUnitOfWork` fixture
// (AsyncLocalStorage-backed) and re-runs every assertion meaningful pre-migration. Sibling-CLS-
// namespace preservation and "works with no active parent CLS root" have no legacy equivalent
// (there was no shared CLS root at all) — see characterization-baseline.md.
import {
  TypeOrmQueryRunnerContext,
  TypeOrmUnitOfWork,
} from '../legacy-fixtures/typeorm-unit-of-work';

function fakeQueryRunner(id: string) {
  return {
    id,
    connect: jest.fn().mockResolvedValue(undefined),
    startTransaction: jest.fn().mockResolvedValue(undefined),
    commitTransaction: jest.fn().mockResolvedValue(undefined),
    rollbackTransaction: jest.fn().mockResolvedValue(undefined),
    release: jest.fn().mockResolvedValue(undefined),
  };
}

describe('[LEGACY] TypeOrmQueryRunnerContext', () => {
  it('returns undefined outside of any withTransaction call', () => {
    const context = new TypeOrmQueryRunnerContext();

    expect(context.get()).toBeUndefined();
  });

  it("isolates concurrent transactions — one never sees the other's QueryRunner", async () => {
    const context = new TypeOrmQueryRunnerContext();
    const runnerA = fakeQueryRunner('A');
    const runnerB = fakeQueryRunner('B');

    const seenByA: unknown[] = [];
    const seenByB: unknown[] = [];

    const taskA = context.run(runnerA as never, async () => {
      seenByA.push(context.get());
      await new Promise((resolve) => setTimeout(resolve, 20));
      seenByA.push(context.get());
    });
    const taskB = context.run(runnerB as never, async () => {
      seenByB.push(context.get());
      await new Promise((resolve) => setTimeout(resolve, 5));
      seenByB.push(context.get());
    });

    await Promise.all([taskA, taskB]);

    expect(seenByA).toEqual([runnerA, runnerA]);
    expect(seenByB).toEqual([runnerB, runnerB]);
  });
});

describe('[LEGACY] TypeOrmUnitOfWork', () => {
  function buildUnitOfWork(queryRunner: ReturnType<typeof fakeQueryRunner>) {
    const dataSource = { createQueryRunner: jest.fn().mockReturnValue(queryRunner) };
    const context = new TypeOrmQueryRunnerContext();
    const unitOfWork = new TypeOrmUnitOfWork(dataSource as never, context);
    return { unitOfWork, context, dataSource };
  }

  it('commits and makes the QueryRunner available to work() via the context', async () => {
    const queryRunner = fakeQueryRunner('A');
    const { unitOfWork, context } = buildUnitOfWork(queryRunner);
    let seenInsideWork: unknown;

    const result = await unitOfWork.withTransaction(async () => {
      seenInsideWork = context.get();
      return 'ok';
    });

    expect(result).toBe('ok');
    expect(seenInsideWork).toBe(queryRunner);
    expect(queryRunner.commitTransaction).toHaveBeenCalled();
    expect(queryRunner.rollbackTransaction).not.toHaveBeenCalled();
    expect(queryRunner.release).toHaveBeenCalled();
    expect(context.get()).toBeUndefined();
  });

  it('rolls back and still releases the connection when work() throws', async () => {
    const queryRunner = fakeQueryRunner('A');
    const { unitOfWork } = buildUnitOfWork(queryRunner);

    await expect(
      unitOfWork.withTransaction(async () => {
        throw new Error('boom');
      }),
    ).rejects.toThrow('boom');

    expect(queryRunner.rollbackTransaction).toHaveBeenCalled();
    expect(queryRunner.commitTransaction).not.toHaveBeenCalled();
    expect(queryRunner.release).toHaveBeenCalled();
  });

  it('still releases the connection when startTransaction() itself fails, instead of leaking it from the pool', async () => {
    const queryRunner = fakeQueryRunner('A');
    queryRunner.startTransaction.mockRejectedValueOnce(new Error('connection reset mid-BEGIN'));
    const { unitOfWork } = buildUnitOfWork(queryRunner);

    await expect(unitOfWork.withTransaction(async () => 'unreachable')).rejects.toThrow(
      'connection reset mid-BEGIN',
    );

    expect(queryRunner.release).toHaveBeenCalled();
    expect(queryRunner.rollbackTransaction).not.toHaveBeenCalled();
    expect(queryRunner.commitTransaction).not.toHaveBeenCalled();
  });

  it('joins an already-active transaction instead of opening a second connection, and lets the outer call own commit/rollback', async () => {
    const queryRunner = fakeQueryRunner('outer');
    const { unitOfWork, dataSource } = buildUnitOfWork(queryRunner);

    const result = await unitOfWork.withTransaction(async () =>
      unitOfWork.withTransaction(async () => 'inner-result'),
    );

    expect(result).toBe('inner-result');
    expect(dataSource.createQueryRunner).toHaveBeenCalledTimes(1);
    expect(queryRunner.commitTransaction).toHaveBeenCalledTimes(1);
    expect(queryRunner.release).toHaveBeenCalledTimes(1);
  });

  it('rolls back the single outer transaction when a nested withTransaction call throws', async () => {
    const queryRunner = fakeQueryRunner('outer');
    const { unitOfWork } = buildUnitOfWork(queryRunner);

    await expect(
      unitOfWork.withTransaction(async () =>
        unitOfWork.withTransaction(async () => {
          throw new Error('inner failure');
        }),
      ),
    ).rejects.toThrow('inner failure');

    expect(queryRunner.rollbackTransaction).toHaveBeenCalledTimes(1);
    expect(queryRunner.commitTransaction).not.toHaveBeenCalled();
    expect(queryRunner.release).toHaveBeenCalledTimes(1);
  });
});
