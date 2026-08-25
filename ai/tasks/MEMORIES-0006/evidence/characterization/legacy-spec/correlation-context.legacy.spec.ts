// [LEGACY origin/master@c8ca980672459e9eccbb03396a9c246448d1ead6]
// MEMORIES-0006 fix-request-review-002 finding #3 — reproducible characterization.
//
// Imports the frozen, byte-identical `CorrelationContext` fixture (AsyncLocalStorage-backed, as it
// existed before this migration) and re-runs every assertion that is meaningful pre-migration.
// Cases with no legacy equivalent (sibling-namespace preservation across a shared CLS root,
// `seedActiveRoot()`) are intentionally omitted — see characterization-baseline.md for why.
import { CorrelationContext } from '../legacy-fixtures/correlation-context';

describe('[LEGACY] CorrelationContext', () => {
  it('exposes the correlation id set for the current async context only', () => {
    expect(CorrelationContext.correlationId()).toBeUndefined();

    CorrelationContext.run({ requestId: 'req-1', correlationId: 'corr-1' }, () => {
      expect(CorrelationContext.correlationId()).toBe('corr-1');
      expect(CorrelationContext.requestId()).toBe('req-1');
    });

    expect(CorrelationContext.correlationId()).toBeUndefined();
  });

  it('preserves traceId when present, and current() returns undefined outside any context', () => {
    expect(CorrelationContext.current()).toBeUndefined();

    CorrelationContext.run({ requestId: 'req-1', correlationId: 'corr-1', traceId: 'trace-1' }, () => {
      expect(CorrelationContext.current()).toEqual({
        requestId: 'req-1',
        correlationId: 'corr-1',
        traceId: 'trace-1',
      });
    });
  });

  describe('nested run()', () => {
    it('restores the parent correlation value after a nested override succeeds', () => {
      CorrelationContext.run({ requestId: 'parent', correlationId: 'parent' }, () => {
        CorrelationContext.run({ requestId: 'child', correlationId: 'child' }, () => {
          expect(CorrelationContext.correlationId()).toBe('child');
        });

        expect(CorrelationContext.correlationId()).toBe('parent');
      });
    });

    it('restores the parent correlation value after a nested override throws', () => {
      CorrelationContext.run({ requestId: 'parent', correlationId: 'parent' }, () => {
        expect(() =>
          CorrelationContext.run({ requestId: 'child', correlationId: 'child' }, () => {
            throw new Error('boom');
          }),
        ).toThrow('boom');

        expect(CorrelationContext.correlationId()).toBe('parent');
      });
    });
  });

  describe('concurrent isolation', () => {
    it('two concurrent correlation scopes never observe each other', async () => {
      const seenByA: unknown[] = [];
      const seenByB: unknown[] = [];

      const taskA = CorrelationContext.run({ requestId: 'A', correlationId: 'A' }, async () => {
        seenByA.push(CorrelationContext.correlationId());
        await new Promise((resolve) => setTimeout(resolve, 20));
        seenByA.push(CorrelationContext.correlationId());
      });
      const taskB = CorrelationContext.run({ requestId: 'B', correlationId: 'B' }, async () => {
        seenByB.push(CorrelationContext.correlationId());
        await new Promise((resolve) => setTimeout(resolve, 5));
        seenByB.push(CorrelationContext.correlationId());
      });

      await Promise.all([taskA, taskB]);

      expect(seenByA).toEqual(['A', 'A']);
      expect(seenByB).toEqual(['B', 'B']);
    });
  });
});
