# Authorization (Portal + RBAC) — Workflow

## Trạng thái mẫu

```text
authenticated → permission-resolved → portal-check
                                          ├──→ authorized   (issue token + refresh session)
                                          └──→ unauthorized (403, no token, no session)
```

Các trạng thái, điều kiện chuyển và hành vi retry thực tế:

- `authenticated`: Account đã qua bước authentication (LOCAL AuthIdentity hợp lệ, Account status `ACTIVE`). Chưa có quyền truy cập portal ở bước này.
- `permission-resolved`: Role và Permission của Account đã được resolve qua `AccountRole` → `RolePermission`.
- `portal-check`: so khớp permission đã resolve với permission yêu cầu của portal (`portal.public.access` hoặc `portal.admin.access`).
- `authorized`: Account có permission tương ứng → tạo `RefreshSession` gắn với portal, phát access token (memory) và refresh token (cookie `HttpOnly`).
- `unauthorized`: Account thiếu permission → không tạo session, không phát token, trả lỗi `403`; không có cơ chế retry tự động, người dùng phải được cấp quyền qua quy trình quản trị Role/Permission (ngoài phạm vi epic này).
- Với mọi request tới API được bảo vệ (không riêng login): guard/decorator resolve permission từ request context, chặn ngay nếu thiếu quyền, không rơi vào state xử lý nghiệp vụ.
- Account bị khoá/xoá trong khi đang có session hợp lệ: toàn bộ session hiện tại bị revoke (chuyển về trạng thái tương đương `unauthorized` cho các request tiếp theo).

Cách biểu diễn trạng thái trong source: enum `Portal` (`PUBLIC`, `ADMIN`) cần bổ sung vào request DTO và `TokenClaims` (`libs/platform/security/src/token.contract.ts` hiện chỉ có `subject` + claim tuỳ ý, chưa có `portal`); permission code dạng chuỗi ổn định (`resource.action`) kiểm tra qua `PermissionChecker.hasPermissions` (đã có sẵn tại `libs/platform/security/src/authorization.contract.ts`); Role/Permission/AccountRole/RolePermission là bảng liên kết sẽ nằm trong `identity.roles`, `identity.permissions`, `identity.account_roles`, `identity.role_permissions` (chưa có migration), không dùng cờ boolean rời rạc để biểu diễn quyền.
