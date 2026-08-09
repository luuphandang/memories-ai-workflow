# Git Policy

Agent được phép đọc:

```bash
git status --short
git diff --stat
git diff
git log --oneline
git branch --show-current
git rev-parse HEAD
```

Agent không được phép:

- `git commit`, `push`, `merge`, `rebase`, `cherry-pick`
- `git checkout`, `switch`, `reset`, `clean`
- tạo/xóa/prune worktree
- sửa `.git/`

## Bất biến toàn hệ thống

Quyền Git ghi không được cấu hình theo từng task. `task.yaml` mới không còn sinh các field `git.allow_*`. Nếu task cũ vẫn có block `git`, mọi giá trị phải là `false`; script sẽ dừng nếu phát hiện giá trị bật.

## Các lớp bảo vệ

1. Quy tắc trong `ai/agents/common.md` và policy này.
2. `ai/config/claude/settings.json` allow/deny-list.
3. Hook `ai/config/claude/hooks/block-destructive.sh`.
4. Script kiểm tra worktree/branch đã đăng ký.

Hook chỉ là defense-in-depth. Hook đã chặn command trực tiếp, executable có đường dẫn tuyệt đối và wrapper thông dụng, nhưng regex không thể phân tích an toàn mọi dạng shell indirection, biến, function hoặc binary tùy biến. Không xem hook là sandbox độc lập; deny-list và chế độ read-only của reviewer vẫn là lớp chính.

Branch model, base branch và quy tắc commit thực tế: single long-lived branch `master` cho cả backend và frontend (không có `develop`/`release/*`); commit message theo Conventional Commits (`commitlint.config.js`, extend `@commitlint/config-conventional`, bắt buộc `scope-case` kebab-case), enforce qua Husky hook `commit-msg`; format/lint tự động trước commit qua `lint-staged` ở hook `pre-commit` (cả 2 repo đều có cấu hình này).
Quy tắc branch của Jira item hiện tại: `[BỔ SUNG THEO TÍNH NĂNG]`.

## Release workflow safety

- Workspace này dùng long-lived branch `master`; workflow không được ngầm giả định `main`/`develop`.
- Khi workflow checkout một branch rồi chuyển sang branch khác, dùng full history (`fetch-depth: 0`) và fetch ref đích tường minh trước khi checkout.
- Sau khi push image/tag mutable, lấy digest từ output/metadata của chính build invocation, không đọc lại mutable tag. Dùng concurrency group theo shared resource; deploy và rollback tác động cùng production/manifest branch phải dùng cùng group.
- Bước tạo tag hoặc ghi artifact durable phải idempotent: rerun chấp nhận kết quả đã tồn tại chỉ khi nó khớp chính xác commit/digest hiện tại.
