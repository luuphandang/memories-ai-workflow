# Runbook triển khai task bằng AI Agent

Tài liệu này là checklist thao tác nhanh. Thay `<TASK-ID>`, `<EPIC-ID>`, `<STORY-ID>`, tên repository và branch bằng giá trị thực tế.

## 1. Kiểm tra control plane

```bash
source .env.ai
./ai/bin/ai self-check
```

Khi vừa thay đổi workflow hoặc skill, chạy thêm smoke test:

```bash
./ai/bin/ai self-check --smoke
```

## 2. Tạo task và viết requirements

Ví dụ hierarchy đầy đủ:

```bash
./ai/bin/ai task create <EPIC-ID> --type epic --title "Tên epic"
./ai/bin/ai task create <STORY-ID> --type story --parent <EPIC-ID> --title "Tên story"
./ai/bin/ai task create <TASK-ID> \
  --type task \
  --parent <STORY-ID> \
  --epic <EPIC-ID> \
  --repos backend,frontend \
  --title "Tên task"
```

Chỉnh các file sau, không để lại placeholder chưa xử lý:

```text
ai/tasks/<TASK-ID>/task.md
ai/tasks/<TASK-ID>/task.yaml
ai/tasks/<TASK-ID>/context.yaml
```

Mặc định task mới có `review.max_cycles: 5`.

## 3. Tạo và đăng ký worktree

Developer tạo worktree cho đúng repository nằm trong scope. AI workflow không tự tạo hoặc đổi branch.

Backend:

```bash
git -C apps/backend worktree add \
  ../../worktrees/<TASK-ID>/backend \
  -b feature/<TASK-ID>-backend \
  origin/master

./ai/bin/ai task register-worktree <TASK-ID> \
  --repo backend \
  --path worktrees/<TASK-ID>/backend \
  --base-ref origin/master
```

Frontend:

```bash
git -C apps/frontend worktree add \
  ../../worktrees/<TASK-ID>/frontend \
  -b feature/<TASK-ID>-frontend \
  origin/master

./ai/bin/ai task register-worktree <TASK-ID> \
  --repo frontend \
  --path worktrees/<TASK-ID>/frontend \
  --base-ref origin/master
```

Chỉ tạo worktree cho repository được khai báo trong `task.yaml`.

## 4. Chuẩn bị domain, skill, plan và context

Nếu chưa có domain knowledge phù hợp, tạo từ template rồi thay toàn bộ nội dung mẫu bằng thông tin đã kiểm chứng:

```bash
cp -R ai/domains/example ai/domains/<domain-name>
```

Cập nhật `ai/tasks/<TASK-ID>/context.yaml`, sau đó chạy đúng thứ tự:

```bash
./ai/bin/ai task classify-skills <TASK-ID>
./ai/bin/ai task classify-skills <TASK-ID> --apply
./ai/bin/ai task prepare-plan <TASK-ID> --force
./ai/bin/ai task prepare-context <TASK-ID>
```

Phải đọc đề xuất classifier trước khi dùng `--apply`. `prepare-context` khóa requirements, knowledge, skill và execution plan; chạy lại ba bước cuối nếu một trong các đầu vào này thay đổi.

## 5. Chạy pipeline tự động

Xem trước:

```bash
./ai/bin/ai task run <TASK-ID> --dry-run
```

Thực thi:

```bash
./ai/bin/ai task run <TASK-ID>
```

Luồng tự động:

```text
implement → validate-code → review
   ↑                            │
   └──── request-fixes ─────────┘
```

- Validation fail được ghi thành fix request cho attempt tiếp theo.
- Review có finding chặn sẽ tự tạo request-fixes và implement lại.
- Vòng lặp dừng tối đa theo `review.max_cycles` (mặc định `5`) và giới hạn attempt.
- Khi pass, report được sinh và task dừng ở `awaiting_user_acceptance`.
- Pipeline không tự accept thay người dùng.

Có thể đặt giới hạn riêng cho lần chạy:

```bash
./ai/bin/ai task run <TASK-ID> --max-attempts 5
```

## 6. Xử lý khi Agent bị gián đoạn

Nếu Claude hết token, timeout, quota hoặc session limit, trạng thái chuyển thành `interrupted`. Kết quả không bị chạy lại mù quáng: attempt sau ưu tiên resume session; nếu không thể, Agent dùng `implementation-progress.json` và Git diff để tiếp tục từ phần đã làm.

Sau khi nguyên nhân quota/availability đã được xử lý:

```bash
./ai/bin/ai task run <TASK-ID> \
  --resume-interrupted \
  --max-interrupted-retries 1
```

Không tăng retry liên tục khi lỗi hạ tầng chưa được giải quyết. Kiểm tra metrics và artifact trước:

```bash
./ai/bin/ai metrics <TASK-ID>
git -C worktrees/<TASK-ID>/<repo> status --short
```

## 7. Luồng thủ công khi cần chẩn đoán

```bash
./ai/bin/ai task implement <TASK-ID>
./ai/bin/ai task validate-code <TASK-ID>
./ai/bin/ai task review <TASK-ID>
./ai/bin/ai task request-fixes <TASK-ID>  # chỉ khi review yêu cầu sửa
./ai/bin/ai task report <TASK-ID>         # chỉ khi validation/review pass
```

Sau `request-fixes`, quay lại bước `implement`. Dùng luồng thủ công khi cần can thiệp từng gate; vận hành thông thường nên dùng `task run`.

## 8. Nghiệm thu

Khi trạng thái là `awaiting_user_acceptance`, người dùng kiểm tra chức năng, acceptance criteria, edge cases, Git diff và `final-report.md`.

```bash
./ai/bin/ai task accept <TASK-ID> \
  --accepted-by "Tên người xác nhận" \
  --note "Đã kiểm tra trên local/dev"
```

Chỉ lệnh này mới chuyển task sang `completed`.

## 9. Correction hoặc requirement change

Trước khi accept, nếu kết quả chưa đúng:

```bash
./ai/bin/ai task request-change <TASK-ID> \
  --kind correction \
  --title "Mô tả vấn đề nghiệm thu"
```

Sau khi task đã completed nhưng requirements thay đổi:

```bash
./ai/bin/ai task request-change <TASK-ID> \
  --kind requirement_change \
  --title "Mô tả yêu cầu mới"
```

Điền đầy đủ `user-request.md` và `requirement-addendum.md` trong change cycle mới, rồi chạy:

```bash
./ai/bin/ai task prepare-plan <TASK-ID> --force
./ai/bin/ai task prepare-context <TASK-ID>
./ai/bin/ai task run <TASK-ID>
```

Requirement change sau completion tiếp tục trên worktree đã đăng ký; không tự tạo worktree hoặc branch mới.

## 10. Điều kiện cần dừng và xử lý thủ công

Dừng pipeline và kiểm tra artifact khi task ở một trong các trạng thái:

- `needs_input`: bổ sung thông tin còn thiếu.
- `blocked`: đã chạm policy/giới hạn hoặc không thể tiếp tục an toàn.
- `interrupted`: xử lý quota, timeout hoặc availability trước khi resume.
- `awaiting_user_acceptance`: người dùng nghiệm thu; không chạy implement tiếp.

Không dùng validation cũ, baseline của cycle trước hoặc report cũ để accept cycle hiện hành.
