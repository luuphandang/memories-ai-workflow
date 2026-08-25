// Legacy characterization shim (MEMORIES-0006 fix-request-review-002 finding #3).
// Re-exports the frozen, byte-identical-to-origin/master@c8ca980 `CorrelationContext` so the REAL,
// unmodified, currently-live `bullmq.publisher.ts` can be executed unchanged against pre-migration
// (AsyncLocalStorage-backed) correlation semantics — see jest.legacy-characterization.config.js,
// which maps `@memories/platform/observability` to this file only for the publisher-precedence
// legacy spec.
export { CorrelationContext } from './correlation-context';
export type { CorrelationStore } from './correlation-context';
