# Runbook triển khai task bằng AI Agent

Tài liệu này là checklist thao tác nhanh. Thay `MEMORIES-ID`, `<EPIC-ID>`, `<STORY-ID>`, tên repository và branch bằng giá trị thực tế.

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
./ai/bin/ai task create MEMORIES-ID \
  --type task \
  --parent <STORY-ID> \
  --epic <EPIC-ID> \
  --repos backend,frontend \
  --title "Tên task"
```

Chỉnh các file sau, không để lại placeholder chưa xử lý:

```text
ai/tasks/MEMORIES-ID/task.md
ai/tasks/MEMORIES-ID/task.yaml
ai/tasks/MEMORIES-ID/context.yaml
```

Mặc định task mới có giới hạn fix request; ưu tiên cấu hình `review.max_fix_cycles: 5`.
`review.max_cycles` cũ chỉ còn là fallback tương thích.

## 3. Tạo và đăng ký worktree

Developer tạo worktree cho đúng repository nằm trong scope. AI workflow không tự tạo hoặc đổi branch.

Backend:

```bash
git -C apps/backend worktree add \
  ../../worktrees/MEMORIES-ID/backend \
  -b feature/MEMORIES-ID-backend \
  origin/master

./ai/bin/ai task register-worktree MEMORIES-ID \
  --repo backend \
  --path worktrees/MEMORIES-ID/backend \
  --base-ref origin/master
```

Frontend:

```bash
git -C apps/frontend worktree add \
  ../../worktrees/MEMORIES-ID/frontend \
  -b feature/MEMORIES-ID-frontend \
  origin/master

./ai/bin/ai task register-worktree MEMORIES-ID \
  --repo frontend \
  --path worktrees/MEMORIES-ID/frontend \
  --base-ref origin/master
```

Chỉ tạo worktree cho repository được khai báo trong `task.yaml`.

## 4. Chuẩn bị domain, skill, CodeGraph, plan và context

Nếu chưa có domain knowledge phù hợp, tạo từ template rồi thay toàn bộ nội dung mẫu bằng thông tin đã kiểm chứng:

```bash
cp -R ai/domains/example ai/domains/<domain-name>
```

Cập nhật `ai/tasks/MEMORIES-ID/context.yaml`, sau đó chạy đúng thứ tự:

```bash
./ai/bin/ai task classify-skills MEMORIES-ID
./ai/bin/ai task classify-skills MEMORIES-ID --apply
./ai/bin/ai task prepare-plan MEMORIES-ID --force
./ai/bin/ai task codegraph MEMORIES-ID --init
./ai/bin/ai task prepare-context MEMORIES-ID
```

Phải đọc đề xuất classifier trước khi dùng `--apply`. `task codegraph --init` tạo hoặc
sync index cho mọi worktree đã đăng ký. `prepare-context` khóa requirements, knowledge,
skill, execution plan và trạng thái CodeGraph; chạy lại các bước liên quan nếu đầu vào
thay đổi.

## 5. Chạy pipeline tự động

Xem trước:

```bash
./ai/bin/ai task run MEMORIES-ID --dry-run
```

Thực thi:

```bash
./ai/bin/ai task run MEMORIES-ID
```

Luồng tự động:

```text
implement → implementation_ready_for_validation → validate-code → review
   ↑                                                               │
   └──────────────── request-fixes/checklist ──────────────────────┘
```

- Validation fail được ghi thành fix request cho attempt tiếp theo.
- Review có finding chặn sẽ tự tạo request-fixes và implement lại.
- Sau handoff, trạng thái là `implementation_ready_for_validation`; nếu command bị restart,
  pipeline tiếp tục validation thay vì gọi Claude lại cho cùng slice.
- Chỉ orchestrator được đổi status trong `execution-plan.json`; Claude chỉ cập nhật
  `implementation-progress.json`, checklist, handoff, source/test/evidence.
- Validation/review findings được ghi thành structured checklist có status và evidence.
- Correction được phân loại code/test, evidence/handoff hoặc validation. Evidence-only
  correction không được sửa source vì sẽ tự làm stale evidence vừa tạo.
- Vòng lặp dừng tối đa theo `review.max_fix_cycles` (mặc định `5`) và giới hạn attempt.
- Full review đầu tiên khóa `review-baseline.json`; review sau không được âm thầm mở rộng contract.
- Khi pass, report được sinh và task dừng ở `awaiting_user_acceptance`.
- Pipeline không tự accept thay người dùng.

Có thể đặt giới hạn riêng cho lần chạy:

```bash
./ai/bin/ai task run MEMORIES-ID --max-attempts 5
```

## 6. Xử lý khi Agent bị gián đoạn hoặc restart giữa implement/validation

Nếu Claude hết token, timeout, quota hoặc session limit, trạng thái chuyển thành `interrupted`. Kết quả không bị chạy lại mù quáng: attempt sau ưu tiên resume session; nếu không thể, Agent dùng `implementation-progress.json` và Git diff để tiếp tục từ phần đã làm.

Nếu Claude đã handoff thành công nhưng validation chưa chạy, trạng thái phải là
`implementation_ready_for_validation`. Chỉ cần chạy lại `task run`; không gọi `task implement`
thủ công. Workflow sẽ kiểm tra handoff/evidence và chạy quick/full validation. Với task cũ,
slice bị đánh dấu completed sớm nhưng thiếu evidence sẽ tự được đưa về `in_progress`.

Sau khi nguyên nhân quota/availability đã được xử lý:

```bash
./ai/bin/ai task run MEMORIES-ID \
  --resume-interrupted \
  --max-interrupted-retries 1
