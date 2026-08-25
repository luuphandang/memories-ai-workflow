# MEMORIES-0006 legacy characterization baseline (AC18)

Current validated unit inventory: [unit-tests: 69 suites / 448 tests]. Historical version entries
below retain the inventory produced by their own run and are not current-state claims.

v9 — fix-request review cycle 21, finding #1 (parentless facade executions could bind the same
caller-owned mutable store). `CorrelationContext.run()` now always binds a fresh top-level store,
and `RequestContext.run()` always binds a fresh top-level store with independently owned
`roles`/`permissions` arrays and `requestedAt` Date. Concurrent regressions pass the exact same
input object to two independent parentless executions, mutate one branch across an await, and prove
the other branch plus caller input remain unchanged; the request-context exception path also proves
cleanup and caller ownership. The JWT guard fixture now enters an explicit root and uses
`seedActiveRoot()`, retaining deliberate same-root HTTP enrichment. The frozen legacy harness was
re-run after the correction and remains 5 suites / 30 tests passing. The migrated unit suite is 69
suites / 448 tests; all five builds, architecture, migration, seed, and 20 suites / 146 E2E tests
also pass against a fresh cycle-21 Postgres/Redis/MinIO stack.

v8 — fix-request review cycle 15, finding #1 (v7's `markRuntimeContextValueAtomic` escape hatch
still let two distinct opted-in leaves — or two distinct `Date` instances — expose one shared
mutable child across roots). v7 claimed a marked/atomic value or a `Date` at its own top level but
never walked into it, so two independently-marked leaves (or two `Date`s) that both merely wrapped
the same nested object were each accepted individually and the shared child itself was never
claimed — reproduced by the reviewer as two concurrent roots each observing the other's mutation of
that shared child (`{seenA:["initial","B"],seenB:["initial","B"],shared:{value:"B"}}` instead of
isolated `A`/`A` and `B`/`B`). Fixed in `libs/platform/context/src/runtime-context.types.ts` by
removing the escape hatch entirely: `markRuntimeContextValueAtomic` no longer exists (not exported
from `public-api.ts`, not callable at all), so `RuntimeContextSeed.set()` now accepts only a plain
object/array (fully walked) or a genuinely plain, undecorated `Date` (`isPlainDateInstance` — exact
`Date.prototype`, zero own properties, enumerable or not, string- or symbol-keyed) — any decorated
Date, `Date` subclass, or class instance is rejected synchronously, with no caller-declared
"trust me" bypass. No production call site ever used the escape hatch: a TypeORM `QueryRunner` is
always bound after `runRoot()` via `setNamespace()`/`TypeOrmQueryRunnerContext.run()`, never through
`RuntimeContextSeed.set()`. New regression coverage in
`libs/platform/context/test/runtime-context.service.spec.ts`: a QueryRunner-shaped class instance is
rejected unconditionally (no opt-in exists), a genuinely plain `Date` is still accepted as an atomic
leaf without being walked, a decorated `Date` and a `Date` subclass are each rejected standalone, two
distinct decorated `Date` instances sharing one nested child are both rejected (the exact review #15
reproduction), and `public-api.ts` no longer exports `markRuntimeContextValueAtomic` at all
(`@ts-expect-error`-verified). That historical v8 run produced 69 suites / 436 tests (up from 431 — 5 net new
cases; see `libs/platform/context/test/runtime-context.service.spec.ts`, current case count computed
live by `ai/skills/review-vertical-slice-completeness/scripts/check_evidence_freshness.py` rather
than hand-transcribed here, closing review #15 finding #2's evidence-staleness gap). The retained
legacy harness (fixtures/specs frozen at the base SHA, unchanged) was re-run fresh and is still
30/30 pass — `CorrelationStore`/`RequestContextStore` are, and always were, plain
objects/arrays/primitives/`Date`, so none of the legacy-comparable behavior is affected. Full
validation suite (lint, typecheck, unit, all 5 builds, architecture, migration+seed, e2e,
characterization) re-ran fresh end to end against a rebuilt throwaway real-infra stack (prior
attempt's stack had a corrupted migrations bookkeeping table — schema tables missing despite 9
migrations marked applied — so it was torn down with `docker compose down -v` and brought back up
clean before use); `evidence/logs/*.log`, the three per-suite `*.legacy.out` captures, and
`evidence/provenance.json` (canonical and both synced runtime copies) are regenerated with this run.

v7 — fix-request review cycle 14, finding #1 (unsupported value-graph shapes silently trusted as
opaque leaves). v6's `claimValueOwnership` walked the complete reachable value graph, but only for
plain objects/arrays (`isTraversableContainer`) — anything else (a class instance, `Map`, `Set`, or
function) was claimed as a single opaque leaf without being walked *or* rejected, and a plain
object/array's own symbol-keyed and non-enumerable/accessor properties were skipped by
`Object.values` entirely. The reviewer reproduced this twice against the attempt-25 build: two
distinct `Box` class instances each carrying the same nested object, and two distinct plain objects
each carrying the same nested object under a shared `Symbol` key — both accepted by two independent
seeds, both roots opened concurrently, and root A observed root B's in-place mutation of the shared
reference. Fixed in `libs/platform/context/src/runtime-context.types.ts`: ownership claiming is now
a closed-world preflight validator, not an open-world walker with an implicit safe-leaf fallback.
`collectOwnableNodes` walks a plain object/array's own state (rejecting, via
`assertSupportedContainerShape`, any symbol-keyed or non-enumerable/accessor property it could not
otherwise see), and now **rejects** — synchronously, before either seed's `runRoot()` runs — any
value that is not a plain object/array, a `Date`, or a value the caller explicitly opted in via the
new exported `markRuntimeContextValueAtomic(value)` (the only way to seed a genuinely non-cloneable
infrastructure reference such as a TypeORM `QueryRunner`, which no production call site currently
does through `RuntimeContextSeed.set()` — it is always bound via `setNamespace` after `runRoot`
instead). Claiming is also now transactional (`claimValueOwnership` only commits `collectOwnableNodes`'s
validated node set to the shared `WeakSet` once the entire graph passes), so a rejected graph never
leaves an unrelated sibling node it visited along the way permanently claimed. 10 new regression
tests added to `libs/platform/context/test/runtime-context.service.spec.ts`'s new "unsupported
value-graph shapes are rejected before any root opens" describe block: unmarked class instance
(both the concurrent-style and sequential-style Box reproductions), symbol-keyed property, a
non-enumerable property, an accessor (getter) property, `Map`, `Set`, a bare function, the
`markRuntimeContextValueAtomic` escape hatch (accepted when marked, still rejected unmarked), and
the transactional-rollback proof — unit suite is now 69 suites / 431 tests (up from 421). The
retained legacy harness (fixtures/specs frozen at the base SHA, unchanged) was re-run fresh and is
still 30/30 pass — `CorrelationStore`/`RequestContextStore` are, and always were, plain
objects/arrays/primitives/`Date`, so none of the legacy-comparable behavior's seeded values are
affected by the stricter contract. `legacy-run-output.txt` and `evidence/provenance.json` (canonical
and both synced runtime copies) are regenerated with this fresh run.

