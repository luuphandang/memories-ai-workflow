# Review Checklist

## Requirement

- [ ] Đã đọc `task.md` gốc.
- [ ] Đã đọc mọi requirement addendum theo thứ tự cycle.
- [ ] Đã xác định active change cycle và nội dung bị thay thế.
- [ ] Đã kiểm tra từng acceptance criterion hiệu lực.

## Code

- [ ] Diff đúng repository/worktree và không ngoài scope.
- [ ] Không có debug code, secret hoặc thay đổi tạm thời.
- [ ] Error handling, authorization, validation và compatibility phù hợp.
- [ ] Migration, transaction, concurrency, retry/idempotency đã được xem xét khi liên quan.
- [ ] Đã lập inventory và đọc mọi changed/untracked implementation file.
- [ ] Đã lần theo dependency trực tiếp và wiring xuyên layer, không chỉ đọc file trong diff.

## Exhaustive passes

- [ ] Requirements pass: mỗi criterion có code path và evidence.
- [ ] Diff pass: toàn bộ thay đổi đã được đọc.
- [ ] Architecture pass: boundary, contract, persistence và wiring đã được trace.
- [ ] Behavior pass: happy/error/boundary/state-transition path đã được kiểm tra.
- [ ] Tests pass: assertion, coverage và validation evidence đã được kiểm tra độc lập.
- [ ] Security pass: mọi security surface áp dụng được đã được kiểm tra.
- [ ] Regression pass: finding cũ và hành vi lân cận đã được retest.

## Validation

- [ ] Chỉ dùng validation của cycle hiện hành.
- [ ] Command bắt buộc đã chạy.
- [ ] Test mới/chỉnh sửa phản ánh yêu cầu mới.
- [ ] Không dùng baseline cũ để kết luận pass.

## Handoff

- [ ] `implementation.json` khớp diff.
- [ ] Finding có bằng chứng và mức severity đúng.
- [ ] Codex pass chỉ chuyển tới user acceptance, không tự completed.
- [ ] Chỉ tổng hợp kết quả sau khi hoàn tất mọi pass; không phát hành finding theo từng đợt nhỏ.
- [ ] `review_coverage` không còn `not_reviewed`/`not_verified` trước khi yêu cầu Claude sửa.