```

Không tăng retry liên tục khi lỗi hạ tầng chưa được giải quyết. Kiểm tra metrics và artifact trước:

```bash
./ai/bin/ai metrics MEMORIES-ID
git -C worktrees/MEMORIES-ID/<repo> status --short
```

## 7. Luồng thủ công khi cần chẩn đoán

```bash
./ai/bin/ai task implement MEMORIES-ID
./ai/bin/ai task validate-code MEMORIES-ID --tier quick
./ai/bin/ai task validate-code MEMORIES-ID --tier full
./ai/bin/ai task review MEMORIES-ID --mode auto
./ai/bin/ai task request-fixes MEMORIES-ID  # chỉ khi review yêu cầu sửa
./ai/bin/ai task report MEMORIES-ID         # chỉ khi validation/review pass
```

Sau `request-fixes`, quay lại bước `implement`. Dùng luồng thủ công khi cần can thiệp từng gate; vận hành thông thường nên dùng `task run`.

Không gọi `implement` lần nữa nếu state đang `implementation_ready_for_validation`; chạy
`validate-code` hoặc quay lại `task run`. Khi correction chỉ yêu cầu evidence/handoff, giữ
nguyên source fingerprint và chỉ refresh artifact được yêu cầu.

## 8. Nghiệm thu

Khi trạng thái là `awaiting_user_acceptance`, người dùng kiểm tra chức năng, acceptance criteria, edge cases, Git diff và `final-report.md`.

```bash
# Cách tối giản (`--accepted-by` mặc định là `user`)
./ai/bin/ai task accept MEMORIES-ID

# Hoặc ghi rõ người nghiệm thu và ghi chú
./ai/bin/ai task accept MEMORIES-ID \
  --accepted-by "Tên người xác nhận" \
  --note "Đã kiểm tra trên local/dev"
```

Chỉ lệnh này mới chuyển task sang `completed`.

Ví dụ với một task cụ thể:

```bash
./ai/bin/ai task accept MEMORIES-0009
```

## 9. Correction hoặc requirement change

Trước khi accept, nếu kết quả chưa đúng:

```bash
./ai/bin/ai task request-change MEMORIES-ID \
  --kind correction \
  --title "Mô tả vấn đề nghiệm thu"
```

Sau khi task đã completed nhưng requirements thay đổi:

```bash
./ai/bin/ai task request-change MEMORIES-ID \
  --kind requirement_change \
  --title "Mô tả yêu cầu mới"
```

Điền đầy đủ `user-request.md` và `requirement-addendum.md` trong change cycle mới, rồi chạy:

```bash
./ai/bin/ai task prepare-plan MEMORIES-ID --force
./ai/bin/ai task prepare-context MEMORIES-ID
./ai/bin/ai task run MEMORIES-ID
```

Requirement change sau completion tiếp tục trên worktree đã đăng ký; không tự tạo worktree hoặc branch mới.

## 10. Điều kiện cần dừng và xử lý thủ công

Dừng pipeline và kiểm tra artifact khi task ở một trong các trạng thái:

- `needs_input`: bổ sung thông tin còn thiếu.
- `blocked`: đã chạm policy/giới hạn hoặc không thể tiếp tục an toàn.
- `interrupted`: xử lý quota, timeout hoặc availability trước khi resume.
- `implementation_ready_for_validation`: không cần Claude; resume từ validation.
- `changes_requested_by_validation`: lỗi validation đã được đưa vào checklist cho attempt kế tiếp.
- `awaiting_user_acceptance`: người dùng nghiệm thu; không chạy implement tiếp.

Không dùng validation cũ, baseline của cycle trước hoặc report cũ để accept cycle hiện hành.

## 11. Command thường sử dụng

### Kiểm tra và bootstrap workspace

```bash
source .venv/bin/activate
source .env.ai
./ai/bin/ai --help
./ai/bin/ai bootstrap
./ai/bin/ai self-check
./ai/bin/ai self-check --smoke
```

### Chuẩn bị task

```bash
# Đăng ký worktree đã được developer tạo
./ai/bin/ai task register-worktree MEMORIES-ID \
  --repo <repo> \
  --path worktrees/MEMORIES-ID/<repo> \
  --base-ref origin/master