v6 — fix-request review cycle 13, finding #1 (nested mutable-value aliasing across distinct seeds)
and finding #4 (authenticated transactional concurrency test missing request/correlation ID
isolation). Finding #1: v5's `claimValueOwnership` only claimed the top-level value passed to
`RuntimeContextSeed.set()` — two distinct top-level wrapper objects that merely both *contained*
the same nested mutable object/array/Date still passed that check while the two roots they open
shared the nested reference (reproduced by the reviewer as `{nested: shared}`/`{nested: shared}`
leaking a mutation between roots). Fixed in `libs/platform/context/src/runtime-context.types.ts`:
`claimValueOwnership` now recursively walks the complete reachable value graph — plain
objects/arrays only (`isTraversableContainer`), with a cycle-safe `seen` set for self-referential
graphs — claiming every node, while still treating any non-plain instance (`Date`, a TypeORM
`QueryRunner`, ...) as an atomic, unwalked leaf so infrastructure objects are never deep-cloned or
touched internally. 7 new regression tests added to
`libs/platform/context/test/runtime-context.service.spec.ts`'s new "cross-seed nested value graph
ownership" describe block: shared nested object (concurrent + sequential), shared nested array,
shared nested `Date`, a production-shaped `RequestContextStore`-like case sharing `roles`, an
atomic non-cloneable instance proven not walked into/corrupted, and a self-referential plain-object
cycle proven not to infinite-loop — unit suite is now 69 suites / 421 tests (up from 414). Finding
#4: `libs/platform/security/test/http-context-lifecycle.e2e-spec.ts`'s "two concurrent authenticated
requests" case sent only authorization headers, so a correlation/request slice leak confined to the
authenticated await window could still pass even though `ProbeAuthService.snapshotAfterDelay`
already returned `requestId`/`correlationId`. Fixed: both overlapping requests now send distinct
`x-request-id`/`x-correlation-id` headers, and the test asserts the returned IDs and response
headers stay request-specific alongside the pre-existing actor/roles/permissions/portal/QueryRunner
assertions — e2e suite is unchanged at 20 suites / 146 tests (this is a stronger assertion inside an
existing case, not a new one). The retained legacy harness (fixtures/specs frozen at the base SHA,
unchanged) was re-run fresh and is still 30/30 pass — neither finding touches any legacy-comparable
behavior. `legacy-run-output.txt` and `evidence/provenance.json` (canonical and both synced runtime
copies) are regenerated with this fresh run.

