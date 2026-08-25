# Request Context — Decisions

Chỉ ghi quyết định đã được xác nhận và có giá trị lâu dài.

## DEC-001 — Gộp 3 `AsyncLocalStorage` độc lập thành 1 `ClsStore` của `nestjs-cls`

- Trạng thái: Proposed (chưa triển khai — task `MEMORIES-0006`)
- Bối cảnh: `CorrelationContext` (observability), `RequestContext` (security),
  `TypeOrmQueryRunnerContext` (database) mỗi cái tự mở một `AsyncLocalStorage` static riêng,
  không chia sẻ store. `RequestContextMiddleware` phải đọc lại `CorrelationContext.current()`
  thủ công để tránh sinh cặp requestId/correlationId thứ hai — một dấu hiệu 3 store này về bản
  chất cùng vòng đời (một request/job/lệnh CLI) nhưng bị tách rời không cần thiết.
- Quyết định: Migrate cả 3 sang `nestjs-cls`, dùng chung một `ClsService`/`ClsStore`. Giữ nguyên
  chữ ký API public (`run/get/currentActorId/runAsSystem` của `RequestContext`,
  `run/current/requestId/correlationId` của `CorrelationContext`, `run/get` của
  `TypeOrmQueryRunnerContext`) để không phải sửa ~40 file consumer trong `libs/modules/*`.
