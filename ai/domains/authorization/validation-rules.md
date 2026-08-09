# Authorization (Portal + RBAC) — Validation Rules

| ID | Dữ liệu | Điều kiện hợp lệ | Xử lý khi sai |
|---|---|---|---|
| VR-001 | `portal` (login request) | Bắt buộc, chỉ nhận giá trị enum `PUBLIC` hoặc `ADMIN`, không suy luận từ nguồn khác. | Trả lỗi validation `400 Bad Request`, không xử lý authentication. |
| VR-002 | Permission cần kiểm tra khi login | Không được nhận từ client; backend tự map từ `portal` sang permission code cố định. | Bỏ qua/không tin giá trị permission nếu client cố truyền; luôn dùng mapping phía server. |
| VR-003 | Role code, Permission code | Chuỗi ổn định dạng `resource.action` (ví dụ `portal.admin.access`, `account.read`), dùng làm business identifier; không dùng display name để so sánh logic. | Từ chối tạo/gán role-permission nếu code không đúng định dạng hoặc không tồn tại trong danh sách permission tối thiểu đã định nghĩa. |
| VR-004 | Permission decorator trên controller | Mọi route Account/UserProfile CRUD phải khai báo permission yêu cầu, không được để trống. | Coi là lỗi cấu hình/triển khai; chặn merge nếu route thiếu khai báo permission (review/lint theo convention dự án). |
| VR-005 | Request context permission (mỗi request) | Roles/permissions trong context phải khớp với Account thực hiện request hiện tại; không tái sử dụng context giữa các request đồng thời. | Nếu phát hiện lẫn context, coi là lỗi hệ thống nghiêm trọng; request phải bị chặn thay vì xử lý với permission sai. |

Thư viện/cơ chế validation của dự án: `class-validator` + `class-transformer` qua `ValidationPipe` (xem `libs/platform/security/src/validation-pipe.factory.ts`); `zod` cũng có trong dependencies cho các schema khác. DTO login/portal sẽ khai báo tại `libs/modules/identity-access/src/presentation` theo cùng convention.
