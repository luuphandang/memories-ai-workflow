# Authorization (Portal + RBAC) — Overview

## Mục tiêu

Xác định Account có được truy cập một portal cụ thể (`public-web` hoặc `admin-web`) hay không, dựa trên permission được resolve từ Role của Account, thay vì hard-code theo role hoặc theo từng ứng dụng.

## Phạm vi nghiệp vụ

- Một Account có thể truy cập public, admin, cả hai, hoặc không portal nào, tuỳ theo permission hiện có.
- Backend tự map portal (`PUBLIC`/`ADMIN`) sang permission tương ứng, client không được truyền permission cần kiểm tra.
- Portal authorization chỉ được thực hiện sau khi authentication (xác thực phone + password) đã thành công.
- Nếu Account không có permission truy cập portal: không tạo refresh session, không phát access token.
- RBAC foundation gồm Role, Permission, AccountRole, RolePermission; Role chỉ là tập hợp các permission, không mang logic riêng.
- Request context lưu roles/permissions đã resolve để dùng xuyên suốt vòng đời request.
- CRUD Role/Permission hoàn chỉnh và giao diện quản trị Role/Permission nằm ngoài phạm vi epic này.

## Thành phần source liên quan

- `libs/platform/security` (đã có sẵn, dùng chung toàn hệ thống):
  - `authorization.contract.ts`: `RequirePermissions(...permissions)` decorator, `PermissionsGuard`, port `PermissionChecker.hasPermissions(userId, permissions[])`, DI token `PERMISSION_CHECKER`. `PermissionChecker` được implement bởi module `identity-access`, các module khác chỉ thấy port này qua DI.
  - `jwt-auth.guard.ts` + `token.contract.ts`: `JwtAuthGuard` xác thực bearer token qua `TokenService`, gắn `request.user = { id: subject }`; `TokenClaims` hiện chỉ có `subject` + claim tuỳ ý — cần bổ sung claim `portal`, `sessionId`, `userProfileId` theo epic này (§13).
  - `current-user.decorator.ts`: `CurrentUser` đọc `request.user`, dùng sau `JwtAuthGuard`.
  - `refresh-cookie.helper.ts`: helper set/đọc refresh token cookie `HttpOnly`.
- Module `identity-access` (`libs/modules/identity-access/src`): hiện mới có scaffolding (`domain/`, `application/`, `infrastructure/`, `presentation/` với README ràng buộc Clean Architecture, enforced bởi `npm run test:architecture`) và `identity-access.module.ts` rỗng — Role, Permission, AccountRole, RolePermission, portal authorization use case sẽ được triển khai trong domain/application của module này.
- Request context (AsyncLocalStorage/`nestjs-cls` hoặc tương đương) chứa `portal`, `roles`, `permissions` — chưa tồn tại trong source, cần triển khai mới (§14).
- Login use case (module `identity-access`) gọi qua `PermissionChecker.hasPermissions(accountId, [permission])` (interface hiện có nhận mảng permission, không phải một permission đơn lẻ) sau bước authentication, trước khi tạo `RefreshSession`.

## Thuật ngữ

| Thuật ngữ | Mô tả |
|---|---|
| Portal | Ứng dụng client thực hiện đăng nhập: `PUBLIC` (public-web) hoặc `ADMIN` (admin-web). |
| Permission | Định danh quyền ổn định, dạng `resource.action`, ví dụ `portal.admin.access`, `account.read`. |
| Role | Tập hợp các Permission, gán cho Account qua `AccountRole`. Dùng code ổn định, không dùng display name làm business identifier. |
| AccountRole | Bảng liên kết Account với Role (một Account có thể có nhiều Role). |
| RolePermission | Bảng liên kết Role với Permission (một Role có thể có nhiều Permission). |
| Portal authorization | Bước kiểm tra Account đã xác thực có permission `portal.<portal>.access` tương ứng hay không, thực hiện trước khi phát token. |
| Permission evaluator/policy | Thành phần resolve và kiểm tra permission của Account, dùng chung cho guard/decorator trên các API. |
