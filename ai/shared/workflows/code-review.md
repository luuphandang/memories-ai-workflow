# Code Review Workflow

Codex review theo thứ tự:

1. Đọc yêu cầu gốc trong `task.md`.
2. Đọc các `requirement-addendum.md` theo thứ tự cycle; nội dung mới hơn có ưu tiên khi nêu rõ xung đột.
3. Đọc `context.lock.json` để biết phiên bản tài liệu đã dùng.
4. Đọc handoff của Claude nhưng không mặc định tin là đúng.
5. Kiểm tra validation output và command thực tế của vòng hiện hành.
6. Liệt kê inventory của toàn bộ tracked diff, untracked implementation file và dependency trực tiếp; đánh dấu từng file trong `review_coverage.changed_files`.
7. Thực hiện đủ bảy review pass: requirements, diff, architecture, behavior, tests, security và regression. Không dừng khi gặp finding đầu tiên.
8. Đọc mọi `fix-request-review-*.md` hiện có, retest từng finding cũ và ghi kết quả trong `review_coverage.prior_findings`.
9. Đánh giá cross-repo contract, từng acceptance criterion hiệu lực và các risk area áp dụng được.
10. Chỉ sau khi hoàn tất coverage mới tổng hợp toàn bộ finding thành một `review.json`.

Nếu bất kỳ file/pass/risk/finding cũ nào chưa được kiểm tra, verdict phải là `blocked`. `changes_requested` có nghĩa review đã hoàn tất và danh sách finding là danh sách tổng hợp của vòng hiện tại, không phải danh sách tạm thời.

Không dùng kết quả review/validation của cycle trước để kết luận cycle mới đã đạt. Không yêu cầu thay đổi chỉ vì sở thích cá nhân nếu code phù hợp convention của repo.
