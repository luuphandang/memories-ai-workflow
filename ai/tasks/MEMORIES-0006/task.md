# MEMORIES-0006: Migrate Runtime Context To `nestjs-cls`

## Jira

* Type: `epic`
* Parent: `-`
* Epic: `MEMORIES-0006`

---

# Goal

Thay thế toàn bộ runtime context hiện đang sử dụng `node:async_hooks` / custom `AsyncLocalStorage` trong backend bằng `nestjs-cls`, đồng thời giữ nguyên observable behavior của hệ thống.

Sau migration:

* backend chỉ sử dụng **một CLS infrastructure chung**;
* mỗi execution flow có root CLS context rõ ràng;
* các context domain vẫn được tách biệt theo responsibility:

  * correlation / observability;
  * request / security;
  * database transaction;
* không xảy ra context leak giữa các concurrent execution;
* không thay đổi business semantics;
* không thay đổi transaction abstraction hiện tại;
* `nestjs-cls` không trở thành dependency trực tiếp của business modules.

Các behavior bắt buộc giữ nguyên:

* request isolation;
* request ID / correlation ID semantics;
* audit actor stamping;
* authenticated / anonymous / system actor semantics;
* BullMQ correlation propagation;
* CLI system actor;
* transaction reentrancy;
* active `QueryRunner` propagation;
* cleanup khi success hoặc exception.

---

# Background

Backend hiện có ba `AsyncLocalStorage` độc lập.

## 1. `CorrelationContext`

File:

```text
libs/platform/observability/src/correlation-context.ts
```

Store hiện tại chứa:

```ts
{
  requestId,
  correlationId,
  traceId?,
}
```

Được seed bởi:

```text
CorrelationMiddleware
```

và được sử dụng bởi:

* logger;
* BullMQ publisher;
* BullMQ worker;
* các consumer cần correlation metadata.

---

## 2. `RequestContext`

File:

```text
libs/platform/security/src/request-context.ts
```

Store hiện tại chứa các thông tin như:

* actor/account;
* roles;
* permissions;
* portal;
* system actor flag;
* các security context field hiện có.

HTTP lifecycle hiện tại:

```text
CorrelationMiddleware
        ↓
RequestContextMiddleware
        ↓
JwtAuthGuard
```

`RequestContextMiddleware` reuse `requestId` / `correlationId` đã được correlation layer resolve.

`JwtAuthGuard` enrich **cùng request context hiện tại**, không tạo context độc lập.

`currentActorId()` có semantics:

```text
system actor
    => SYSTEM_ACTOR_ID

authenticated actor
    => accountId

anonymous
    => null
```

CLI hiện sử dụng:

```ts
requestContext.runAsSystem(...)
```

để audit write bằng:

```text
SYSTEM_ACTOR_ID
```

---

## 3. `TypeOrmQueryRunnerContext`

File:

```text
libs/platform/database/src/typeorm-unit-of-work.ts
```

Context lưu active `QueryRunner`.

`TypeOrmUnitOfWork.withTransaction()` sử dụng context để:

* repository trong cùng execution dùng đúng transaction;
* detect nested transaction;
* nested `withTransaction()` join active transaction;
* không mở transaction thứ hai nếu đã có active `QueryRunner`.

Expected behavior:

```text
outer withTransaction
    │
    └── QueryRunner A
          │
          └── inner withTransaction
                    │
                    └── reuse QueryRunner A
```

---

# Current execution models

Backend hiện có:

```text
apps/api
apps/worker
apps/scheduler
apps/cli
apps/realtime
```

Không phải execution model nào cũng chạy qua HTTP middleware.

Migration phải xử lý context boundary dựa trên **execution model**, không giả định mọi consumer đều chạy trong HTTP request.

---

# Source-of-truth baseline và trạng thái integration

Behavior legacy phải được characterize từ repository đích:

```text
apps/backend
```

Base branch/SHA cụ thể phải được ghi vào implementation report trước khi sửa code. Một feature
worktree chỉ là nơi chứa implementation candidate; nó không được xem là trạng thái của hệ thống
hiện tại cho đến khi diff đã được review và tích hợp vào repository/branch đích.

Các artifact như:

```text
implementation.json
implementation-progress.json
evidence/**
```

chỉ chứng minh revision/worktree được nêu trong provenance đã được kiểm tra. Chúng không chứng
minh `apps/backend` hiện tại đã chứa migration. Báo cáo bàn giao phải ghi rõ một trong hai trạng
thái:

```text
implemented in feature worktree, not integrated into target branch
integrated and re-verified on target repository/branch
```

Không dùng post-migration worktree làm baseline giả định cho legacy semantics.

---

# Architecture decisions

## 1. Tạo `libs/platform/context`

Tạo platform library mới:

```text
libs/platform/context
```

Path alias:

```text
@memories/platform/context
```

Library này chịu trách nhiệm encapsulate runtime CLS infrastructure dựa trên `nestjs-cls`.

Định hướng file:

```text
libs/platform/context/
└── src/
    ├── public-api.ts
    ├── runtime-context.module.ts
    ├── runtime-context.service.ts
    ├── runtime-context-accessor.ts
    └── runtime-context.types.ts
```

Tên file/class có thể thay đổi theo convention hiện tại của repository, nhưng responsibility phải giữ nguyên.

---

## 2. Dependency direction

Expected dependency direction:

```text
observability ─┐
security ──────┼──> platform/context ──> nestjs-cls
database ──────┘
```

Không được tạo dependency ngược:

```text
platform/context
      ↓
observability / security / database
```

`libs/platform/context` không được phụ thuộc vào:

```text
libs/platform/observability
libs/platform/security
libs/platform/database
```

---

## 3. Context infrastructure không sở hữu domain state type

`libs/platform/context` chỉ cung cấp generic runtime context mechanism.

Nó không sở hữu các type:

```text
CorrelationStore
RequestContextStore
QueryRunner
```

Ownership:

```text
observability owns CorrelationStore
security      owns RequestContextStore
database      owns QueryRunner/context state
```

`platform/context` không được import:

```text
typeorm
CorrelationStore
RequestContextStore
QueryRunner
```

chỉ để định nghĩa một central store.

Điều này tránh:

* reverse dependency;
* circular dependency;
* coupling generic context infrastructure với database technology;
* coupling observability/security/database state vào một flat type.

---

## 4. Typed namespaced context

Runtime CLS phải hỗ trợ logical namespaces:

```text
CLS
├── correlation
├── request
└── database
```

Có thể implement bằng:

* typed context key;
* typed token;
* generic accessor;
* typed wrapper/facade;
* TypeScript module augmentation;
* giải pháp tương đương.

