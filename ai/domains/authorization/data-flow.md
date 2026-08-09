# Authorization (Portal + RBAC) — Data Flow

```text
Login request (phone + password + portal)
  → Authentication (LOCAL AuthIdentity: verify password, check Account status)
  → Resolve Role/Permission của Account (AccountRole → RolePermission → Permission)
  → Map portal sang permission cần kiểm tra (PUBLIC → portal.public.access, ADMIN → portal.admin.access)
  → PermissionChecker.hasPermissions(accountId, [permissionCode])  (port tại libs/platform/security, implement bởi identity-access)
      ├─ Có quyền  → tạo RefreshSession (gắn portal) → phát access token (memory) + refresh token (cookie HttpOnly)
      └─ Thiếu quyền → không tạo session, không phát token → trả lỗi 403

Protected request (đã có access token)
  → JwtAuthGuard xác thực Account từ token (gắn request.user qua TokenService)
  → PermissionsGuard đọc metadata từ @RequirePermissions(...) trên route → gọi PermissionChecker.hasPermissions
      ├─ Đủ quyền → vào application/use case
      └─ Thiếu quyền → chặn request, trả lỗi 403
```

- Luồng nghiệp vụ chi tiết: authentication và portal authorization tách rời rõ ràng (xem `ai/tasks/MEMORIES-0002/task.md` §10) — login use case không tự kiểm tra role, chỉ gọi cùng port `PermissionChecker` dùng chung với các API khác (`libs/platform/security/src/authorization.contract.ts`, đã tồn tại trong source).
- Module, database, queue hoặc service thực tế: `PermissionChecker`/`PermissionsGuard`/`RequirePermissions` đã có sẵn tại `libs/platform/security`; Role/Permission/AccountRole/RolePermission sẽ được triển khai trong `domain/roles`, `domain/permissions` của module `identity-access` (hiện là scaffolding rỗng); bảng `identity.roles`, `identity.permissions`, `identity.account_roles`, `identity.role_permissions` (chưa có migration); request context bằng AsyncLocalStorage/`nestjs-cls` hoặc abstraction tương đương của dự án (chưa có trong source).
- Transaction, idempotency và concurrency: resolve permission là thao tác đọc, không cần transaction riêng; seed Role/Permission phải idempotent (chạy nhiều lần không tạo trùng); hai request đồng thời không được lẫn permission/context của nhau (mỗi request có context riêng biệt).
