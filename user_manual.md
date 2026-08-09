# Hướng dẫn sử dụng AI Workspace

## 1. Mục tiêu

Bộ workspace điều phối quy trình:

```text
Jira requirement
→ developer tạo worktree
→ Claude triển khai
→ validation deterministic
→ Codex review kỹ thuật
→ người dùng nghiệm thu
→ completed
```

Claude là implementer, Codex là reviewer độc lập, còn người dùng là người duy nhất xác nhận task hoàn thành.

Hai trường hợp thay đổi yêu cầu được hỗ trợ:

1. **Correction trước nghiệm thu**: Codex đã pass nhưng người dùng phát hiện kết quả chưa đúng.
2. **Requirement change sau completion**: người dùng đã xác nhận hoàn thành, sau đó yêu cầu thay đổi và muốn tiếp tục trên worktree hiện có.

## 2. Thuật ngữ quan trọng

| Thuật ngữ | Ý nghĩa |
|---|---|
| Technical pass | Validation bắt buộc pass và Codex verdict là `pass` |
| User acceptance | Người dùng kiểm tra kết quả và chạy lệnh `task accept` |
| Change cycle | Một vòng yêu cầu sửa hoặc thay đổi được lưu trong `changes/cycle-NNN/` |
| Correction | Sửa kết quả chưa đúng trước khi người dùng xác nhận |
| Requirement change | Thay đổi yêu cầu sau khi task đã được xác nhận completed |
| Baseline | Bản lưu implementation/review/report/validation của vòng trước |
| Effective requirements | `task.md` cộng các requirement addendum theo thứ tự cycle |

## 3. Quy ước placeholder

- `[BỔ SUNG THEO DỰ ÁN]`: điền sau khi đọc source code, cấu hình, kiến trúc hoặc convention thực tế.
- `[BỔ SUNG THEO TÍNH NĂNG]`: điền từ Jira, thiết kế, API contract, quyết định PO/BA hoặc phản hồi người dùng đã xác nhận.

Không thay marker bằng giả định chưa được kiểm chứng.

## 4. Yêu cầu môi trường

- macOS/Linux hoặc shell tương thích.
- Git có hỗ trợ `git worktree`.
- Python 3.10+.
- Claude Code CLI đã cài và đăng nhập.
- Codex CLI đã cài và đăng nhập.
- Toolchain của từng repository: Node.js `>=20.0.0` + npm (workspaces) cho cả `apps/backend` và `apps/frontend`; backend cần thêm PostgreSQL, Redis và 1 S3-compatible storage (MinIO ở local/dev) chạy qua `apps/backend/docker/docker-compose.yml`.

Kiểm tra:

```bash
git --version
python3 --version
claude --version
codex --version
```

## 5. Khởi tạo một lần

```bash
cd /duong-dan/toi/project
python3 -m venv .venv
source .venv/bin/activate
pip install -r ai/requirements.txt
cp .env.ai.example .env.ai
```

Cập nhật `.env.ai`:

```bash
export AI_WORKSPACE_ROOT="/duong-dan-tuyet-doi/toi/project"
export AI_ROOT="$AI_WORKSPACE_ROOT/ai"
export CLAUDE_CONFIG_DIR="$HOME/.project-ai/claude"
export CODEX_HOME="$HOME/.project-ai/codex"
export CLAUDE_COMMAND="claude"
export CODEX_COMMAND="codex"
export CLAUDE_TIMEOUT_SECONDS="3600"
export CODEX_TIMEOUT_SECONDS="1800"
```

Nạp biến và cấu hình:

```bash
source .env.ai
./ai/bin/bootstrap
```

Không lưu token, secret hoặc credential trong workspace. `CLAUDE_TIMEOUT_SECONDS` và `CODEX_TIMEOUT_SECONDS` phải là số nguyên dương. Khi Claude implement bị timeout, quota hoặc session limit, task chuyển sang `interrupted`; mỗi attempt có log riêng và lần `implement` sau resume session nếu có, hoặc phục hồi từ `implementation-progress.json` cùng Git diff. Timeout của các bước khác vẫn được xử lý theo script tương ứng.

## 6. Đưa repository gốc vào `apps/`

```bash
git clone <REPOSITORY_URL> apps/<repo-name>
```