Không bắt buộc một kỹ thuật cụ thể.

### Invariant

Type safety phải được enforce tại platform facade boundary.

Không sử dụng flat global store kiểu:

```ts
{
  requestId,
  correlationId,
  accountId,
  roles,
  permissions,
  queryRunner,
}
```

---

## 5. Encapsulate `nestjs-cls`

`nestjs-cls` là infrastructure detail.

Business modules không được trực tiếp import:

```ts
ClsService
ClsModule
ClsServiceManager
```

Business code tiếp tục phụ thuộc vào:

```text
CorrelationContext
RequestContext
UnitOfWork
```

hoặc abstraction platform tương đương.

Direct `nestjs-cls` import chỉ được phép tại:

```text
libs/platform/context/**
```

và application composition/bootstrap layer nếu thực sự cần configure CLS lifecycle.

Không được lan vào:

```text
libs/modules/**
```

hoặc platform consumer khác nếu không có documented exception.

---

## 6. Runtime context accessor

Nếu cần truy cập CLS ngoài constructor DI, ví dụ callback/factory trong logger, việc truy cập này phải được encapsulate.

Preferred:

```text
logger
   ↓
RuntimeContextAccessor
   ↓
ClsServiceManager
```

Không:

```text
logger
   ↓
ClsServiceManager directly
```

`ClsServiceManager` chỉ được sử dụng ở nơi DI thực sự không khả dụng.

---

# Context lifecycle

## Terminology

### Root execution boundary

CLS context đại diện cho một execution độc lập:

```text
HTTP request
BullMQ job
CLI command
scheduler execution
realtime event
```

### Nested scope

Temporary contextual override bên trong một execution đang tồn tại.

Ví dụ:

```text
runAsSystem(...)
CorrelationContext.run(...)
RequestContext.run(...)
temporary transaction state
```

Nested scope không được xem là một HTTP request/job/command mới.

---

# Root boundary ownership

## HTTP

Mỗi HTTP request có đúng **một root CLS context**.

Target:

```text
HTTP request
      ↓
CLS initialization
      ↓
Correlation seed
      ↓
RequestContext seed
      ↓
JwtAuthGuard enrich
      ↓
Controller
      ↓
UseCase
      ↓
Repository
```

Không được:

```text
HTTP CLS root
    ↓
CorrelationMiddleware.run(new CLS)
    ↓
RequestContextMiddleware.run(new CLS)
```

`CorrelationMiddleware` và `RequestContextMiddleware` chỉ seed/enrich root context hiện tại.

---

## BullMQ

Mỗi BullMQ job có một root CLS context độc lập.

```text
Job A → CLS A
Job B → CLS B
```

Không reuse:

* CLS của HTTP producer;
* CLS của job trước;
* CLS của concurrent job khác.

---

## CLI

Mỗi CLI command có một root CLS execution.

`runAsSystem()` có thể:

* tạo temporary root scope nếu chưa có active context theo legacy contract;
* hoặc enrich/override request slice trong root scope đã tồn tại.

Không tạo redundant root context:

```text
runtimeContext.run(...)
    ↓
runAsSystem() tạo root khác
```

nếu root hiện tại đã đủ.

---

## Scheduler / realtime

Rà soát actual consumer.

Nếu execution sử dụng runtime context thì phải có transport-appropriate root CLS context.

Nếu không sử dụng context thì không thêm behavior mới chỉ để đồng nhất kiến trúc.

---

# Nested scope semantics

Đây là backward-compatibility requirement quan trọng.

Hệ thống cũ có ba ALS độc lập.

Ví dụ, một nested `RequestContext` scope không làm mất:

```text
CorrelationContext
TypeOrmQueryRunnerContext
```

Sau migration sang shared CLS, behavior này phải tiếp tục đúng.

---

## Rule

Không dựa vào implicit/default nested behavior của `nestjs-cls`.

Mọi API tạo nested scope phải có semantics explicit.

Ví dụ:

```text
parent:
  correlation = C1
  request     = R1
  database    = D1
```

Khi mở temporary system request context:

```text
child:
  correlation = C1
  request     = SYSTEM
  database    = D1
```

Sau callback:

```text
parent:
  correlation = C1
  request     = R1
  database    = D1
```

Không được:

```text
child:
  request = SYSTEM

correlation = lost
database = lost
```

---

# Mutable-reference isolation

Nested context phải preserve không chỉ logical value mà cả isolation khỏi mutable parent state.

Ví dụ parent:

```ts
request = {
  accountId: 'A',
  isSystemActor: false,
};
```

Không được implement nested system scope bằng:

```ts
request.isSystemActor = true;
```

nếu `request` vẫn là cùng object reference với parent.

Nested override phải conceptually tạo child value:

```ts
const childRequest = {
  ...parentRequest,
  isSystemActor: true,
};
```

và bind value đó vào child scope.

Sau callback:

```text
parent request state unchanged
```

---

## Root enrichment vs nested override

### Root request enrichment

`JwtAuthGuard` đang enrich request hiện tại.

Behavior này vẫn có thể mutate cùng root `RequestContextStore` object để giữ backward compatibility.

```text
HTTP root
    ↓
RequestContextStore
    ↓
JwtAuthGuard mutate current root object
```

### Nested contextual override

Các API:

```text
RequestContext.run(...)
runAsSystem(...)
CorrelationContext.run(...)
```

không được mutate parent-owned object nếu mutation cần được rollback sau callback.

Nested scope phải:

```text
replace / clone overridden slice
```

và giữ sibling slices nguyên vẹn.

---

## Database contextual state

Nguyên tắc tương tự áp dụng cho database transaction state.

Nếu implementation sử dụng:

```ts
{
  queryRunner,
}
```

không được mutate shared parent object theo cách khiến value leak giữa scope.

Ưu tiên:

* replace contextual value;
* hoặc sử dụng typed context key riêng cho active `QueryRunner`.

---

# `CorrelationContext.run()`

Nếu facade này được giữ:

* thay đổi chỉ correlation slice;
* không làm mất request slice;
* không làm mất database slice;
* parent state được restore sau callback;
* restore cả khi callback throw;
* nếu chưa có active CLS context thì có thể tạo temporary root scope để giữ backward compatibility.

Không được rely vào implicit nested behavior của installed `nestjs-cls` version.

---

# `RequestContext.run()`

Nếu facade này được giữ:

* thay đổi chỉ request/security slice;
* giữ correlation/database sibling slices;
* không mutate parent request object;
* restore parent request value;
* restore cả khi callback throw.

---

# `runAsSystem()`

Phải giữ:

```text
currentActorId() => SYSTEM_ACTOR_ID
```