v5 — review cycle 10, finding #1 (`RuntimeContextSeed` cross-seed value ownership). Two distinct,
individually single-use `RuntimeContextSeed` instances could still be seeded with the exact same
mutable object reference, so two roots opened from those two seeds shared that object as part of
their supposedly independent CLS storage — an in-place mutation from one root's callback was
observable from the other. Fixed in `libs/platform/context/src/runtime-context.types.ts`:
`RuntimeContextSeed.set()` now permanently claims ownership of every object/function value it is
given (a module-private `WeakSet`), across every seed instance, and throws synchronously if the
same reference is placed into a second seed — before either seed's `runRoot()` call, let alone
either root's callback, ever runs. 4 new regression tests added to
`libs/platform/context/test/runtime-context.service.spec.ts` (concurrent cross-seed reproduction,
sequential cross-seed reproduction, primitive-value exemption, and confirmation that every
production-shaped fresh-value-per-seed call site is unaffected) — unit suite is now 69 suites / 414
tests (up from 410). The retained legacy harness (fixtures/specs frozen at the base SHA, unchanged)
was re-run fresh and is still 30/30 pass with no incompatibility, since none of its fixtures alias a
mutable value across two seeds. `legacy-run-output.txt` and `evidence/provenance.json` (canonical
and both synced runtime copies) are regenerated with this fresh run.

v4 — fix-request review #8, finding #2. `legacy-run-output.txt` had been captured at 2026-08-23
15:21 (attempt 13), while `correlation-context.ts` and `request-context.ts` were subsequently
changed at 20:55 (attempt 16, mutable-reference isolation) and 22:50 (attempt 18, single-use seed
contract) respectively — later cycles reused that stale legacy run instead of regenerating it,
which is exactly the reuse-after-relevant-source-change the "Reuse policy" below forbids. v4 fixes
this: the retained legacy harness (fixtures/specs are frozen at the base SHA and did not change —
see "What is retained" below) was re-run fresh, plus every "matching migrated suite" it is compared
against (`correlation-context.spec.ts`, `request-context.spec.ts`, `typeorm-unit-of-work.spec.ts`,
`logger.module.spec.ts`, `bullmq.publisher.spec.ts`), against the finalized attempt-21 source (see
review #8 finding #1 below for the one concurrent source change, an added `TypeOrmQueryRunnerContext`
nested-restoration regression test). Result unchanged: still 30/30 legacy assertions pass, and all
5 migrated suites pass with no incompatibility. `legacy-run-output.txt` and `evidence/provenance.json`
(canonical and both synced runtime copies) are regenerated with this fresh run.