Sau khi đọc source thật, cập nhật:

```text
ai/repos/<repo-name>/
├── INDEX.md
├── overview.md
├── architecture.md
├── source-map.md
├── conventions.md
├── commands.yaml
├── testing.md
└── ...
```

Các repository mẫu trong gói cần được đổi hoặc bổ sung theo dự án thực tế.

## 7. Tạo Jira hierarchy

### 7.1 Epic

```bash
./ai/bin/ai task create PROJ-1000 \
  --type epic \
  --title "Example epic"
```

### 7.2 Story

```bash
./ai/bin/ai task create PROJ-1001 \
  --type story \
  --parent PROJ-1000 \
  --title "Example story"
```

### 7.3 Task

```bash
./ai/bin/ai task create PROJ-1002 \
  --type task \
  --parent PROJ-1001 \
  --epic PROJ-1000 \
  --repos backend,frontend \
  --title "Implement example feature"
```

Task mới có thêm:

```text
ai/tasks/PROJ-1002/
├── acceptance.yaml
└── changes/
```

`acceptance.yaml` lưu xác nhận người dùng. `changes/` lưu mọi vòng correction/requirement change.

## 8. Viết yêu cầu ban đầu

Chỉnh:

```text
ai/tasks/<ID>/task.md
ai/tasks/<ID>/task.yaml
ai/tasks/<ID>/context.yaml
```

`task.md` phải có:

- Mục tiêu.
- Bối cảnh.
- Scope và out of scope.
- Acceptance criteria đo được.
- Quy tắc nghiệp vụ và trường hợp biên.
- UI/API/data contract liên quan.

`task.yaml` phải có đúng Jira hierarchy, repository, validation và Git policy.


## 8.1 Cấu hình có hiệu lực trong `task.yaml`

```yaml
review:
  max_cycles: 5
  fail_on: [blocker, major]
report:
  language: vi
  include_diff_stat: true
  include_changed_files: true
  include_test_results: true
  include_review_findings: true
  include_knowledge_updates: true
```

- `review.max_cycles`: số lần review tối đa trong một implementation cycle. Nếu review vẫn không đạt khi chạm giới hạn, `request-fixes` chuyển task sang `blocked`.
- `review.fail_on`: các severity được xem là finding chặn. Giá trị hỗ trợ: `blocker`, `major`, `minor`, `note`. Giá trị này được dùng trong prompt Codex, `request-fixes`, `finalize-task` và `accept-task`.
- `report.language`: `vi` hoặc `en`.
- Các field `report.include_*`: bật/tắt từng section trong `final-report.md`.
- Quyền Git ghi không được cấu hình theo task. Task mới không có `git.allow_*`; block legacy chỉ được giữ để tương thích và mọi giá trị phải là `false`.

## 9. Tạo Git worktree — developer thực hiện

AI và script không tự tạo worktree.

```bash
mkdir -p worktrees/PROJ-1002

git -C apps/backend fetch origin
git -C apps/backend worktree add \
  ../../worktrees/PROJ-1002/backend \
  -b feature/PROJ-1002-example \
  origin/develop
```

Với repository khác, lặp lại và giữ nguyên tên repository trong task workspace.

## 10. Đăng ký worktree

```bash
./ai/bin/ai task register-worktree PROJ-1002 \
  --repo backend \
  --path worktrees/PROJ-1002/backend \
  --base-ref origin/develop
```

Script ghi lại:

- Worktree path.
- Branch tại thời điểm đăng ký.
- Base ref và SHA.
- Validation mapping.

Branch đã đăng ký được dùng để bảo vệ luồng reopened.

## 11. Chuẩn bị plan, skill và context

Thay domain mẫu bằng domain thật khi đã có dữ liệu:

```bash
cp -R ai/domains/example ai/domains/<feature-name>
```

Sau đó sửa `context.yaml` để tham chiếu domain mới. Chạy các bước chuẩn bị theo đúng thứ tự:

```bash
./ai/bin/ai task classify-skills PROJ-1002
# kiểm tra đề xuất; chỉ áp dụng khi mapping phù hợp
./ai/bin/ai task classify-skills PROJ-1002 --apply
./ai/bin/ai task prepare-plan PROJ-1002 --force
./ai/bin/ai task prepare-context PROJ-1002
```