# Chọn skill và tạo execution plan
./ai/bin/ai task classify-skills MEMORIES-ID
./ai/bin/ai task classify-skills MEMORIES-ID --apply
./ai/bin/ai task prepare-plan MEMORIES-ID --force

# CodeGraph: init + sync, chỉ sync, hoặc chỉ kiểm tra status
./ai/bin/ai task codegraph MEMORIES-ID --init
./ai/bin/ai task codegraph MEMORIES-ID
./ai/bin/ai task codegraph MEMORIES-ID --no-sync

# Luôn chạy sau khi requirements, skills, plan hoặc graph thay đổi
./ai/bin/ai task prepare-context MEMORIES-ID
```

### Pipeline tự động

```bash
./ai/bin/ai task run MEMORIES-ID --dry-run
./ai/bin/ai task run MEMORIES-ID
./ai/bin/ai task run MEMORIES-ID --max-attempts 5
./ai/bin/ai task run MEMORIES-ID \
  --resume-interrupted \
  --max-interrupted-retries 1
```

### Pipeline thủ công và chẩn đoán

```bash
./ai/bin/ai task implement MEMORIES-ID --dry-run
./ai/bin/ai task implement MEMORIES-ID
./ai/bin/ai task implement MEMORIES-ID --print-command

./ai/bin/ai task validate-code MEMORIES-ID --dry-run
./ai/bin/ai task validate-code MEMORIES-ID --tier quick
./ai/bin/ai task validate-code MEMORIES-ID --tier full
# Chạy thêm command optional hoặc chỉ định một command trong commands.yaml
./ai/bin/ai task validate-code MEMORIES-ID --tier full --include-optional
./ai/bin/ai task validate-code MEMORIES-ID --tier full --command <COMMAND-NAME>

./ai/bin/ai task review MEMORIES-ID --dry-run
./ai/bin/ai task review MEMORIES-ID --mode auto
./ai/bin/ai task review MEMORIES-ID --mode full
./ai/bin/ai task review MEMORIES-ID --print-command

./ai/bin/ai task request-fixes MEMORIES-ID
./ai/bin/ai task report MEMORIES-ID
./ai/bin/ai metrics MEMORIES-ID
```

`quick` chỉ dùng để phản hồi sớm giữa các slice. Trước Codex review phải có full
validation. `--mode auto` là lựa chọn mặc định; pipeline tự quyết định delta/full theo
rủi ro và luôn yêu cầu final full review trước report.

### Nghiệm thu và thay đổi yêu cầu

```bash
./ai/bin/ai task accept MEMORIES-ID \
  --accepted-by "Tên người xác nhận" \
  --note "Đã kiểm tra trên local/dev"

./ai/bin/ai task request-change MEMORIES-ID \
  --kind correction \
  --title "Mô tả vấn đề nghiệm thu"

# Có thể nhập phản hồi đã viết sẵn từ file
./ai/bin/ai task request-change MEMORIES-ID \
  --kind correction \
  --title "Mô tả vấn đề nghiệm thu" \
  --from-file <FEEDBACK-FILE>

./ai/bin/ai task request-change MEMORIES-ID \
  --kind requirement_change \
  --title "Mô tả yêu cầu mới"
```

### Knowledge, requirements và indexes

```bash
# Chỉ áp dụng knowledge sau khi task completed và đã review proposal
./ai/bin/ai task update-knowledge MEMORIES-ID
./ai/bin/ai task update-knowledge MEMORIES-ID --apply

# Gộp requirement addenda của task completed sau khi review draft
./ai/bin/ai task consolidate-requirements MEMORIES-ID
./ai/bin/ai task apply-requirements-consolidation MEMORIES-ID \
  --approved-by "Tên người duyệt"

./ai/bin/ai indexes rebuild
```

### Git read-only để kiểm tra nhanh

```bash
git -C worktrees/MEMORIES-ID/<repo> status --short
git -C worktrees/MEMORIES-ID/<repo> diff --stat
git -C worktrees/MEMORIES-ID/<repo> diff
git -C worktrees/MEMORIES-ID/<repo> branch --show-current
```
