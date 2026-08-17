# MEMORIES-0005 — Trạng thái Facebook Auth

Ngày cập nhật: 2026-08-17.

Đăng nhập Facebook được tạm hoãn và **vô hiệu hóa hoàn toàn** trong phạm vi task này. Public
login hiện chỉ hỗ trợ số điện thoại/mật khẩu và Google OAuth.

Yêu cầu vô hiệu hóa gồm:

- không hiển thị nút/link Facebook trên public UI;
- không đăng ký hoặc không cho phép public OAuth start/callback Facebook hoạt động;
- request trực tiếp không được gọi Facebook, tạo/liên kết account hoặc phát hành phiên;
- mã backend chưa kích hoạt có thể được giữ lại để phục vụ lần triển khai sau.

Chỉ bật lại UI và backend public entry points sau khi có một trong các bằng chứng sau:

- kiểm thử bằng Facebook test app/sandbox chạy qua `FacebookOAuthClient` thật; hoặc
- contract chính thức gắn với Graph API version được cấu hình, xác nhận method, endpoint,
  parameter channel, profile authentication và response fields mà client sử dụng.

Khi bật lại phải bổ sung regression test public UI và backend endpoint, chạy lại
backend/frontend validation và Codex full review cho toàn bộ luồng authorize → callback →
account/session.
