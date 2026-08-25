import { AsyncLocalStorage } from 'node:async_hooks';

import { Injectable } from '@nestjs/common';

/**
 * Actor/request metadata threaded through a single request's async call chain (§14). Roles and
 * permissions are mutable arrays on the same store object — `RequestContextMiddleware` seeds an
 * empty store before any guard runs; `JwtAuthGuard`/`PermissionsGuard` enrich the SAME object
 * in place once they resolve the caller, rather than starting a new `AsyncLocalStorage.run`, so
 * every layer downstream (use cases, repositories, audit metadata) observes the same reference.
 * A `null` `accountId` means "no authenticated Account" (anonymous request or system actor);
 * `isSystemActor` distinguishes worker/scheduler/CLI background execution from an anonymous HTTP
 * caller (both have `accountId: null`).
 */
export interface RequestContextStore {
  requestId: string;
  correlationId: string;
  accountId: string | null;
  userProfileId: string | null;
  sessionId: string | null;
  portal: string | null;
  authProvider: string | null;
  roles: string[];
  permissions: string[];
  ipAddress: string | null;
  userAgent: string | null;
  requestedAt: Date;
  isSystemActor: boolean;
}

/** Same shape as `Partial<RequestContextStore>`, but each key explicitly allows `undefined` so
 * callers built with `exactOptionalPropertyTypes` can pass through possibly-undefined values
 * (e.g. `correlation?.requestId`) without first stripping the key. */
type RequestContextOverrides = {
  [K in keyof RequestContextStore]?: RequestContextStore[K] | undefined;
};

/** Stamped into `createdBy`/`updatedBy`/`deletedBy` audit columns for writes performed by a
 * background actor (worker/scheduler/CLI, §14) instead of `null` — audit columns are `uuid`
 * (no free-text sentinel like `'SYSTEM'` fits), and `null` must stay reserved for "no authenticated
 * actor at all" (e.g. unauthenticated self-registration) so the two cases stay distinguishable
 * (§14 "System actor phải được phân biệt với Account actor"). */
export const SYSTEM_ACTOR_ID = '00000000-0000-0000-0000-000000000000';

export function createEmptyRequestContextStore(
  overrides: RequestContextOverrides = {},
): RequestContextStore {
  return {
    requestId: overrides.requestId ?? crypto.randomUUID(),
    correlationId: overrides.correlationId ?? overrides.requestId ?? crypto.randomUUID(),
    accountId: overrides.accountId ?? null,
    userProfileId: overrides.userProfileId ?? null,
    sessionId: overrides.sessionId ?? null,
    portal: overrides.portal ?? null,
    authProvider: overrides.authProvider ?? null,
    roles: overrides.roles ?? [],
    permissions: overrides.permissions ?? [],
    ipAddress: overrides.ipAddress ?? null,
    userAgent: overrides.userAgent ?? null,
    requestedAt: overrides.requestedAt ?? new Date(),
    isSystemActor: overrides.isSystemActor ?? false,
  };
}

@Injectable()
export class RequestContext {
  private static readonly storage = new AsyncLocalStorage<RequestContextStore>();

  run<TResult>(store: RequestContextStore, callback: () => TResult): TResult {
    return RequestContext.storage.run(store, callback);
  }

  get(): RequestContextStore | undefined {
    return RequestContext.storage.getStore();
  }

  /** The actor id to stamp on audit columns: the authenticated Account, `SYSTEM_ACTOR_ID` for a
   * `runAsSystem` background actor, or `null` for a genuinely anonymous request (no Account
   * authenticated at all, e.g. self-registration) — never throws, since not every write happens
   * inside a request with a context (direct unit-test/use-case construction). */
  currentActorId(): string | null {
    const store = RequestContext.storage.getStore();
    if (!store) {
      return null;
    }
    return store.isSystemActor ? SYSTEM_ACTOR_ID : store.accountId;
  }

  /** Runs `work` under a synthetic system-actor context (worker/scheduler/CLI, §14) so audit
   * columns and correlation IDs are still populated outside of any HTTP request. */
  runAsSystem<TResult>(callback: () => TResult, correlationId?: string): TResult {
    return this.run(
      createEmptyRequestContextStore({ isSystemActor: true, correlationId }),
      callback,
    );
  }
}