`classify-skills` xác định skill implement/review cần dùng. `prepare-plan` tạo execution plan từ requirements và skill đã chọn. `prepare-context` là bước khóa cuối cùng, vì vậy phải chạy lại sau mọi thay đổi trong `task.md`, requirement addendum, `task.yaml.skills` hoặc execution plan.

Script sẽ:

- Kiểm tra file knowledge.
- Kiểm tra worktree và branch.
- Đưa `task.md` và mọi change addendum vào requirement manifest.
- Tạo SHA-256 cho tài liệu.
- Khóa aggregate hash của các skill bắt buộc và execution plan.
- Ghi `context.lock.json`.

Nếu active change cycle còn marker chưa xử lý, script dừng để tránh agent làm theo yêu cầu thiếu.

## 12. Chạy pipeline ban đầu

### 12.1 Luồng tự động khuyến nghị

```bash
./ai/bin/ai task run PROJ-1002 --dry-run
./ai/bin/ai task run PROJ-1002
```

Pipeline tự lặp `implement → validate-code → review → request-fixes`. Validation failure được chuyển thành fix request cho implementation attempt kế tiếp. Khi Codex pass, pipeline sinh report và dừng ở `awaiting_user_acceptance`; pipeline không tự accept task.

Tuỳ chọn kiểm soát:

```bash
./ai/bin/ai task run PROJ-1002 --max-attempts 5
./ai/bin/ai task run PROJ-1002 --resume-interrupted --max-interrupted-retries 1
```

Không bật `--resume-interrupted` cho đến khi quota hoặc lỗi availability đã được giải quyết. Pipeline dừng khi chạm `review.max_cycles`, `--max-attempts`, gặp `blocked`/`needs_input`, hoặc gặp lỗi không thể retry.

Xem metrics cục bộ bằng:

```bash
./ai/bin/ai metrics PROJ-1002
```

Dữ liệu runtime gồm attempt, cycle, resume, thời lượng và token usage khi CLI trả về.

### 12.1.1 Luồng thủ công để chẩn đoán hoặc can thiệp

```bash
./ai/bin/ai task implement PROJ-1002 --dry-run
./ai/bin/ai task implement PROJ-1002
./ai/bin/ai task validate-code PROJ-1002
./ai/bin/ai task review PROJ-1002
./ai/bin/ai task request-fixes PROJ-1002  # khi review yêu cầu sửa
./ai/bin/ai task report PROJ-1002         # khi validation và review đã pass
```

Luồng này hữu ích khi cần xem hoặc xử lý riêng từng gate. Bình thường nên dùng `task run` để tránh bỏ sót validation, fix request hoặc report.

### 12.2 Validation

```bash
./ai/bin/ai task validate-code PROJ-1002 --dry-run
./ai/bin/ai task validate-code PROJ-1002
```

`--dry-run` chỉ hiển thị/kế hoạch hóa command. Kết quả dry-run không được phép dùng để review, sinh acceptance report hoặc accept task.

Command thật lấy từ `ai/repos/<repo>/commands.yaml`.

### 12.3 Codex review

```bash
./ai/bin/ai task review PROJ-1002 --dry-run
./ai/bin/ai task review PROJ-1002
```

Nếu Codex yêu cầu sửa, lưu ý `review.max_cycles` áp dụng cho implementation cycle hiện hành. Mặc định là `5`: nếu lần review thứ năm vẫn không đạt, `request-fixes` chuyển task sang `blocked` và cần người dùng quyết định bổ sung thông tin, đổi yêu cầu hoặc xử lý thủ công.

```bash
./ai/bin/ai task request-fixes PROJ-1002
./ai/bin/ai task implement PROJ-1002
./ai/bin/ai task validate-code PROJ-1002
./ai/bin/ai task review PROJ-1002
```

### 12.4 Sinh báo cáo kỹ thuật

```bash
./ai/bin/ai task report PROJ-1002
```

Khi validation và Codex pass, trạng thái trở thành:

```text
awaiting_user_acceptance
```

Task **chưa completed** tại bước này.

## 13. Người dùng nghiệm thu

Kiểm tra:

- Chức năng thực tế.
- UI/UX.
- Các acceptance criteria.
- Edge case.
- Git diff.
- `final-report.md`.

Nếu kết quả đúng:

```bash
./ai/bin/ai task accept PROJ-1002 \
  --accepted-by "Tên người xác nhận" \
  --note "Đã kiểm tra trên môi trường local/dev"
```

Kết quả:

- `acceptance.yaml` chuyển `accepted`.
- `state.yaml` chuyển `completed`.
- `final-report.md` được cập nhật.
- Task xuất hiện trong `ai/indexes/completed.md`.
- Knowledge update mới được phép áp dụng.

## 14. Trường hợp 1 — Chưa accept và người dùng phát hiện vấn đề

Điều kiện đầu vào thường là:

```text
status: awaiting_user_acceptance
```

### 14.1 Tạo correction cycle

```bash
./ai/bin/ai task request-change PROJ-1002 \
  --kind correction \
  --title "Sửa kết quả chưa đúng theo nghiệm thu"
```

Có thể để script tự xác định loại:

```bash
./ai/bin/ai task request-change PROJ-1002 \
  --title "Sửa kết quả chưa đúng theo nghiệm thu"
```

Script tạo:

```text
ai/tasks/PROJ-1002/changes/cycle-001/
├── metadata.yaml
├── user-request.md
├── requirement-addendum.md
├── attachments/README.md
└── baseline/
```

Đồng thời script:

- Lưu implementation/review/report/context/validation hiện tại vào `baseline/`.
- Reset output máy đọc để không dùng nhầm kết quả cũ.
- Tăng `implementation_cycle` và `change_cycle`.
- Reset `review_cycle`.
- Chuyển trạng thái thành `changes_requested_by_user`.
- Giữ nguyên worktree đang có.

### 14.2 Điền phản hồi người dùng

Chỉnh:

```text
changes/cycle-001/user-request.md
```

Ghi rõ:

- Vấn đề quan sát được.
- Kết quả hiện tại.
- Kết quả mong muốn.
- Cách tái hiện.
- Screenshot/video/log hoặc tài liệu tham chiếu.

### 14.3 Chuẩn hóa thành yêu cầu

Chỉnh:

```text
changes/cycle-001/requirement-addendum.md
```

Ghi rõ:

- Scope bổ sung hoặc sửa.
- Acceptance criteria mới.
- Nội dung cũ bị thay thế.
- Out of scope của cycle.

Claude và Codex dùng addendum làm yêu cầu chính thức; `user-request.md` là bằng chứng và bối cảnh.

### 14.4 Chạy lại pipeline

```bash
./ai/bin/ai task prepare-plan PROJ-1002 --force
./ai/bin/ai task prepare-context PROJ-1002
./ai/bin/ai task run PROJ-1002
```

Sau đó người dùng kiểm tra lại và chạy `task accept` hoặc tạo correction cycle tiếp theo.

## 15. Trường hợp 2 — Task đã completed nhưng yêu cầu thay đổi

Điều kiện đầu vào:

```text
status: completed
```

Worktree cũ phải vẫn tồn tại tại path đã đăng ký và vẫn ở đúng branch.

### 15.1 Không tạo worktree mới

Không chạy `git worktree add` và không đăng ký path mới.

Chạy:

```bash
./ai/bin/ai task request-change PROJ-1002 \
  --kind requirement_change \
  --title "Bổ sung yêu cầu do nghiệp vụ thay đổi"
```

Hoặc để `auto` xác định từ trạng thái completed:

```bash
./ai/bin/ai task request-change PROJ-1002 \
  --title "Bổ sung yêu cầu do nghiệp vụ thay đổi"
```

Script sẽ:

1. Đọc worktree đã đăng ký từ `task.yaml` và `state.yaml`.
2. Kiểm tra path vẫn là Git worktree.
3. Kiểm tra branch hiện tại trùng branch đã đăng ký.
4. Không checkout, không tạo branch và không tạo worktree.
5. Lưu acceptance/report/implementation/review/validation đã hoàn thành vào baseline.
6. Tạo change cycle loại `requirement_change`.
7. Chuyển trạng thái sang `reopened`.
8. Chuyển user acceptance cũ thành `superseded` cho vòng mới.

### 15.2 Điền yêu cầu thay đổi

Chỉnh:

```text
changes/cycle-NNN/user-request.md
changes/cycle-NNN/requirement-addendum.md
```

Addendum phải chỉ ra rõ:

- Nội dung mới.
- Điều gì vẫn giữ nguyên.
- Điều gì thay thế acceptance criteria cũ.
- Rủi ro migration/backward compatibility nếu có.

### 15.3 Chạy tiếp trên worktree cũ

```bash
./ai/bin/ai task prepare-plan PROJ-1002 --force
./ai/bin/ai task prepare-context PROJ-1002
./ai/bin/ai task run PROJ-1002
./ai/bin/ai task accept PROJ-1002 --accepted-by "Tên người xác nhận"
```

Lịch sử task và Jira ID được giữ nguyên; chỉ change cycle tăng lên.

## 16. Khi worktree cũ không còn hợp lệ

`request-change` hoặc `prepare-context` dừng nếu:

- Worktree path đã bị xóa.
- Path không còn là Git worktree.
- Branch đã thay đổi.

Script không tự sửa vì có thể làm mất hoặc trộn code.

Developer cần:

1. Kiểm tra lý do worktree bị xóa/đổi branch.
2. Khôi phục đúng worktree/branch theo Git policy của dự án.
3. Chỉ cập nhật đăng ký khi có quyết định có chủ đích.
4. Chạy lại `request-change` hoặc `prepare-context`.

## 17. Thứ tự ưu tiên yêu cầu

Agent phải áp dụng:

```text
policy an toàn
→ task.md gốc
→ cycle-001 requirement-addendum
→ cycle-002 requirement-addendum
→ ...
```

Addendum mới chỉ ghi đè nội dung cũ khi nó mô tả rõ phần xung đột hoặc bị thay thế.

Không xóa/sửa lịch sử cycle cũ để “làm sạch” yêu cầu.

## 18. Cập nhật knowledge base

Chỉ sau trạng thái `completed`:

```bash
./ai/bin/ai task update-knowledge PROJ-1002
./ai/bin/ai task update-knowledge PROJ-1002 --apply
```

Luôn review nội dung proposal trước `--apply`.

Nếu task được reopened, knowledge phát sinh từ cycle mới chỉ áp dụng sau lần accept tiếp theo.

## 19. Trạng thái task

| Trạng thái | Ý nghĩa |
|---|---|
| `ready` | Hồ sơ mới tạo |
| `prepared` | Context và worktree đã kiểm tra |
| `implementing` | Claude đang triển khai |
| `interrupted` | Implementation bị gián đoạn; có thể resume session hoặc tiếp tục từ checkpoint và Git diff |
| `validating` | Đang chạy kiểm tra deterministic |
| `reviewing` | Codex đang/đã review, chưa sinh acceptance report |
| `changes_requested_by_codex` | Codex yêu cầu sửa kỹ thuật |
| `awaiting_user_acceptance` | Đã pass kỹ thuật, chờ người dùng xác nhận |
| `changes_requested_by_user` | Người dùng yêu cầu correction trước nghiệm thu |
| `completed` | Người dùng đã xác nhận vòng hiện hành |
| `reopened` | Task completed được mở lại do yêu cầu mới |
| `needs_input` | Thiếu thông tin cần người dùng bổ sung |
| `blocked` | Không thể tiếp tục an toàn |
| `failed` | Pipeline hoặc dữ liệu task lỗi |

## 20. Cấu trúc change cycle

```text
changes/cycle-NNN/
├── metadata.yaml               # Loại, nguồn trạng thái, policy và trạng thái cycle
├── user-request.md             # Phản hồi/bối cảnh/bằng chứng từ người dùng
├── requirement-addendum.md     # Yêu cầu chính thức cho agent
├── attachments/README.md       # Quy tắc và danh mục bằng chứng
└── baseline/                   # Snapshot vòng trước
    ├── implementation.json
    ├── review.json
    ├── final-report.md
    ├── acceptance.yaml
    ├── context.lock.json
    ├── knowledge-updates.json
    └── validation/
```

Các artifact vận hành quan trọng ngoài change cycle:

```text
ai/tasks/<ID>/
├── execution-plan.json             # Kế hoạch thực thi hiện hành
├── context.lock.json               # Hash requirements, knowledge, skills và plan
├── implementation.json             # Kết quả implement hiện hành
├── implementation-progress.json    # Checkpoint dùng khi implementation bị gián đoạn
├── review.json                     # Verdict/findings hiện hành
├── final-report.md                 # Báo cáo chờ nghiệm thu
└── validation/                     # Bằng chứng validation hiện hành
```

