# Authorization (Portal + RBAC) — Business Rules

| ID | Quy tắc | Nguồn xác nhận | Trạng thái |
|---|---|---|---|
| BR-001 | Backend tự map portal sang permission: `PUBLIC → portal.public.access`, `ADMIN → portal.admin.access`. Client không được truyền permission cần kiểm tra. | Jira MEMORIES-0002 §9, §10 | Đã xác nhận |
| BR-002 | Portal authorization chỉ thực hiện sau khi authentication (credential) đã hợp lệ; nếu Account thiếu permission portal thì không tạo refresh session và không phát access token. | Jira MEMORIES-0002 §9, §10, AC #15 | Đã xác nhận |
| BR-003 | Role chỉ là nhóm các Permission, không chứa logic nghiệp vụ riêng; Role và Permission dùng code ổn định làm business identifier, không dùng display name. | Jira MEMORIES-0002 §12, AC #17 | Đã xác nhận |
| BR-004 | Không hard-code role trong login use case hoặc controller (ví dụ cấm `if (role === 'ADMIN')`); mọi kiểm tra truy cập portal phải qua port `PermissionChecker.hasPermissions(accountId, ['portal.admin.access'])` đã có sẵn tại `libs/platform/security`, hoặc qua decorator `@RequirePermissions(...)` + `PermissionsGuard` cho các route khác. | Jira MEMORIES-0002 §10, AC #16 | Đã xác nhận |
| BR-005 | Có default role gán cho Account public khi tạo mới; default role được cấu hình, không hard-code trong use case. | Jira MEMORIES-0002 §12 | Đã xác nhận |
| BR-006 | Mọi API Account và UserProfile phải khai báo permission yêu cầu; không controller nào hard-code role để kiểm tra quyền truy cập. | Jira MEMORIES-0002 §12 | Đã xác nhận |
| BR-007 | Request context phải chứa Role và Permission đã resolve của Account cho request hiện tại, không resolve lại nhiều lần không cần thiết trong cùng request. | Jira MEMORIES-0002 §12, §14 | Đã xác nhận |
| BR-008 | Nếu permission có thể thay đổi trong khi token còn hạn, phải có cơ chế token version, permission version, hoặc resolve lại permission ở protected request. | Jira MEMORIES-0002 §13 | Đã xác nhận |
| BR-009 | Token phát cho portal `PUBLIC` không được mặc nhiên hợp lệ để truy cập portal `ADMIN`; Admin API phải kiểm tra đúng audience/portal claim. | Jira MEMORIES-0002 §13, AC #22, #23 | Đã xác nhận |

## Trường hợp biên

- Account có permission `portal.public.access` nhưng không có `portal.admin.access`: đăng nhập admin phải bị từ chối dù credential đúng.
- Account có cả hai permission portal: có thể đăng nhập độc lập vào từng portal, mỗi lần đăng nhập tạo refresh session riêng gắn với portal đó.
- Account bị revoke permission portal sau khi đã có access token hợp lệ: cần cơ chế permission/token version hoặc resolve lại permission để không cho phép truy cập tiếp (BR-008).
- Permission cần kiểm tra không tồn tại trong hệ thống (permission code sai hoặc chưa seed): phải coi như không có quyền, không được mặc định cho phép.
- Role bị xoá hoặc RolePermission bị gỡ trong khi Account đang có session hợp lệ: hành vi theo cơ chế permission version/resolve lại, không tự động vô hiệu hoá session ngay lập tức trừ khi policy yêu cầu.

## Quy tắc hiện có trong source

- `libs/platform/security` đã có sẵn nền tảng dùng chung ở mức platform: `JwtAuthGuard` (xác thực bearer token, gắn `request.user`), `PermissionsGuard` + `RequirePermissions` decorator + port `PermissionChecker` (DI token `PERMISSION_CHECKER`), `CurrentUser` decorator, `TokenService`/`TokenClaims`, `refresh-cookie.helper.ts`.
- Module `identity-access` (`libs/modules/identity-access/src`) hiện chỉ là scaffolding rỗng (README ràng buộc layer, enforced bởi `npm run test:architecture`) — chưa có Role, Permission, AccountRole, RolePermission, chưa implement `PermissionChecker`, chưa có portal claim trong `TokenClaims`, chưa có migration cho các bảng RBAC. Đây chính là phần cần triển khai trong epic `MEMORIES-0002`.