v3 — fix-request review #3, finding #5. v2 (fix-request-review-002, finding #3) replaced the v1
narrative-only baseline (fix-request-review-001 finding #3, which recorded legacy PASS/FAIL by
prose description and Jest console output only, excluded logger/publisher entirely, and had no
reproducible artifact a reviewer could re-run) with an executable, retained, hash-bound harness —
but never actually registered that harness's files in `evidence/provenance.json`, and mischaracterized
CLI audit actor resolution as a "new cross-transport guarantee" with no legacy behavior to compare
against, when it is in fact a pre-existing gap in behavior that existed before this migration too.
v3 fixes both: every harness file below is now a provenance input/artifact (see "Artifact hashes"),
and the CLI audit section below replaces the old blanket exclusion.

## Locked legacy base

- Repository: `backend`
- Base ref: `origin/master`
- Base SHA: `c8ca980672459e9eccbb03396a9c246448d1ead6` (matches
  `context.lock.json.repositories.backend.head_sha` / execution-plan `base_ref`)

## What is retained (not just described)

Everything needed to independently reproduce every result below is a real file under this
`evidence/characterization/` directory, hashed in the table at the bottom — not a narrative claim
about a since-discarded temporary edit:

```
evidence/characterization/
  jest.legacy-characterization.config.js   # dedicated Jest config, see "How to re-run"
  legacy-fixtures/                         # byte-identical `git show <base-sha>:<path>` output
    correlation-context.ts                 #   (verified via `diff` against `git show` at capture
    correlation.middleware.ts              #    time — see "Fixture provenance" below)
    logger.module.ts
    request-context.ts
    request-context.middleware.ts
    typeorm-unit-of-work.ts
    bullmq.publisher.ts                    # kept for reference; the actual legacy publisher run
                                            #   below imports the REAL, currently-live file instead
                                            #   (see "BullMqPublisher" below) — this copy is
                                            #   unused by any spec, and confirmed byte-identical to
                                            #   it, so nothing here is a stale/unread reference.
    observability-shim.ts                  # re-exports the frozen CorrelationContext; see below
  legacy-spec/                             # the actual test files executed against the fixtures
    correlation-context.legacy.spec.ts
    request-context.legacy.spec.ts
    typeorm-unit-of-work.legacy.spec.ts
    logger-header-matrix.legacy.spec.ts
    bullmq-publisher-precedence.legacy.spec.ts
  legacy-run-output.txt                    # verbatim `--verbose` run of the full harness
```

### Fixture provenance

Each file under `legacy-fixtures/` (except `observability-shim.ts`, written for this harness) was
fetched with `git show c8ca980672459e9eccbb03396a9c246448d1ead6:<repo-relative-path>` from the
`backend` worktree and saved with no manual edits. Verified byte-identical at capture time with
`diff <(git show <sha>:<path>) legacy-fixtures/<file>` for all seven files (all reported `OK`, zero
diff output). SHA-256 of each retained file is in the table below — a future cycle can re-fetch
from the same base SHA and hash-compare to detect any drift in this evidence itself.

### How to re-run

From the `backend` worktree (`worktrees/MEMORIES-0006/backend`):

```
npx jest --config ../../../ai/tasks/MEMORIES-0006/evidence/characterization/jest.legacy-characterization.config.js --verbose
```

This is a fully separate Jest config from `jest.config.js` — it is never picked up by `npm test`,
and none of the `legacy-fixtures`/`legacy-spec` files live under `apps/` or `libs/`, so they cannot
accidentally run as part of, or be confused with, the standing migrated test suite. `rootDir` is
the backend worktree (so `node_modules`/`tsconfig` resolve normally); `modulePaths` adds the
worktree's `node_modules` explicitly because the fixtures/specs physically live outside the
worktree (durable evidence belongs under `ai/tasks/<TASK-ID>/evidence/`, not committed into the
worktree). The only alias override is `@memories/platform/observability` →
`legacy-fixtures/observability-shim.ts`, scoped to this config only, used by exactly one spec (see
"BullMqPublisher" below).

## Results — every compatibility-sensitive case now has both a legacy and a migrated result

