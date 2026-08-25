// [LEGACY correlation semantics — origin/master@c8ca980672459e9eccbb03396a9c246448d1ead6]
// MEMORIES-0006 fix-request-review-002 finding #3 — reproducible characterization.
//
// `bullmq.publisher.ts` itself is NOT in this migration's changed-file set (its source is
// byte-identical before and after — it only ever calls `CorrelationContext.correlationId()`).
// Rather than assert that fact and skip characterization (the finding rightly rejected that
// shortcut), this spec imports the REAL, currently-live, unmodified `BullMqPublisher` from the
// worktree and executes it against the frozen legacy (AsyncLocalStorage-backed) `CorrelationContext`
// instead of the migrated (CLS-backed) one — see jest.legacy-characterization.config.js, which maps
// `@memories/platform/observability` to `../legacy-fixtures/observability-shim.ts` only for this
// spec. Identical assertions against the migrated `CorrelationContext` already run as part of the
// standing `npm test` (`libs/platform/queue/test/bullmq.publisher.spec.ts`).
import { CorrelationContext } from '@memories/platform/observability';

// eslint-disable-next-line import/no-relative-packages -- reaches into the live worktree source
// deliberately: this is the actual production file, not a copy, run against a swapped dependency.
import { BullMqPublisher } from '../../../../../../worktrees/MEMORIES-0006/backend/libs/platform/queue/src/bullmq/bullmq.publisher';

function buildPublisher(addMock: jest.Mock) {
  const queueFactory = { getQueue: jest.fn().mockReturnValue({ add: addMock }) };
  const queueRegistry = {
    queueNameForJob: jest.fn().mockReturnValue('media'),
    get: jest.fn().mockReturnValue({ name: 'media', overrides: undefined }),
  };
  const configService = {
    getOrThrow: jest.fn().mockReturnValue({
      defaultJobOptions: {
        attempts: 3,
        backoffMs: 2000,
        removeOnComplete: 1000,
        removeOnFail: 5000,
      },
    }),
  };

  return new BullMqPublisher(queueFactory as never, queueRegistry as never, configService as never);
}

describe('[LEGACY correlation semantics] BullMqPublisher correlationId precedence (MEMORIES-0006 AC13)', () => {
  it("defaults the envelope's correlationId to the ambient HTTP request's correlation ID", async () => {
    const add = jest.fn().mockResolvedValue({ id: 'job-1' });
    const publisher = buildPublisher(add);

    await CorrelationContext.run({ requestId: 'req-1', correlationId: 'corr-from-http' }, () =>
      publisher.publish('media.generate-thumbnail.v1', {}),
    );

    const [, envelope] = add.mock.calls[0];
    expect(envelope.correlationId).toBe('corr-from-http');
  });

  it('falls back to a generated correlationId when publishing outside any HTTP request', async () => {
    const add = jest.fn().mockResolvedValue({ id: 'job-1' });
    const publisher = buildPublisher(add);

    await publisher.publish('media.generate-thumbnail.v1', {});

    const [, envelope] = add.mock.calls[0];
    expect(typeof envelope.correlationId).toBe('string');
    expect(envelope.correlationId.length).toBeGreaterThan(0);
  });

  it('an explicit options.correlationId overrides the ambient HTTP correlation id', async () => {
    const add = jest.fn().mockResolvedValue({ id: 'job-1' });
    const publisher = buildPublisher(add);

    await CorrelationContext.run({ requestId: 'req-1', correlationId: 'corr-from-http' }, () =>
      publisher.publish(
        'media.generate-thumbnail.v1',
        {},
        { correlationId: 'corr-explicit-override' },
      ),
    );

    const [, envelope] = add.mock.calls[0];
    expect(envelope.correlationId).toBe('corr-explicit-override');
  });
});