trong callback.

Nếu có parent context:

* correlation state vẫn giữ nguyên;
* database state vẫn giữ nguyên;
* parent request state không bị mutate;
* parent request state được restore sau callback.

Nếu chưa có active context:

* giữ legacy contract;
* hoặc caller tạo root scope rõ ràng nếu đó đã là behavior hiện tại.

Behavior phải được khóa bằng characterization test trước migration.

---

# Module registration

## Configuration ownership

`ClsModule.forRoot()` / `ClsModule.forRootAsync()` là **application-level configuration**.

Không đặt:

```ts
ClsModule.forRoot(...)
```

bên trong reusable platform module được import ở nhiều nơi.

`libs/platform/context` có thể:

* import `ClsModule` theo cách không tạo root configuration;
* provide `RuntimeContextService`;
* provide `RuntimeContextAccessor`;
* export runtime context abstractions.

Application composition root chịu trách nhiệm configure CLS đúng một lần.

Conceptually:

```text
apps/api
   ├── configure CLS once
   └── RuntimeContextModule

apps/worker
   ├── configure CLS once
   └── RuntimeContextModule

apps/cli
   ├── configure CLS once
   └── RuntimeContextModule
```

`scheduler` / `realtime` chỉ configure nếu execution path thực sự sử dụng runtime context.

### Invariant

Trong một Nest application:

```text
CLS root configuration count = 1
```

Không có multiple independent:

```ts
ClsModule.forRoot(...)
```

trong cùng application container.

---

# HTTP CLS initializer

HTTP CLS initializer phải preserve existing behavior.

## Request ID

Không sử dụng request ID generator riêng của `nestjs-cls`.

Configure tương đương:

```text
generateId = false
```

Existing:

```text
requestId
correlationId
```

là source of truth.

Nếu dùng custom generator thì phải reuse **chính xác** existing request ID semantics.

---

## Request/response storage

Không persist raw HTTP request/response vào CLS nếu hệ thống hiện không có requirement này.

Configure tương đương:

```text
saveReq = false
saveRes = false
```

trừ khi codebase review chứng minh consumer hiện tại cần chúng.

Middleware nhận `req` để seed context không đồng nghĩa phải lưu raw request object vào CLS.

---

## Context initialization mechanism

Ưu tiên execution-safe `run` semantics.

Không enable:

```text
useEnterWith = true
```

trừ khi:

1. actual framework/integration làm mất context với `run`;
2. issue được reproduce bằng test;
3. lý do được document trong implementation report.

Expected baseline:

```text
generateId = false
saveReq = false
saveRes = false
useEnterWith = false
```

Exact mount strategy có thể automatic hoặc manual tùy actual middleware ordering.

---

# Request ID / correlation ID

Existing ID semantics là source of truth.

Migration không được thay đổi behavior của:

```text
x-request-id
x-correlation-id
```

Characterize trước migration:

```text
1. có x-request-id + x-correlation-id
2. chỉ có x-request-id
3. chỉ có x-correlation-id
4. không có cả hai
```

Nếu hiện tại có:

* normalization;
* fallback;
* generated ID;
* validation;
* response propagation;

phải giữ nguyên.

Không được phát sinh:

```text
HTTP request ID = A
CLS ID          = B
pino ID         = C
```

cho cùng request.

---

# Correlation metadata compatibility

Characterize toàn bộ existing `CorrelationStore`, không chỉ hai ID chính.

Tối thiểu:

```text
requestId
correlationId
traceId
```

nếu `traceId` đang tồn tại/được consumer sử dụng.

Test:

* read trong context;
* nested preservation;
* parent restoration;
* concurrent isolation;
* exception cleanup.

Không tự thêm propagation mới cho `traceId`.

Nếu `traceId` hiện không propagate qua BullMQ thì migration không được tự thêm behavior đó.

---

# RequestContextStore compatibility

Migration infrastructure không đồng nghĩa được thay đổi public shape của `RequestContextStore`.

Rà soát actual fields và consumer trước migration.

Nếu store hiện chứa mirrored metadata như:

```text
requestId
correlationId
```

thì không tự xóa các field này chỉ vì correlation slice đã trở thành canonical runtime source.

Rule:

```text
CorrelationContext = canonical correlation source
```

nhưng existing `RequestContextStore` fields phải được giữ nếu chúng là existing facade contract hoặc có consumer hiện tại.

Việc normalize/remove duplicated field là refactor riêng ngoài migration scope.

---

# Logger integration

Rà soát:

```text
libs/platform/observability/src/logger.module.ts
```

đặc biệt:

```text
genReqId
customProps
```

Không giả định callback luôn chạy trong active CLS context.

Logger phải:

* hoạt động khi context chưa active;
* không throw;
* sử dụng cùng request ID / correlation ID source of truth;
* đọc CLS khi lifecycle cho phép;
* không tự tạo ID thứ hai.

Nếu logger chạy trước CLS initialization:

* dùng request/header information hiện có;
* hoặc shared pure resolver;
* không ép callback phụ thuộc vào một CLS store chưa tồn tại.

Nếu cần shared ID resolution logic:

* extract pure helper;
* không duplicate generation/fallback logic.

---

# Scope

## 1. Dependency

* [ ] Thêm `nestjs-cls` vào `apps/backend/package.json`.
* [ ] Chọn stable version có peer dependency tương thích với NestJS version hiện tại.
* [ ] Không sử dụng prerelease.
* [ ] Verify compatibility trước khi install.
* [ ] Không upgrade NestJS.
* [ ] Cập nhật `package-lock.json`.
* [ ] Ghi selected version trong implementation report.
* [ ] Không đổi major `nestjs-cls` trong quá trình implement nếu không có documented reason.
* [ ] Không thêm `@nestjs-cls/transactional`.

---

## 2. Platform context infrastructure

* [ ] Tạo `libs/platform/context`.
* [ ] Thêm path alias:

```text
@memories/platform/context
```

* [ ] Implement runtime context abstraction.
* [ ] Encapsulate direct dependency tới `nestjs-cls`.
* [ ] Context lib không import:

  * `platform/security`;
  * `platform/observability`;
  * `platform/database`;
  * `typeorm`.