| Implementation | Legacy (this harness) | Migrated | Legacy evidence |
|---|---|---|---|
| `CorrelationContext` (nested run, concurrent isolation, traceId) | 5/5 pass | `libs/platform/observability/test/correlation-context.spec.ts` (part of standing `npm test`, 69 suites / 431 tests as of attempt 26) | `legacy-spec/correlation-context.legacy.spec.ts` |
| `RequestContext` (actor semantics, `runAsSystem`, nested run) | 10/10 pass | `libs/platform/security/test/request-context.spec.ts` | `legacy-spec/request-context.legacy.spec.ts` |
| `TypeOrmQueryRunnerContext` / `TypeOrmUnitOfWork` (concurrency, commit/rollback/release, reentrant nesting) | 7/7 pass | `libs/platform/database/test/typeorm-unit-of-work.spec.ts` (gained 2 nested-restoration regression tests exercising the real `DATABASE_CONTEXT_KEY` facade directly, fix-request-review-008 finding #1) | `legacy-spec/typeorm-unit-of-work.legacy.spec.ts` |
| `BullMqPublisher` correlationId precedence (ambient/default/explicit) | 3/3 pass | `libs/platform/queue/test/bullmq.publisher.spec.ts` "correlationId precedence" block | `legacy-spec/bullmq-publisher-precedence.legacy.spec.ts` |
| Logger + `CorrelationMiddleware` HTTP header matrix (4 combinations) | 4/4 pass (wired case) | `libs/platform/observability/test/logger.module.spec.ts` "header-combination matrix" block | `legacy-spec/logger-header-matrix.legacy.spec.ts` |
| Logger `genReqId` with no context ever active | 1/1 — **characterizes a pre-existing bug**, see below | now fixed, see below | `legacy-spec/logger-header-matrix.legacy.spec.ts` |

Total: 30/30 legacy assertions pass against the frozen base-SHA fixtures (`legacy-run-output.txt`).

### `BullMqPublisher`: real production code, swapped dependency

`bullmq.publisher.ts` is not in this migration's changed-file set (its source is byte-identical
before and after — confirmed above). Rather than treat that as a reason to skip characterization
(the exact shortcut fix-request-review-002 rejected), `legacy-spec/bullmq-publisher-precedence.legacy.spec.ts`
imports the REAL, currently-live `BullMqPublisher` class straight from the worktree and runs it
against the frozen legacy `CorrelationContext` (via the `observability-shim.ts` module-name-mapper
override, scoped to this one spec). The identical assertions already pass against the real,
migrated `CorrelationContext` as part of the standing `npm test`. This is a stronger claim than
"unchanged source implies unchanged behavior" — it is unchanged source **executed** against both
revisions of its one dependency.

### Logger header handling: one intentional, documented behavior change

The "no CorrelationMiddleware mounted" case is not a compatibility match — it is the fix-request-
review-002 finding #2 defect, characterized here on purpose so the fix is provably a deliberate,
reviewed correction and not an unnoticed regression:

- **Legacy** (`legacy-spec/logger-header-matrix.legacy.spec.ts`, "no CorrelationMiddleware
  mounted" describe block): the frozen `genReqId: () => CorrelationContext.requestId() ??
  crypto.randomUUID()` takes no `req` parameter at all, so an incoming `x-request-id` header is
  structurally impossible for it to read — the test sends the header and asserts the logged id is
  **not** the header value, proving the discard.
- **Migrated** (`libs/platform/observability/test/logger.module.spec.ts`, "honors an incoming
  x-request-id header even with no CLS ever active" — added by this fix): `genReqId: (req) =>
  resolveRequestId(req)` reads the header directly. Same test shape, opposite (fixed) outcome.
- In the **wired** configuration (`CorrelationMiddleware`/`RuntimeContextModule` actually mounted,
  matching every real application in this repo), legacy and migrated agree on all four header
  combinations — see the two "wired" result rows above — because module registration order happens
  to seed the context before `genReqId` runs either way. The defect is specific to the case where
  nothing ever seeds the context, which the fix makes robust regardless of registration order.

No compatibility claim in `implementation.json` relies on this fixed case matching legacy — it is
recorded explicitly as an improvement, per fix-request-review-002 finding #2.

### CLI audit persistence (AC14): one intentional, documented behavior change, not a "new guarantee"

v2 filed this under "new cross-transport guarantees this migration introduces" (see the removed
bullet below), on the theory that CLI audit stamping had no legacy behavior to compare against.
Fix-request review #3 finding #5 correctly rejected that: AC14's contract ("Audit actor vẫn là
SYSTEM_ACTOR_ID") predates this migration — it is the same legacy `RequestContext.runAsSystem()`
contract characterized in `legacy-spec/request-context.legacy.spec.ts` above ("system actor:
currentActorId() is SYSTEM_ACTOR_ID even with no accountId", 3/3 `runAsSystem()` cases passing).
What actually has no legacy vs. migrated comparison to make is a narrower, previously-unstated
question: whether the **production use cases the shipped CLI `seed` command actually calls**
(`SeedRolesAndPermissionsUseCase`, `SeedCardTemplatesUseCase`, `SeedProductsUseCase`) ever *read*
`RequestContext.currentActorId()` at all when stamping `createdBy`/`updatedBy`/(the `grant()` call's
audit column).

Verified directly against the frozen base SHA — not inferred, not assumed:

```
git show c8ca980672459e9eccbb03396a9c246448d1ead6:libs/modules/identity-access/src/application/use-cases/seed-roles-and-permissions.use-case.ts | grep -n "grant(\|RequestContext"
  112:        await this.rolePermissions.grant(role.id.toValue(), permission.id.toValue(), null, now);
git show c8ca980672459e9eccbb03396a9c246448d1ead6:libs/modules/card-catalog/src/application/use-cases/seed-card-templates.use-case.ts | grep -n "createdBy\|updatedBy"
  313:        createdBy: existing?.audit.createdBy ?? null,
  315:        updatedBy: null,
git show c8ca980672459e9eccbb03396a9c246448d1ead6:libs/modules/product-catalog/src/application/use-cases/seed-products.use-case.ts | grep -n "createdBy\|updatedBy"
  442:        createdBy: existing?.audit.createdBy ?? null,
  444:        updatedBy: null,
```

All three hardcoded `null` at the base SHA, exactly as they still did before fix-request review #3
finding #2 — this is a **pre-existing production gap that predates this migration**, not something
the migration broke. There is accordingly no meaningful "legacy vs. migrated" comparison to run for
it (both the frozen base SHA and the pre-fix worktree state agree: `null`) — the correct baseline
statement is that fix-request review #3 finding #2 is a deliberate, reviewed correction of a
pre-existing gap, made while implementing AC14, exactly parallel to the Logger fix above. Its
current-revision-only proof lives in `apps/cli/test/cli-runner.audit-persistence.e2e-spec.ts`
(exercises the real, unmocked shipped `seed` command against real Postgres — see that file and
`implementation.json`'s changed-file/validation entries), not in this legacy harness, since a legacy
run would just reproduce the same `null` the base SHA already shows above.

## Cases intentionally not run against legacy (unchanged from v1, still applicable)

- **Sibling-namespace preservation** across `CorrelationContext`/`RequestContext`/
  `TypeOrmUnitOfWork`: pre-migration these are three independent `AsyncLocalStorage` instances with
  no shared store — one can never observe or disturb another's value by construction, so there is
  nothing to characterize. The migrated-revision sibling-preservation tests are what actually prove
  the property this migration must hold (staying independent once sharing one CLS context).
- **`CorrelationContext.seedActiveRoot()` / `RequestContext.seedActiveRoot()`**: new methods with no
  legacy API surface at all.
- **`TypeOrmUnitOfWork` "works with no active parent CLS context"**: legacy has no concept of a
  parent CLS root to be absent.
- **Worker actor propagation / real-Redis job isolation**: these are new cross-transport guarantees
  this migration introduces (a shared root CLS context per job); legacy had no shared context to
  characterize compatibility against. Their current-revision coverage is tracked under
  fix-request-review-002 finding #4 / fix-request review #3 finding #4, not this baseline.
- **CLI audit persistence**: see "CLI audit persistence (AC14)" above — this is NOT excluded for
  lack of a legacy comparison; the comparison was made and both sides agree (`null`), which is
  exactly why the current-revision fix is documented as a deliberate correction rather than run
  through this legacy harness a second time.

## Artifact hashes (SHA-256)

| File | SHA-256 |
|---|---|
| `jest.legacy-characterization.config.js` | `2b01879acd8d273062d98270236ee3204fcfbbc2ed295cdbe108405173248a9f` |
| `legacy-fixtures/bullmq.publisher.ts` | `1f2ca0b61eb1777f0873bef85e75514d8d54c74237ffa26f09856e0257541545` |
| `legacy-fixtures/correlation-context.ts` | `a1124823df460dbebf9b93d9037a20738b7a3684672eb17d3795378ea319d1a3` |
| `legacy-fixtures/correlation.middleware.ts` | `afa168f6c59401e51ea4edfc133efbce4f1c3ce1a870255acdbc1029e6b6bb23` |
| `legacy-fixtures/logger.module.ts` | `5c7c4587965d44b07f4532e5c192ceb76d55b3351dcd26da7a3dc1505785aa1d` |
| `legacy-fixtures/observability-shim.ts` | `118631128407a0c743bd8626e9c6ddb8857f0d53e20b0a1690b2bb197106c84a` |
| `legacy-fixtures/request-context.middleware.ts` | `58773003d8d49b7e0836f1d2c7a9eee79fbd745cbddc7189c13cde8df4ea19a6` |
| `legacy-fixtures/request-context.ts` | `f1c3cf92578d366d717c125f09c6e6963a8afeb677ff48401225db3530fcf18b` |
| `legacy-fixtures/typeorm-unit-of-work.ts` | `499d7cda630b5f5f05b89525b25f32c6dd403a6a2f8d6aeeae26922c9fe5c949` |
| `legacy-spec/bullmq-publisher-precedence.legacy.spec.ts` | `41379ce5eeb3eb5fe3a1e9bab74198530d695171ee2f9debed022e68e89b81dd` |
| `legacy-spec/correlation-context.legacy.spec.ts` | `9eaf5486093b5b425d1bd5cb60c77645b6eb570bb2cd3888349c01ba6e7a8cb9` |
| `legacy-spec/logger-header-matrix.legacy.spec.ts` | `f89820f669b5cf78c7a1c7195b044d44b7f89db74c0295f8b9bef58e0158351b` |
| `legacy-spec/request-context.legacy.spec.ts` | `e5d81aa9d2cad2eadb1479c94bbfa046ed6250a33fadec85d4ce40e007c875af` |
| `legacy-spec/typeorm-unit-of-work.legacy.spec.ts` | `04b12d70a95105b30483647658ff810b7fa2815563ce0174d6f0498988a8fb84` |

These hashes (plus `legacy-run-output.txt`) are registered as provenance inputs/artifacts in
`evidence/provenance.json` — see that file for the full manifest and the command that produced
`legacy-run-output.txt`.

## Reuse policy

This is a point-in-time characterization record. If `correlation-context.ts`, `correlation.middleware.ts`,
`logger.module.ts`, `request-context.ts`, `request-context.middleware.ts`, `typeorm-unit-of-work.ts`,
or `bullmq.publisher.ts` change again in a future cycle, that cycle must re-run
`jest.legacy-characterization.config.js` (the fixtures/base SHA do not change, only the migrated
side does) and refresh `legacy-run-output.txt` plus the provenance manifest — reusing this baseline
without doing so is exactly the shortcut fix-request-review-002 finding #3 rejected.

Fix-request review #8 finding #2 caught exactly this happening: `correlation-context.ts` (attempt 16)
and `request-context.ts` (attempt 18) both changed after `legacy-run-output.txt` was last captured
(attempt 13), and no later cycle re-ran the harness before this one. `legacy-run-output.txt` is now
refreshed as of attempt 21 (see v4 note above) — a future cycle that touches any of the seven files
above must repeat this step again rather than trust this v4 timestamp indefinitely.
