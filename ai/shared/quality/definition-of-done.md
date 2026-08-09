# Definition of Done

Một task chỉ hoàn thành khi:

- [ ] Scope và acceptance criteria hiệu lực, bao gồm mọi requirement addendum, đã được xử lý hoặc có ngoại lệ được chấp thuận.
- [ ] Không có thay đổi ngoài worktree khai báo.
- [ ] Không có secret/debug code/tạm thời.
- [ ] Validation bắt buộc của vòng hiện hành pass hoặc có waiver rõ ràng.
- [ ] Test bao phủ happy path và rủi ro chính.
- [ ] Migration/API/UI tương thích theo policy dự án.
- [ ] Codex không còn finding `blocker`/`major` trong vòng hiện hành.
- [ ] `implementation.json`, `review.json`, `state.yaml`, `final-report.md` hợp lệ.
- [ ] Task đã ở `awaiting_user_acceptance` và người dùng đã chạy lệnh xác nhận.
- [ ] Knowledge update cần thiết đã được đề xuất/duyệt; chỉ áp dụng sau xác nhận.

Tiêu chí bổ sung của dự án: test e2e backend (`npm run test:e2e` tại `apps/backend`) phải chạy thật với PostgreSQL/Redis/MinIO (qua `docker/docker-compose.yml` hoặc container throwaway tương đương), không được coi là đạt nếu chỉ pass với mock/stub hạ tầng — đây là thực hành đã áp dụng xuyên suốt toàn bộ MEMORIES-0001 và nhiều lần phát hiện bug thật (BullMQ/S3/dotenv) mà test chỉ mock sẽ bỏ sót.
Tiêu chí riêng của tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`.
