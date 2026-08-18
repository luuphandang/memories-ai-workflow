# Authorization Domain Index

Domain quản lý portal authorization và RBAC (Role/Permission) dùng chung cho `public-web` và `admin-web`, thuộc module `identity-access` (epic `MEMORIES-0002`).

- `overview.md`: phạm vi và thuật ngữ của portal authorization/RBAC.
- `business-rules.md`: quy tắc nghiệp vụ về portal permission và RBAC.
- `api-contract.md`: hợp đồng interface kiểm tra permission và login theo portal.
- `data-flow.md`: luồng resolve role/permission và kiểm tra portal access.
- `workflow.md`: trạng thái authorization trong luồng đăng nhập/request.
- `validation-rules.md`: quy tắc kiểm tra dữ liệu portal/permission.
- `decisions.md`: quyết định kiến trúc về RBAC và portal authorization.

## Trạng thái hiện tại (2026-08-18)

Google và Facebook OAuth đã được cài đặt đầy đủ ở tầng provider-client/use-case (authorization-code flow, verify ID token OIDC, exchange profile, gắn `Account` theo `(provider, providerSubject)` — email do provider cung cấp không bao giờ dùng để cross-link sang `Account` LOCAL hoặc provider khác) nhưng **cả hai đều đang bị vô hiệu hóa** trên public surface của `identity-access`: `OAuthController.parseSocialProvider` reject mọi provider trước khi chạm `OAuthClientRegistry`, nên `/auth/oauth/:provider/start|callback` fail closed bất kể cấu hình env. Google bị hoãn vì đang chờ thông tin OAuth client id/secret thật từ Google (chưa có credential production); Facebook bị hoãn vì provider contract chưa được xác minh độc lập. Mã của cả hai được giữ lại làm deferred code (đăng ký DI nhưng không nằm trong `OAUTH_CLIENTS` đang hoạt động) để bật lại khi có đủ thông tin. Apple vẫn chỉ ở mức contract, chưa triển khai.
