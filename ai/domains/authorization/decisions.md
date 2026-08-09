# Authorization (Portal + RBAC) — Decisions

Chỉ ghi quyết định đã được xác nhận và có giá trị lâu dài.

## DEC-001 — Portal access được kiểm soát bằng permission (RBAC), không hard-code role

- Trạng thái: Accepted
- Bối cảnh: Hai ứng dụng `public-web` và `admin-web` dùng chung một Account; cần một cơ chế xác định Account có được vào từng portal hay không mà không gắn cứng logic theo role trong từng use case/controller (`ai/tasks/MEMORIES-0002/task.md` §10).
- Quyết định: Backend tự map `portal` (`PUBLIC`/`ADMIN`) sang permission cố định (`portal.public.access`, `portal.admin.access`) và kiểm tra qua port `PermissionChecker.hasPermissions(userId, permissions[])` đã có sẵn tại `libs/platform/security/src/authorization.contract.ts`. Login use case và các API khác đều dùng chung port này (qua `RequirePermissions` decorator + `PermissionsGuard` cho route, gọi trực tiếp port cho login).
- Lý do kỹ thuật theo source: Port `PermissionChecker`, decorator `RequirePermissions` và `PermissionsGuard` đã tồn tại trong `libs/platform/security`, được thiết kế để module khác chỉ phụ thuộc qua DI token `PERMISSION_CHECKER`, không import trực tiếp `identity-access`. Tận dụng lại port này tránh tạo thêm một cơ chế kiểm tra quyền song song.
- Hệ quả: Module `identity-access` phải implement `PermissionChecker` (Role → Permission qua `AccountRole`/`RolePermission`); mọi route Account/UserProfile phải khai báo `@RequirePermissions(...)`; không controller hoặc use case nào được phép so sánh role trực tiếp.

## DEC-002 — Portal là claim bắt buộc trên token/session, không dùng chung token giữa các portal

- Trạng thái: Accepted
- Bối cảnh: Một Account có thể có quyền truy cập một hoặc cả hai portal; cần đảm bảo token phát cho `PUBLIC` không thể dùng để gọi admin API (`ai/tasks/MEMORIES-0002/task.md` §13, AC #22, #23).
- Quyết định: `RefreshSession` gắn với một portal cụ thể; JWT payload bổ sung claim `portal` bên cạnh `sub`, `sessionId`, `userProfileId`, `authProvider`. `TokenClaims` hiện tại (`libs/platform/security/src/token.contract.ts`) chỉ có `subject` + claim tuỳ ý nên cho phép mở rộng mà không phá cấu trúc port hiện có.
- Lý do kỹ thuật theo source: `TokenService`/`TokenClaims` được thiết kế generic (`[claim: string]: unknown`), không cần thay đổi contract, chỉ cần identity-access truyền thêm claim khi issue token.
- Hệ quả: Guard/middleware xử lý request phải kiểm tra claim `portal` khớp với portal của route trước khi coi token hợp lệ; một Account có thể có nhiều `RefreshSession` song song cho các portal/thiết bị khác nhau; khoá hoặc xoá Account phải revoke toàn bộ session bất kể portal.

## DEC-003 — Role và Permission dùng code ổn định, CRUD Role/Permission hoàn chỉnh nằm ngoài phạm vi epic

- Trạng thái: Accepted
- Bối cảnh: Cần nền tảng RBAC tối thiểu để phục vụ portal authorization và bảo vệ API Account/UserProfile, nhưng chưa cần giao diện quản trị Role/Permission đầy đủ (`ai/tasks/MEMORIES-0002/task.md` §12, mục "Out of scope").
- Quyết định: Role và Permission dùng code dạng `resource.action` làm business identifier (không dùng display name); seed Role/Permission mặc định (`PUBLIC_USER`, `ADMIN`, `SUPER_ADMIN`, danh sách permission tối thiểu) phải idempotent; không xây CRUD Role/Permission hoàn chỉnh hay UI quản trị trong epic này.
- Lý do kỹ thuật theo source: Module `identity-access` hiện chỉ là scaffolding (domain/application/infrastructure/presentation rỗng), phù hợp để giới hạn phạm vi triển khai ở mức nền tảng, tránh xây dựng thừa trước khi có nhu cầu quản trị Role/Permission thực tế.
- Hệ quả: Việc gán role cho Account mới dùng default role cấu hình sẵn (không hard-code trong use case); các tác vụ quản trị Role/Permission (tạo, sửa, xoá qua UI) để lại cho epic sau.
