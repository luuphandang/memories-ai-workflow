# Authorization (Portal + RBAC) — API Contract

## Endpoint/interface

- Method/event: Application-level port call (không phải REST endpoint riêng) — `PermissionChecker.hasPermissions(userId, permissions[]): Promise<boolean>`, port đã có sẵn tại `libs/platform/security/src/authorization.contract.ts` (DI token `PERMISSION_CHECKER`). Login use case và `PermissionsGuard` (qua decorator `RequirePermissions(...permissions)`) đều gọi qua port này; `identity-access` chịu trách nhiệm implement port.
- Path/topic: Không có route HTTP riêng trong epic này (CRUD Role/Permission hoàn chỉnh nằm ngoài phạm vi — xem `ai/tasks/MEMORIES-0002/task.md` mục "Out of scope"). Portal authorization được nhúng vào luồng `POST /auth/login` (route login cụ thể do module authentication định nghĩa, chưa tồn tại trong source hiện tại).
- Module triển khai hiện tại: `identity-access` (`domain/roles`, `domain/permissions`, `application` — implement `PermissionChecker`, `presentation` — controller dùng `@RequirePermissions(...)`); port/guard/decorator dùng chung nằm ở `libs/platform/security`.

## Request

Payload login (chứa `portal` để xác định permission cần kiểm tra, không chứa permission trực tiếp):

```json
{
  "phone": "0912345678",
  "password": "...",
  "portal": "ADMIN"
}
```

- `portal`: enum bắt buộc, chỉ nhận `PUBLIC` hoặc `ADMIN`. Không cho client tự truyền permission code.

## Response

Thành công (đã qua authentication và portal authorization):

```json
{
  "accessToken": "...",
  "portal": "ADMIN",
  "sessionId": "...",
  "roles": ["ADMIN"],
  "permissions": ["portal.admin.access", "account.read", "user-profile.read"]
}
```

- Refresh token không xuất hiện trong response body, được set qua cookie `HttpOnly`.
- Không trả `passwordHash` hoặc credential dưới bất kỳ hình thức nào.

Interface kiểm tra permission dùng nội bộ (đã tồn tại trong `libs/platform/security`, dùng cho cả login use case và guard trên controller):

```ts
// Decorator trên controller (presentation layer):
@RequirePermissions('portal.admin.access')

// Port được identity-access implement, gọi qua DI (PERMISSION_CHECKER):
permissionChecker.hasPermissions(accountId, ['portal.admin.access']);
```

## Error mapping

| Điều kiện | Mã lỗi | Hành vi |
|---|---|---|
| Phone không tồn tại hoặc password sai | `401 Unauthorized` (thông điệp generic, không phân biệt hai trường hợp) | Không tạo refresh session, không phát access token. |
| Account đang `INACTIVE`, `LOCKED` hoặc đã bị xoá | `403 Forbidden` | Từ chối đăng nhập; không phát token; không tạo refresh session. |
| Authentication hợp lệ nhưng Account thiếu permission `portal.<portal>.access` | `403 Forbidden` | Không tạo refresh session, không phát access token, trả lỗi phân biệt rõ với lỗi sai credential. |
| Gọi API được bảo vệ nhưng Account thiếu permission tương ứng (ví dụ `account.read`) | `403 Forbidden` | Guard/decorator chặn request trước khi vào handler; không thực thi use case. |
| Access token dùng để gọi API khác portal/audience (ví dụ token `PUBLIC` gọi admin API) | `403 Forbidden` | Từ chối request; không coi token hợp lệ mặc nhiên giữa các portal. |