## 21. Lệnh thường dùng

```bash
# Tạo task
./ai/bin/ai task create PROJ-1002 --type task --parent PROJ-1001 --epic PROJ-1000 --title "Example"

# Đăng ký worktree
./ai/bin/ai task register-worktree PROJ-1002 --repo backend --path worktrees/PROJ-1002/backend

# Chuẩn bị
./ai/bin/ai task classify-skills PROJ-1002 --apply
./ai/bin/ai task prepare-plan PROJ-1002 --force
./ai/bin/ai task prepare-context PROJ-1002

# Pipeline tự động (khuyến nghị)
./ai/bin/ai task run PROJ-1002 --dry-run
./ai/bin/ai task run PROJ-1002

# Resume sau khi đã xử lý nguyên nhân gián đoạn
./ai/bin/ai task run PROJ-1002 --resume-interrupted --max-interrupted-retries 1

# Pipeline thủ công
./ai/bin/ai task implement PROJ-1002
./ai/bin/ai task validate-code PROJ-1002
./ai/bin/ai task review PROJ-1002
./ai/bin/ai task report PROJ-1002

# Metrics
./ai/bin/ai metrics PROJ-1002

# Nghiệm thu
./ai/bin/ai task accept PROJ-1002 --accepted-by "User"

# Correction trước accept
./ai/bin/ai task request-change PROJ-1002 --kind correction --title "Fix acceptance issue"

# Requirement change sau completed, dùng worktree cũ
./ai/bin/ai task request-change PROJ-1002 --kind requirement_change --title "New requirement"

# Knowledge
./ai/bin/ai task update-knowledge PROJ-1002 --apply

# Indexes
./ai/bin/ai indexes rebuild

# Tự kiểm tra control plane
./ai/bin/ai self-check --smoke
```

## 22. Tự kiểm tra workspace

Chạy kiểm tra tĩnh:

```bash
./ai/bin/ai self-check
```

Chạy smoke test end-to-end trong thư mục tạm, không gọi dịch vụ Claude/Codex thật và không thay đổi task/worktree thật:

```bash
./ai/bin/ai self-check --smoke
```

Smoke test tạo repository và worktree dùng một lần, dùng fake Claude/Codex CLI để kiểm tra skill fixtures, resume/checkpoint, vòng tự động implement–validate–review–request-fixes, `review.fail_on`, correction, reopening, report và user acceptance.

## 23. Dữ liệu ví dụ

Xem:

```text
ai/examples/tasks/PROJ-1002/
```

- `cycle-001`: correction trước acceptance.
- `cycle-002`: requirement change sau completed.

Toàn bộ nội dung ví dụ là trung lập và không dùng dữ liệu dự án thật.

## 24. Checklist vận hành

### Trước Claude

- [ ] Jira hierarchy đúng.
- [ ] `task.md` đầy đủ.
- [ ] Worktree đúng path và branch.
- [ ] Context không chứa secret.
- [ ] Active change addendum không còn placeholder chưa xử lý.
- [ ] Skill implement/review đã được classify, kiểm tra và apply.
- [ ] `execution-plan.json` phản ánh requirements hiện hành.
- [ ] `context.lock.json` được tạo sau lần sửa requirements/skill/plan cuối cùng.

### Trước Codex

- [ ] `implementation.json` hợp lệ.
- [ ] Validation của cycle hiện hành đã chạy.
- [ ] Không dùng validation cũ trong baseline.
- [ ] Implementation progress và Git diff của attempt hiện hành đã được ghi nhận.

### Trước accept

- [ ] Codex pass.
- [ ] Validation pass.
- [ ] Pipeline đang ở `awaiting_user_acceptance`, không phải `interrupted` hoặc `blocked`.
- [ ] Người dùng đã test kết quả.
- [ ] Không còn correction cần thực hiện.

### Sau accept

- [ ] `acceptance.yaml` là accepted.
- [ ] `state.yaml` là completed.
- [ ] Knowledge proposal được review trước khi apply.
- [ ] Giữ worktree nếu có khả năng cần mở lại task; xóa theo Git policy khi không còn cần.