- Lý do kỹ thuật theo source: `nestjs-cls` là thư viện chuẩn cộng đồng NestJS cho continuation-local
  storage, cung cấp `ClsServiceManager.getClsService()` cho các call site ngoài DI (đúng nhu cầu của
  `logger.module.ts`'s `genReqId`/`customProps`), và tránh việc mỗi platform lib mới lại tự viết một
  `AsyncLocalStorage` riêng khi cần context mới trong tương lai.
- Hệ quả: Ranh giới BullMQ worker đã được chốt rõ trong `task.md` (Out of scope + acceptance
  criteria #16): migration này KHÔNG propagate actor từ HTTP request sang job nền — mỗi job chỉ
  khôi phục `correlationId` từ `BackgroundJobEnvelope`, không khôi phục `RequestContext`/actor.
  Nếu tương lai cần actor propagation cho job, đó là một feature/task riêng, không phải phạm vi
  của `MEMORIES-0006` (đổi audit/security semantics). Xem thêm DEC-002 (vị trí `libs/platform/
  context` và ranh giới không biết domain type) và DEC-003 (`ClsModule.forRoot()` thuộc composition
  root) để tránh vòng lặp dependency giữa observability/security/database.

## DEC-002 — Tạo lib mới `libs/platform/context` làm nơi duy nhất import `nestjs-cls`; KHÔNG đặt một `ApplicationClsStore` type gộp cụ thể ở đó, kể cả cho slice `database`

- Trạng thái: Proposed (chưa triển khai — task `MEMORIES-0006`)
- Bối cảnh: Dependency graph hiện tại: `security → observability` (một chiều, để đọc
  `CorrelationContext`), `security → shared/kernel`, `database → shared/kernel`; `observability`
  và `database` không phụ thuộc lẫn nhau hoặc phụ thuộc `security`. `libs/shared/kernel` là lib
  framework-agnostic thuần domain primitives, không có import `@nestjs/*` nào — không phù hợp để
  đăng ký một NestJS module (`ClsModule`).
- Quyết định (đã sửa lại lần 2 — xem "Lý do đổi" bên dưới): Tạo lib platform mới
  `libs/platform/context` (alias `@memories/platform/context`) sở hữu dependency `nestjs-cls`. Đây
  là nơi DUY NHẤT trong platform layer import trực tiếp `ClsService`/`ClsModule`/
  `ClsServiceManager`. Lib này CHỈ cung cấp cơ chế generic — typed namespaced slice (typed key /
  facade / TypeScript module augmentation, kỹ thuật cụ thể để ngỏ cho execution-plan) — KHÔNG tự
  định nghĩa bất kỳ concrete domain type nào, kể cả `QueryRunner`. `platform/context` không được
  import `typeorm`, `CorrelationStore` (owned bởi `observability`), hay `RequestContextStore`
  (owned bởi `security`) dưới bất kỳ hình thức nào. Mỗi domain lib tự sở hữu type slice của mình
  và tự bind vào cơ chế generic đó. Việc đăng ký `ClsModule.forRoot()` KHÔNG thuộc lib này — xem
  DEC-003.
- Lý do đổi (lần 2, so với bản DEC-002 trước): bản trước cho phép một ngoại lệ — type cụ thể
  `QueryRunner` được `platform/context` import trực tiếp từ `typeorm` vì đó là type của package
  bên thứ ba, không phải type do `libs/platform/database` định nghĩa, nên "không tạo dependency
  edge tới lib `database`". Lý lẽ đó đúng về mặt *dependency edge* nhưng bỏ sót một nguyên tắc
  rộng hơn: `platform/context` là lớp hạ tầng generic, có trách nhiệm không biết bất kỳ công nghệ
  cụ thể nào ở tầng domain (kể cả một ORM) — nếu dự án đổi ORM sau này, một lib lẽ ra phải
  agnostic-với-công-nghệ lại buộc phải sửa theo. Task `task.md` (Architecture decisions #3, dòng
  249–286) đã sửa đúng: cấm `platform/context` biết `typeorm`/`QueryRunner` tuyệt đối, không có
  ngoại lệ nào — slice `database` cũng phải bind qua cùng cơ chế generic (typed key/facade) như
  `correlation`/`request`.
- Lý do kỹ thuật theo source: tránh tạo dependency edge mới hoặc vòng lặp giữa 3 lib platform vốn
  độc lập với nhau; giữ `libs/shared/kernel` framework-agnostic; giữ lớp hạ tầng CLS agnostic với
  mọi công nghệ domain (kể cả ORM); đúng convention `src/public-api.ts` đã dùng cho mọi platform
  lib khác trong repo.
- Hệ quả: `libs/platform/context` không được phụ thuộc ngược lại `security`/`observability`/
  `database`, và cũng không được import `typeorm` — không có ngoại lệ. Facade public
  (`CorrelationContext`, `RequestContext`, `TypeOrmQueryRunnerContext`) giữ nguyên tên/chữ ký, chỉ
  đổi implementation nội bộ — business modules trong `libs/modules/*` không cần và không được
  import `@memories/platform/context` trực tiếp.

## DEC-003 — `ClsModule.forRoot()` thuộc application composition root (`apps/*/src/app.module.ts`), không thuộc `libs/platform/context`

- Trạng thái: Proposed (chưa triển khai — task `MEMORIES-0006`)
- Bối cảnh: `nestjs-cls` khuyến cáo (official docs) rằng `ClsModule.forRoot()`/`forRootAsync()` là
  global configuration, nên đăng ký một lần tại root module của application — không đặt bên trong
  một reusable library được import từ nhiều nơi, vì library không phải là nơi ra quyết định cấu
  hình toàn ứng dụng.
- Quyết định (sửa lại so với DEC-002 bản đầu tiên, vốn ghi "platform/context ... đăng ký
  `ClsModule.forRoot()`"): `libs/platform/context` chỉ export abstraction (`RuntimeContextService`/
  `RuntimeContextAccessor`/tương đương) và import `ClsModule` theo cách KHÔNG tự tạo root
  configuration. Từng Nest application (`apps/api`, `apps/worker`, `apps/cli`, và `apps/scheduler`/
  `apps/realtime` nếu thực sự dùng runtime context) tự gọi `ClsModule.forRoot()` đúng một lần tại
  composition root của mình.
- Lý do kỹ thuật theo source: đúng khuyến cáo chính thức của `nestjs-cls`; tránh tình huống
  `platform/context` được nhiều lib platform khác import mà vô tình kích hoạt nhiều root
  configuration độc lập trong cùng một Nest application nếu module resolution không dedupe đúng
  cách.
- Hệ quả: mỗi application phải tự chịu trách nhiệm gọi `ClsModule.forRoot()` một lần — không giả
  định `apps/api` cần nhưng `apps/worker`/`apps/cli` thì không; xem thêm `task.md` phần "Module
  registration" và AC3.
