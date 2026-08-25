import { AsyncLocalStorage } from 'node:async_hooks';

export interface CorrelationStore {
  requestId: string;
  correlationId: string;
  traceId?: string;
}

/**
 * Carries request/correlation IDs from an HTTP request through to any background job it
 * publishes, so a single ID can be followed across API and worker logs (§15/§24).
 */
export class CorrelationContext {
  private static readonly storage = new AsyncLocalStorage<CorrelationStore>();

  static run<TResult>(store: CorrelationStore, callback: () => TResult): TResult {
    return this.storage.run(store, callback);
  }

  static current(): CorrelationStore | undefined {
    return this.storage.getStore();
  }

  static requestId(): string | undefined {
    return this.storage.getStore()?.requestId;
  }

  static correlationId(): string | undefined {
    return this.storage.getStore()?.correlationId;
  }
}