* [ ] Context lib không sở hữu domain-specific store types.
* [ ] Thêm rule mới vào `.dependency-cruiser.js` (`apps/backend/.dependency-cruiser.js`) để
  `npm run test:architecture` tự động chặn `libs/platform/context` import `libs/platform/security`,
  `libs/platform/observability`, `libs/platform/database`, `typeorm`. Toàn bộ 5 rule hiện có trong
  file này chỉ scope vào `libs/modules/*` (trừ `no-circular` là global) — không có rule nào đang
  enforce boundary giữa các `libs/platform/*` — nên các ràng buộc dependency-direction của task này
  (Architecture decisions #2, #3) hiện chỉ là quy ước bằng văn bản, không được CI xác minh, trái
  với nguyên tắc "mọi ràng buộc kiến trúc được depcruise kiểm tra tự động, không chỉ dựa vào
  convention" (`ai/repos/backend/architecture.md`). Không được coi item này là optional.
* [ ] Hỗ trợ typed namespaced contextual state.
* [ ] Hỗ trợ:

  * active-context detection;
  * get/set state;
  * root scope;
  * scoped override;
  * safe cleanup.
* [ ] Không expose unnecessary `nestjs-cls` implementation detail.
* [ ] Scoped override không mutate parent-owned object.
* [ ] Có explicit nested policy.
* [ ] Không rely vào default `ifNested` behavior của library.

---

## 3. CorrelationContext

Refactor:

```text
libs/platform/observability/src/correlation-context.ts
```

* [ ] Xóa custom `AsyncLocalStorage`.
* [ ] Dùng shared runtime context infrastructure.
* [ ] Ưu tiên giữ public API:

```ts
run()
current()
requestId()
correlationId()
```

* [ ] Giữ behavior ngoài active context.
* [ ] Giữ `traceId` behavior nếu hiện có.
* [ ] Giữ nested scope semantics.
* [ ] Preserve sibling slices.
* [ ] Restore parent state sau success/exception.
* [ ] Không mở nested root CLS trong HTTP middleware flow.

---

## 4. RequestContext

Refactor:

```text
libs/platform/security/src/request-context.ts
```

* [ ] Xóa custom `AsyncLocalStorage`.
* [ ] Giữ:

```ts
run()
get()
currentActorId()
runAsSystem()
```

* [ ] Giữ:

```text
SYSTEM_ACTOR_ID
createEmptyRequestContextStore
```

* [ ] Giữ anonymous/authenticated/system semantics.
* [ ] Giữ existing `RequestContextStore` shape.
* [ ] Preserve sibling CLS slices.
* [ ] Nested `run()` không mutate parent request object.
* [ ] `runAsSystem()` không làm `isSystemActor` leak về parent.
* [ ] Restore parent state cả success và exception.

---

## 5. HTTP context initialization

Rà soát:

```text
libs/platform/observability/src/correlation.middleware.ts
libs/platform/security/src/request-context.middleware.ts
libs/platform/observability/src/observability.module.ts
libs/platform/security/src/security.module.ts
apps/api/src/app.module.ts
apps/api bootstrap
```

* [ ] Chỉ có một HTTP root CLS context.
* [ ] CLS initialize trước các context consumer.
* [ ] Correlation seed trước request/security seed.
* [ ] Authentication enrich sau request context seed.
* [ ] Middleware không gọi facade `run()` để tạo root mới.
* [ ] Verify actual middleware ordering.
* [ ] Manual mount CLS initializer tại bootstrap nếu ordering yêu cầu.
* [ ] Không generate CLS-specific request ID.
* [ ] Không persist raw request/response nếu không cần.
* [ ] Không enable `useEnterWith` nếu không có reproduced requirement.

---

## 6. JwtAuthGuard

Rà soát:

```text
libs/platform/security/src/jwt-auth.guard.ts
```

* [ ] Guard mutate/enrich root `RequestContextStore` hiện tại.
* [ ] Không tạo CLS root mới.
* [ ] Không replace object ngoài existing semantics.
* [ ] Giữ:

  * account;
  * roles;
  * permissions;
  * portal;
  * các field hiện có.

---

# TypeORM / UnitOfWork

## Existing behavior

`TypeOrmUnitOfWork.withTransaction()` phải giữ reentrant transaction.

---

## Active context

Nếu có active CLS root:

```text
HTTP / Job / CLI
      ↓
withTransaction
```

outer transaction set database transaction state vào current execution context.

State cleanup phải exception-safe.

---

## No active context

`TypeOrmUnitOfWork` không được trở nên phụ thuộc bắt buộc vào việc caller đã tạo CLS root.

Nếu `withTransaction()` được gọi khi chưa có active CLS:

* outer transaction phải tạo temporary CLS context cần thiết;
* repository trong callback vẫn thấy active `QueryRunner`;
* context cleanup sau callback.

Behavior này phải được characterization trước migration.

---

## Reentrant transaction

Nếu đã có active `QueryRunner`:

```text
outer
  QueryRunner A
      ↓
inner withTransaction
      ↓
reuse QueryRunner A
```

Không:

* create QueryRunner B;
* start transaction thứ hai;
* commit outer transaction từ inner;
* rollback outer transaction từ inner.

---

## QueryRunner cleanup

Conceptual implementation:

```ts
const previous = currentRunner();

setCurrentRunner(runner);

try {
  return await work();
} finally {
  restore(previous);
}
```

Required behavior:

```text
before outer
  runner = previous / undefined

inside outer
  runner = A

inside inner
  runner = A

after inner
  runner = A

after outer
  runner = previous / undefined
```

Phải đúng cho:

* success;
* throw;
* rollback;
* nested calls.

---

## Parent sibling preservation

Parent context:

```text
correlation = C1
request     = R1
```

Trong transaction:

```text
correlation = C1
request     = R1
queryRunner = Q1
```

Sau transaction:

```text
correlation = C1
request     = R1
queryRunner = previous / undefined
```

Transaction scope không được thay thế toàn bộ CLS context hoặc làm mất sibling state.

---

# BullMQ

## Publisher

Rà soát:

```text
libs/platform/queue/src/bullmq/bullmq.publisher.ts
```

* [ ] Current `correlationId` tiếp tục được serialize vào `BackgroundJobEnvelope`.
* [ ] Không serialize toàn bộ CLS store.
* [ ] Không propagate `QueryRunner`.
* [ ] Giữ nguyên optional `actorId` hiện có: caller có thể truyền tường minh qua
  `BackgroundJobOptions` và publisher phải copy nguyên giá trị đó vào `BackgroundJobEnvelope`.
* [ ] Không tự động lấy actor từ ambient `RequestContext` khi caller không truyền `actorId`.
* [ ] Không thêm `traceId` propagation nếu hiện tại chưa có.
* [ ] Nếu publisher có explicit correlation override, giữ precedence semantics hiện tại.
* [ ] Không thay đổi shape hoặc semantics của các field hiện có trong `BackgroundJobEnvelope`:

  ```text
  jobId
  jobName
  version
  createdAt
  correlationId
  causationId
  actorId
  payload
  ```

---

## Worker

Rà soát:

```text
libs/platform/queue/src/bullmq/bullmq.worker.ts
```

Mỗi job:

```text
BackgroundJobEnvelope
        ↓
new job CLS root
        ↓
restore correlation metadata
        ↓
processor
```

* [ ] Không inherit HTTP producer store.
* [ ] Không inherit previous job store.
* [ ] Concurrent jobs independent.
* [ ] Cleanup khi success.
* [ ] Cleanup khi processor throw.

---

## Actor semantics

Task này **không tự động propagate authenticated actor từ HTTP sang background job** và không
restore actor thành ambient `RequestContext` trong worker.

```text
HTTP actor
    │
    └── NOT propagated
            ↓
        BullMQ worker
```

Actor propagation nếu cần là task riêng vì thay đổi audit/security semantics.

`BackgroundJobEnvelope.actorId` là metadata optional đã tồn tại trong contract: caller vẫn có thể
truyền nó tường minh. Việc giữ field này không đồng nghĩa worker được phép bind nó vào
`RequestContext` hoặc làm cho `currentActorId()` trả về giá trị đó.

## Actor semantics theo execution model

| Execution model | Ambient `RequestContext` legacy | `currentActorId()` legacy |
|---|---|---|
| Authenticated HTTP | Có, được guard enrich | `accountId` |
| Anonymous HTTP | Có, không có account | `null` |
| CLI command | `runAsSystem()` | `SYSTEM_ACTOR_ID` |
| BullMQ worker | Không restore request/security context | `null` nếu handler đọc trực tiếp |
| Scheduler | Chưa có consumer thực tế | Chưa xác định; phải characterize nếu thêm consumer |
| Realtime | Phụ thuộc transport/entrypoint thực tế | Phải characterize trước khi thay đổi |

Không suy diễn rằng mọi background execution đều là system actor. Trong phạm vi task này, chỉ CLI
có legacy contract `runAsSystem()`. Không tự thêm `runAsSystem()` cho worker/scheduler.

---

# CLI

Rà soát:

```text
apps/cli/src/cli-runner.service.ts
```

* [ ] Mỗi command có root CLS execution.
* [ ] `runAsSystem()` vẫn dẫn tới:

```text
currentActorId() = SYSTEM_ACTOR_ID
```

* [ ] Audit columns vẫn stamp:

  * `createdBy`;
  * `updatedBy`;
  * `deletedBy`.
* [ ] Cleanup khi success.
* [ ] Cleanup khi throw.
* [ ] Không tạo redundant root context.
* [ ] Nested `runAsSystem()` không mutate parent context.

---

# Scheduler / realtime

Rà soát:

```text
apps/scheduler
apps/realtime
```

Search consumer:

```text
CorrelationContext
RequestContext
TypeOrmQueryRunnerContext
TypeOrmUnitOfWork
```

Nếu có:

* [ ] xác định execution entrypoint;
* [ ] tạo transport-appropriate CLS root;
* [ ] đảm bảo cleanup;
* [ ] đảm bảo concurrency isolation.

Nếu không có context consumer:

* không thêm behavior mới.

---

# Characterization tests

Characterization tests là **migration prerequisite**.

Đối với behavior chưa explicit:

```text
1. viết characterization test
2. chạy test trên legacy AsyncLocalStorage implementation
3. xác nhận PASS
4. migrate implementation
5. chạy lại cùng test trên nestjs-cls implementation
```

Không được:

```text
migrate trước
    ↓
viết test dựa trên behavior mới
    ↓
coi đó là legacy characterization
```

Nếu behavior hiện tại không xác định được:

* ghi nhận ambiguity;
* chọn behavior làm thay đổi observable semantics ít nhất;
* document decision.

---

## Correlation characterization

Characterize:

* `current()` ngoài context;
* `requestId()` ngoài context;
* `correlationId()` ngoài context;
* `traceId` nếu hiện có;
* nested `run()`;
* sibling preservation;
* parent restoration;
* exception restoration.

---

## RequestContext characterization

Characterize:

* `get()` ngoài context;
* anonymous actor;
* authenticated actor;
* system actor;
* nested `run()`;
* nested `runAsSystem()`;
* parent restoration;
* exception restoration;
* sibling state preservation;
* mutable-reference isolation.

---

## Request header characterization

Characterize:

```text
both headers
request ID only
correlation ID only
no headers
```

Đồng thời kiểm tra:

```text
incoming headers
resolved internal IDs
response headers
```

Nếu implementation hiện tại expose:

```text
x-request-id
x-correlation-id
```

trong response thì giữ behavior đó.

Nếu hiện tại không expose thì không tự thêm.

---

## UnitOfWork characterization

Characterize:

* transaction có parent CLS;
* transaction không có parent CLS;
* nested transaction;
* sibling preservation;
* success cleanup;
* exception cleanup.

---

## BullMQ publisher characterization

Characterize explicit/default correlation precedence nếu API hiện hỗ trợ cả hai.

---

# Tests after migration

## CorrelationContext

Update:

```text
libs/platform/observability/test/correlation-context.spec.ts
```

Cover:

* get/set;
* request ID;
* correlation ID;
* `traceId` nếu applicable;
* isolation;
* nested scope;
* sibling preservation;
* parent restore;
* success cleanup;
* exception cleanup;
* concurrent executions.

---

## RequestContext

Tạo nếu chưa có:

```text
libs/platform/security/test/request-context.spec.ts
```

Cover:

* anonymous;
* authenticated;
* system;
* `runAsSystem`;
* nested scope;
* parent restore;
* exception cleanup;
* sibling namespace preservation;
* mutable-reference isolation.

---

## `runAsSystem()` parent isolation

Parent:

```text
actor = A
isSystemActor = false
```

Inside:

```text
runAsSystem()
```

Expected:

```text
currentActorId() = SYSTEM_ACTOR_ID
```

After:

```text
actor = A
isSystemActor = false
```

Parent state không bị mutate.

---

## RequestContext nested exception

```text
parent R1
    ↓
nested R2
    ↓
throw
```

After exception:

```text
current request context = R1
```

---

## Correlation nested exception

```text
parent C1
    ↓
nested C2
    ↓
throw
```

After exception:

```text
current correlation context = C1
```

---

## JwtAuthGuard

Update:

```text
libs/platform/security/test/jwt-auth.guard.spec.ts
```

Verify:

* enrich đúng current root request context;
* không tạo root context mới;
* actor;
* roles;
* permissions;
* portal;
* existing fields.

---

## TypeOrmUnitOfWork

Update:

```text
libs/platform/database/test/typeorm-unit-of-work.spec.ts
```

Bắt buộc cover:

1. outer transaction;
2. reentrant nested transaction;
3. active CLS parent;
4. no active CLS parent;
5. cleanup success;
6. cleanup exception;
7. restore previous runner;
8. concurrent QueryRunner isolation;
9. correlation sibling preservation;
10. request sibling preservation.

---

## Logger

Update:

```text
libs/platform/observability/test/logger.module.spec.ts
```

Cover:

* active CLS;
* no active CLS;
* same request/correlation ID source;
* no duplicate generation;
* concurrent isolation;
* no throw;
* correct behavior trước/sau CLS initialization nếu lifecycle khác nhau.

---

## HTTP E2E

Reuse existing API E2E infrastructure. Chạy qua `npm run test:e2e` trên hạ tầng thật
(PostgreSQL/Redis/MinIO) theo yêu cầu Definition of Done — xem "Validation > E2E trên hạ tầng
thật".

Thêm concurrent test:

```text
Request A:
  actor = A
  correlation = A

Request B:
  actor = B
  correlation = B
```

Run concurrently.

Expected:

```text
A never observes B
B never observes A
```

Cover tối thiểu:

* actor;
* roles/permissions nếu khả thi;
* request ID;
* correlation ID;
* active transaction context nếu test path có transaction.

---

## HTTP error isolation

```text
Request A
    ↓
throws
```

Sau đó:

```text
Request B
```

không được observe state của A.

---

## BullMQ

Cover:

* publisher propagation;
* explicit/default precedence;
* job root creation;
* Job A / Job B isolation;
* concurrent jobs;
* success cleanup;
* exception cleanup;
* actor không propagate;
* unrelated CLS state không propagate.

---

## CLI

Cover:

* system actor;
* audit actor;
* isolated command root;
* success cleanup;
* exception cleanup;
* no redundant root;
* nested system-scope parent restoration.

---

# Legacy cleanup

Sau migration:

* [ ] Xóa custom `AsyncLocalStorage`.
* [ ] Xóa runtime-context imports từ:

```ts
node:async_hooks
```

Search source:

```bash
grep -R \
  --include='*.ts' \
  --include='*.tsx' \
  "AsyncLocalStorage\|node:async_hooks" \
  apps libs
```

Expected:

```text
không còn custom AsyncLocalStorage implementation
```

Nếu có occurrence hợp lệ không thuộc migration này:

* không xóa máy móc;
* document exception.

---

# Consumer review

Search:

```bash
grep -R \
  "RequestContext\|CorrelationContext\|TypeOrmQueryRunnerContext" \
  apps libs \
  --exclude-dir=node_modules
```

Review tối thiểu:

```text
libs/modules/identity-access
libs/modules/user-profiles
libs/modules/media
libs/modules/catalog
libs/modules/product-catalog
libs/modules/card-catalog
libs/platform/queue

apps/api
apps/worker
apps/cli
apps/scheduler
apps/realtime
```

Ưu tiên giữ facade API để giảm regression surface.

Không refactor business consumer nếu migration không yêu cầu.

---

# Direct dependency validation

Scan toàn backend source:

```bash
grep -R \
  --include='*.ts' \
  "from ['\"]nestjs-cls['\"]" \
  apps libs
```

Allowed:

```text
libs/platform/context/**
explicit application composition/bootstrap files
```

Không allowed nếu không có documented exception:

```text
libs/modules/**
libs/platform/security/**
libs/platform/observability/**
libs/platform/database/**
libs/platform/queue/**
business application services
```

Platform facade cần CLS functionality phải depend vào:

```text
@memories/platform/context
```

không depend trực tiếp `nestjs-cls`.

---

# Acceptance criteria

## AC1 — Infrastructure

* `nestjs-cls` được tích hợp thành shared runtime context infrastructure.
* `libs/platform/context` không phụ thuộc:

  * security;
  * observability;
  * database;
  * TypeORM.
* Không có circular dependency mới.
* Không còn custom runtime `AsyncLocalStorage`.

---

## AC2 — Architecture boundary

Business modules không trực tiếp depend vào:

```text
nestjs-cls
ClsService
ClsModule
ClsServiceManager
```

Platform facade vẫn là dependency boundary chính.

---

## AC3 — Configuration ownership

Mỗi Nest application configure CLS root đúng một lần.

Reusable `libs/platform/context` không tự tạo global root configuration khi được import.

---

## AC4 — HTTP lifecycle

Mỗi HTTP request có một root CLS execution context.

Correlation/request middleware không tạo redundant root context.

Hai concurrent HTTP requests không thấy state của nhau.

---

## AC5 — CLS initializer configuration

HTTP CLS initialization:

* không tạo CLS-specific request ID;
* không persist raw request/response nếu không cần;
* không dùng `enterWith` nếu không có reproduced technical requirement;
* chạy trước context consumer.

---

## AC6 — IDs

Existing:

```text
requestId
correlationId
x-request-id
x-correlation-id
```

semantics không đổi.

Không có identifier thứ hai gây divergence giữa:

* logger;
* CLS;
* request;
* job envelope.

---

## AC7 — Correlation compatibility

Existing `CorrelationStore` semantics được giữ.

Nếu có `traceId`, migration:

* không làm mất;
* không tự thêm propagation mới;
* giữ nested/concurrent isolation.

---

## AC8 — Request/security context

Ba actor cases:

```text
system        => SYSTEM_ACTOR_ID
authenticated => accountId
anonymous     => null
```

vẫn đúng.

`JwtAuthGuard` enrich đúng current root request context.

Existing `RequestContextStore` shape không bị thay đổi ngoài phần implementation cần thiết.

---

## AC9 — Nested scopes

Explicit scoped APIs:

```text
CorrelationContext.run()
RequestContext.run()
runAsSystem()
```

nếu còn tồn tại phải:

* preserve unrelated slices;
* không mutate parent-owned contextual object;
* restore parent state;
* cleanup on exception;
* không phụ thuộc implicit nested policy của library.

---

## AC10 — Mutable state isolation

Nested contextual operation không để mutation tồn tại trong parent sau callback.

Được chứng minh tối thiểu với:

```text
runAsSystem()
RequestContext.run()
CorrelationContext.run()
```

cho cả:

```text
success
exception
```

---

## AC11 — UnitOfWork

`withTransaction()`:

* hoạt động với active parent CLS;
* hoạt động khi không có parent CLS;
* nested call reuse same `QueryRunner`;
* không mở transaction thứ hai;
* preserve correlation/request siblings;
* restore previous runner;
* không leak runner sau success/exception;
* concurrent transactions isolated.

---

## AC12 — Logger

Logger:

* không throw ngoài active CLS;
* sử dụng đúng request/correlation ID;
* không generate duplicate ID;
* không đọc chéo concurrent context;
* không phụ thuộc vào CLS trước khi CLS được initialize.

---

## AC13 — BullMQ

Publisher vẫn propagate `correlationId`.

Publisher giữ nguyên optional explicit `actorId` trong envelope nhưng không tự lấy actor từ
ambient `RequestContext`.

Mỗi worker job có independent root context.

Worker:

* restore correlation;
* không bind `envelope.actorId` hoặc HTTP actor vào ambient `RequestContext`;
* không propagate QueryRunner;
* không inherit previous job;
* cleanup success/failure.

---

## AC14 — CLI

Mỗi CLI command có isolated root context.

Audit actor vẫn là:

```text
SYSTEM_ACTOR_ID
```

Context cleanup sau success/failure.

Nested system scope không mutate parent state.

---

## AC15 — Other execution models

`scheduler` và `realtime` được rà soát.

Execution nào consume runtime context có root scope phù hợp.

Execution không consume context không bị thêm behavior ngoài scope.

---

## AC16 — Context infrastructure independence

`libs/platform/context` không biết:

```text
CorrelationStore
RequestContextStore
QueryRunner
TypeORM
```

Domain-specific contextual type thuộc owner tương ứng.

---

## AC17 — Context shape compatibility

Existing:

```text
CorrelationStore
RequestContextStore
```

observable shape/semantics không bị thay đổi ngoài phần implementation bắt buộc cho migration.

Không vô tình xóa:

```text
traceId
requestId
correlationId
```

hoặc mirrored metadata đang có consumer.

---

## AC18 — Characterization baseline

Mọi characterization test liên quan behavior chưa explicit phải:

1. pass trên legacy ALS implementation;
2. pass lại sau migration.

Không dùng post-migration behavior làm baseline giả định cho legacy semantics.

---

## AC19 — Quality gate

Pass:

* characterization tests;
* unit tests;
* relevant integration tests;
* HTTP E2E (`npm run test:e2e`, chạy trên PostgreSQL/Redis/MinIO thật — không mock/stub hạ tầng,
  theo Definition of Done);
* lint;
* typecheck;
* build;
* `npm run test:architecture` (depcruise) — bao gồm rule mới cho `libs/platform/context`.

Không có observable regression so với implementation trước migration.

---

## AC20 — Background actor compatibility

Các behavior sau được khóa bằng test:

* publish không truyền `actorId` thì `envelope.actorId` vẫn `undefined`;
* publish có explicit `options.actorId` thì giá trị được giữ nguyên;
* worker nhận envelope có `actorId` vẫn không có ambient request/security actor;
* worker restore đúng `correlationId`;
* concurrent jobs không leak correlation hoặc request/security state.

---

## AC21 — Documentation consistency

* Không còn tài liệu/comment nói CLI system actor được stamp `null`.
* Phân biệt rõ anonymous actor (`null`), CLI system actor (`SYSTEM_ACTOR_ID`) và worker không có
  restored `RequestContext` (`null` khi đọc ambient actor).
* Optional `BackgroundJobEnvelope.actorId` không được mô tả như ambient actor đã được restore.

---

## AC22 — Handoff và integration status

Bàn giao implementation phải ghi rõ:

* target repository, base branch và base SHA;
* exact worktree/revision đã chạy validation;
* implementation mới chỉ nằm trong feature worktree hay đã được tích hợp vào target branch;
* review verdict và user acceptance hiện tại.

Nếu đã tích hợp vào target branch, phải re-verify tại chính `apps/backend`:

* có dependency `nestjs-cls` và `libs/platform/context`;
* không còn custom runtime `AsyncLocalStorage`;
* application roots có đúng một CLS root configuration theo execution model;
* relevant test, lint, typecheck, build và architecture checks pass.

Nếu chưa tích hợp, báo cáo không được dùng từ ngữ hàm ý `apps/backend/master` đã hoàn tất migration.

---

# Out of scope

* Thay đổi `BackgroundJobEnvelope`.
* Thay đổi publisher/worker contract.
* Propagate HTTP actor sang background job.
* Tự động bind `BackgroundJobEnvelope.actorId` vào ambient `RequestContext` của worker.
* Propagate `QueryRunner` sang background job.
* Tự thêm `traceId` propagation.
* Thêm context field mới không cần cho migration.
* Xóa duplicated context field chỉ để normalize model.
* Thay đổi `SYSTEM_ACTOR_ID`.
* Thay đổi auth/RBAC semantics.
* Refactor `PermissionsGuard` / `ThrottlerGuard` ngoài integration bắt buộc.
* Refactor business repositories không liên quan.
* Upgrade NestJS.
* Thay database transaction abstraction.
* Thay `TypeOrmUnitOfWork` bằng `@nestjs-cls/transactional`.
* Introduce transaction propagation semantics mới.
* Refactor frontend.
* Thay đổi service ngoài backend.

---

# Relevant files

## New context platform

```text
libs/platform/context/**
tsconfig.json
apps/backend/package.json
apps/backend/package-lock.json
```

## Observability

```text
libs/platform/observability/src/correlation-context.ts
libs/platform/observability/src/correlation.middleware.ts
libs/platform/observability/src/logger.module.ts
libs/platform/observability/src/observability.module.ts

libs/platform/observability/test/correlation-context.spec.ts
libs/platform/observability/test/logger.module.spec.ts
```

## Security

```text
libs/platform/security/src/request-context.ts
libs/platform/security/src/request-context.middleware.ts
libs/platform/security/src/security.module.ts
libs/platform/security/src/jwt-auth.guard.ts

libs/platform/security/test/jwt-auth.guard.spec.ts
libs/platform/security/test/request-context.spec.ts
```

## Database

```text
libs/platform/database/src/typeorm-unit-of-work.ts
libs/platform/database/src/database.module.ts

libs/platform/database/test/typeorm-unit-of-work.spec.ts
```

## Queue

```text
libs/platform/queue/src/bullmq/bullmq.publisher.ts
libs/platform/queue/src/bullmq/bullmq.worker.ts
```

## Applications

```text
apps/api/**
apps/worker/**
apps/cli/**
apps/scheduler/**
apps/realtime/**
```

---

# Expected architecture

```text
                nestjs-cls infrastructure
                         │
                         ▼
                platform/context
                         │
            generic typed context API
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
  observability      security       database
          │              │              │
 CorrelationStore  RequestContext   QueryRunner
```

Dependency direction:

```text
business modules
      │
      ▼
platform facade
      │
      ▼
platform/context
      │
      ▼
nestjs-cls
```

---

# Expected HTTP lifecycle

```text
HTTP request
      │
      ▼
CLS root
      │
      ▼
Correlation seed
      │
      ▼
RequestContext seed
      │
      ▼
JwtAuthGuard enrich
      │
      ▼
Controller
      │
      ▼
UseCase
      │
      ▼
UnitOfWork
      │
      ▼
Repository
```

---

# Expected BullMQ lifecycle

```text
HTTP
 │
 └── publish correlation metadata
               │
               ▼
       BackgroundJobEnvelope
               │
               ▼
         BullMQ worker
               │
               ▼
        independent CLS root
               │
               ├── restore correlation
               └── no HTTP actor
               │
               ▼
           processor
```

---

# Expected CLI lifecycle

```text
CLI command
    │
    ▼
CLS root
    │
    ▼
runAsSystem()
    │
    ▼
UseCase
    │
    ▼
Repository
```

---

# Implementation principles

1. Migration trước, improvement sau.
2. Preserve behavior trước khi refactor API.
3. Một root context cho mỗi independent execution.
4. Nested scope phải explicit.
5. Không rely vào library defaults cho compatibility-sensitive behavior.
6. Context domain phải namespaced.
7. Generic context infrastructure không biết domain technology.
8. Temporary state phải restore.
9. Cleanup phải exception-safe.
10. Business layer không biết `nestjs-cls`.
11. Không tạo dependency cycle chỉ để đạt compile-time typing.
12. Không duplicate ID source.
13. UnitOfWork không được phụ thuộc bắt buộc vào HTTP/request CLS.
14. Actor propagation sang background job là feature riêng.
15. Transaction architecture hiện tại được giữ nguyên.
16. Root enrichment và nested override có mutation semantics khác nhau.
17. Không shallow-inherit mutable slice rồi mutate nếu parent phải được restore.
18. Characterization phải chứng minh legacy behavior trước migration.
19. CLS root configuration thuộc application composition root.
20. Library defaults không được trở thành application contract một cách vô tình.
21. Không refactor observable context shape chỉ vì migration cho phép implementation sạch hơn.

---

# Validation

Chạy các script tương ứng tồn tại trong backend, tối thiểu:

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run test:architecture
```

`npm run test:architecture` (`depcruise --config .dependency-cruiser.js apps libs`) là gate kiến
trúc chính thức của dự án (`ai/repos/backend/architecture.md`) — bắt buộc, không phải optional,
đặc biệt vì task này thêm rule mới cho `libs/platform/context` (xem Scope > "2. Platform context
infrastructure").

Nếu test scripts chia theo project/lib thì chạy thêm suite liên quan:

```text
platform/context
platform/observability
platform/security
platform/database
platform/queue
apps/api e2e
```

## E2E trên hạ tầng thật

`ai/shared/quality/definition-of-done.md` yêu cầu `npm run test:e2e` (tại `apps/backend`) phải
chạy thật với PostgreSQL/Redis/MinIO (qua `docker/docker-compose.yml` hoặc container throwaway
tương đương) — **không được coi là đạt nếu chỉ pass với mock/stub hạ tầng**. Yêu cầu này đặc biệt
quan trọng cho task này vì AC7/AC11 (concurrent transaction isolation, reentrant transaction) và
AC13 (BullMQ job isolation) là loại behavior mock `QueryRunner`/mock Redis dễ che giấu race
condition thật — timing của `AsyncLocalStorage`/`nestjs-cls` dưới tải Postgres/Redis thật khác với
mock. Không được coi migration là pass chỉ dựa trên unit test dùng `fakeQueryRunner`/mock BullMQ.

---

## Check legacy ALS

```bash
grep -R \
  --include='*.ts' \
  --include='*.tsx' \
  "AsyncLocalStorage\|node:async_hooks" \
  apps libs
```

Expected:

```text
no custom runtime AsyncLocalStorage implementation
```

Document legitimate unrelated occurrence thay vì xóa máy móc.

---

## Check direct `nestjs-cls` dependency

```bash
grep -R \
  --include='*.ts' \
  "from ['\"]nestjs-cls['\"]" \
  apps libs
```

Allowed:

```text
libs/platform/context/**
explicit application composition/bootstrap files
```

Expected không có direct dependency trong:

```text
libs/modules/**
libs/platform/security/**
libs/platform/observability/**
libs/platform/database/**
libs/platform/queue/**
```

trừ documented exception.

---

## Check consumer

```bash
grep -R \
  "RequestContext\|CorrelationContext\|TypeOrmQueryRunnerContext" \
  apps libs \
  --exclude-dir=node_modules
```

---

## Knowledge update timing

`ai/domains/request-context` chỉ được chuyển từ mô tả `legacy`/`proposed` sang `implemented` sau
khi implementation đã được review và tích hợp vào repository/branch đích. Nếu thay đổi mới tồn
tại trong feature worktree, knowledge update phải ghi rõ trạng thái này.

Khi cập nhật domain documentation, phải giữ chính xác boundary:

```text
anonymous HTTP actor              => null
CLI system actor                  => SYSTEM_ACTOR_ID
worker without restored context   => null
explicit envelope.actorId         => metadata, not ambient actor
```

Đảm bảo toàn bộ existing consumer đã được review.

---

## Check architecture boundaries (depcruise)

```bash
npm run test:architecture
```

Chạy `depcruise --config .dependency-cruiser.js apps libs`. Rule `no-circular` (global) bắt mọi
cycle mới, kể cả giữa:

```text
platform/context
platform/observability
platform/security
platform/database
```

Rule dedicated cho `libs/platform/context` (thêm ở Scope > "2. Platform context infrastructure")
xác nhận lib này không import `security`/`observability`/`database`/`typeorm`. 5 rule gốc trong
`.dependency-cruiser.js` (`domain-no-framework-dependency`, `domain-no-outer-layer-dependency`,
`application-no-infrastructure-or-presentation-dependency`, `no-cross-module-internal-import`,
`no-direct-bullmq-dependency-in-business-module`) chỉ scope `libs/modules/*`, không tự động phủ
`libs/platform/*` — đây là lý do phải thêm rule mới thay vì giả định check hiện có đã đủ.

---

# Constraints

* Không quản lý worktree/branch.
* Không commit.
* Không push.
* Không đọc secret.
* Không sửa ngoài worktree khai báo.
* Không upgrade NestJS.
* Không thay transaction architecture.
* Không thêm business behavior ngoài migration scope.
* Không thay đổi public context semantics nếu chưa có characterization test chứng minh.
* Không mở rộng task thành refactor architecture ngoài runtime context migration.
