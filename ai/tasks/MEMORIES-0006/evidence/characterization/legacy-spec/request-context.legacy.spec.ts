// [LEGACY origin/master@c8ca980672459e9eccbb03396a9c246448d1ead6]
// MEMORIES-0006 fix-request-review-002 finding #3 — reproducible characterization.
//
// Imports the frozen, byte-identical `RequestContext` fixture (AsyncLocalStorage-backed) and
// re-runs every actor-semantics assertion that is meaningful pre-migration. Sibling-namespace
// preservation across a shared CLS root has no legacy equivalent (three independent
// AsyncLocalStorage instances can never observe each other by construction) — see
// characterization-baseline.md.
import {
  createEmptyRequestContextStore,
  RequestContext,
  SYSTEM_ACTOR_ID,
} from '../legacy-fixtures/request-context';

describe('[LEGACY] RequestContext', () => {
  it('get() / currentActorId() outside any context', () => {
    const requestContext = new RequestContext();

    expect(requestContext.get()).toBeUndefined();
    expect(requestContext.currentActorId()).toBeNull();
  });

  it('anonymous actor: accountId null, isSystemActor false => currentActorId() is null', () => {
    const requestContext = new RequestContext();
    const store = createEmptyRequestContextStore();

    requestContext.run(store, () => {
      expect(requestContext.get()).toBe(store);
      expect(requestContext.currentActorId()).toBeNull();
    });
  });

  it('authenticated actor: currentActorId() is the accountId', () => {
    const requestContext = new RequestContext();
    const store = createEmptyRequestContextStore({ accountId: 'account-1' });

    requestContext.run(store, () => {
      expect(requestContext.currentActorId()).toBe('account-1');
    });
  });

  it('system actor: currentActorId() is SYSTEM_ACTOR_ID even with no accountId', () => {
    const requestContext = new RequestContext();
    const store = createEmptyRequestContextStore({ isSystemActor: true });

    requestContext.run(store, () => {
      expect(requestContext.currentActorId()).toBe(SYSTEM_ACTOR_ID);
    });
  });

  it('run(): does not leak the store outside the callback', () => {
    const requestContext = new RequestContext();

    requestContext.run(createEmptyRequestContextStore({ accountId: 'account-1' }), () => {
      expect(requestContext.get()).toBeDefined();
    });

    expect(requestContext.get()).toBeUndefined();
  });

  describe('nested run()', () => {
    it('does not mutate the parent request object and restores the parent after success', () => {
      const requestContext = new RequestContext();
      const parentStore = createEmptyRequestContextStore({ accountId: 'parent' });

      requestContext.run(parentStore, () => {
        requestContext.run(createEmptyRequestContextStore({ accountId: 'child' }), () => {
          expect(requestContext.currentActorId()).toBe('child');
        });

        expect(requestContext.get()).toBe(parentStore);
        expect(requestContext.currentActorId()).toBe('parent');
        expect(parentStore.accountId).toBe('parent');
      });
    });

    it('restores the parent after the nested callback throws', () => {
      const requestContext = new RequestContext();
      const parentStore = createEmptyRequestContextStore({ accountId: 'parent' });

      requestContext.run(parentStore, () => {
        expect(() =>
          requestContext.run(createEmptyRequestContextStore({ accountId: 'child' }), () => {
            throw new Error('boom');
          }),
        ).toThrow('boom');

        expect(requestContext.get()).toBe(parentStore);
        expect(requestContext.currentActorId()).toBe('parent');
      });
    });
  });

  describe('runAsSystem()', () => {
    it('currentActorId() is SYSTEM_ACTOR_ID inside the callback', () => {
      const requestContext = new RequestContext();

      requestContext.runAsSystem(() => {
        expect(requestContext.currentActorId()).toBe(SYSTEM_ACTOR_ID);
      });
    });

    it('does not leak isSystemActor to the parent request, and restores parent state after', () => {
      const requestContext = new RequestContext();
      const parentStore = createEmptyRequestContextStore({
        accountId: 'account-A',
        isSystemActor: false,
      });

      requestContext.run(parentStore, () => {
        requestContext.runAsSystem(() => {
          expect(requestContext.currentActorId()).toBe(SYSTEM_ACTOR_ID);
        });

        expect(requestContext.get()).toBe(parentStore);
        expect(parentStore.isSystemActor).toBe(false);
        expect(requestContext.currentActorId()).toBe('account-A');
      });
    });

    it('restores parent state after the callback throws', () => {
      const requestContext = new RequestContext();
      const parentStore = createEmptyRequestContextStore({ accountId: 'account-A' });

      requestContext.run(parentStore, () => {
        expect(() =>
          requestContext.runAsSystem(() => {
            throw new Error('boom');
          }),
        ).toThrow('boom');

        expect(requestContext.currentActorId()).toBe('account-A');
      });
    });
  });
});
