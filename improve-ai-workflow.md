# Cải thiện AI workflow để đồng nhất qua nhiều task

Ngày triển khai: 2026-08-07  
Phạm vi: `ai/` control plane, Claude implementer, Codex reviewer và các task hiện có.

## 1. Mục tiêu

Thay đổi này chuyển các hướng dẫn kỹ thuật lặp lại từ prompt chung sang skill có version/hash, đồng thời đưa những kiểm tra dễ sai sang script deterministic. Workflow mới nhằm:

- Giữ cách xử lý nhất quán giữa task và giữa các phiên Agent.
- Phân rã task lớn thành vertical slice có thể hoàn thành và review độc lập.
- Phát hiện sớm port thiếu adapter/DI binding, requirement thiếu evidence và context thiếu repository knowledge.
- Không dựa hoàn toàn vào khả năng Agent tự nhớ hoặc tự chọn quy trình.
- Giảm review cycle và token dùng để Agent khám phá lại cấu trúc dự án.

## 2. Vấn đề trước thay đổi

Workflow cũ có policy, role, schema và review checklist nhưng thiếu procedure chuyên biệt. Implementer chỉ được yêu cầu đọc yêu cầu, lập kế hoạch, code, test và handoff. Quy trình đó không bắt buộc Agent hoàn thiện chuỗi runtime:

```text
domain → application port → infrastructure adapter → DI provider
       → migration/constraint → presentation → tests
```

Các vấn đề quan sát được:

- `ai/skills/` trống và bootstrap không đưa skill vào Claude/Codex home.
- Task không khai báo skill bắt buộc, nên hai phiên Agent có thể chọn quy trình khác nhau.
- Registered worktree có thể tồn tại khi `context.repositories` vẫn trống.
- Epic lớn được implement trực tiếp mà không có execution plan.
- Interface/repository port có thể được tạo trước khi adapter và Nest provider hoàn tất.
- Reviewer phải tự suy luận completeness, khiến lỗi được phát hiện muộn.
- Handoff không chứng minh skill/checklist nào đã được áp dụng.

## 3. Skill mới

### 3.1 `decompose-implementation-task`

Đường dẫn: `ai/skills/decompose-implementation-task/`

- Phân rã epic/task lớn thành vertical slices.
- Mapping requirement vào slice; xác định deliverable, test, validation và dependency.
- Đồng bộ `execution-plan.json` với checkpoint.
- `references/scope-thresholds.md` quy định ngưỡng decomposition.
- `scripts/validate_execution_plan.py` validate schema, duplicate ID và dependency.

### 3.2 `implement-nestjs-vertical-slice`

Đường dẫn: `ai/skills/implement-nestjs-vertical-slice/`

- Bắt buộc completeness xuyên domain, application, infrastructure, wiring, persistence, presentation và test.
- Kiểm tra runtime reachability; TypeScript compile không được coi là bằng chứng DI graph hợp lệ.
- Yêu cầu mapper, migration, constraint và transaction analysis khi thay đổi persistence.
- References: `clean-architecture.md`, `dependency-injection.md`, `persistence.md`, `testing.md`.
- `scripts/check_port_bindings.py` tìm Symbol token được `@Inject()` nhưng không có Nest provider binding.

Checker port binding được chạy sau implement và trước review khi task yêu cầu skill này.

### 3.3 `implement-auth-security-change`

Đường dẫn: `ai/skills/implement-auth-security-change/`

- Chuẩn hóa identity/credential handling.
- Kiểm tra password hashing, identifier normalization và database uniqueness.
- Kiểm tra JWT, refresh session, account status, portal permission và request context.
- Yêu cầu negative, concurrency và security test.
- References: `identity-and-credentials.md`, `sessions-and-authorization.md`, `security-verification.md`.

Application-level `exists()` chỉ là preflight phục vụ UX; database constraint và duplicate-key handling vẫn bắt buộc để xử lý race condition.

### 3.4 `review-vertical-slice-completeness`

Đường dẫn: `ai/skills/review-vertical-slice-completeness/`

- Review theo evidence matrix thay vì chỉ đọc handoff.
- Trace requirement đến implementation, wiring/runtime path, test và validation.
- Kiểm tra port → adapter → DI → migration → presentation → test.
- References: `evidence-matrix.md`, `review-gates.md`.
- `scripts/build_evidence_matrix.py` tạo coverage report trước review.

Evidence có thể khai báo theo từng criterion hoặc dùng một entry `slice:<slice-id>` cho toàn bộ slice đã pass. Slice-level evidence giữ handoff ngắn với task lớn mà vẫn bảo toàn traceability.

## 4. Skill discovery

`ai/bin/bootstrap` hiện liên kết từng project skill vào:

```text
~/.project-ai/claude/skills/<skill-name>
~/.project-ai/codex/skills/<skill-name>
```

Bootstrap từ chối ghi đè một skill directory thật không phải symlink. Chạy:

```bash
source .env.ai
./ai/bin/ai bootstrap
```

## 5. Required-skill contract

`task.yaml` có hai trường mới:

```yaml
skills:
  implement:
    - decompose-implementation-task
    - implement-nestjs-vertical-slice
    - implement-auth-security-change
  review:
    - review-vertical-slice-completeness
scope:
  execution_plan_required: true
```

`task.schema.json` validate tên skill và cấu trúc. `prepare-context` xác minh skill, tính aggregate SHA-256 cho `SKILL.md`, `references/`, `scripts/` và `agents/openai.yaml`, sau đó ghi file manifest cùng aggregate hash vào `context.lock.json`. `run-claude` và `run-codex-review` dừng nếu bất kỳ file skill nào không còn khớp hash.

`implementation.json` và `review.json` hỗ trợ:

```json
{
  "applied_skills": [
    {
      "name": "implement-nestjs-vertical-slice",
      "sha256": "<locked hash>",
      "checks_completed": ["port bindings", "persistence", "tests"]
    }
  ]
}
```

Review bị chặn nếu implementation thiếu required skill hoặc dùng hash cũ. Review output cũng bị đánh fail nếu không khai báo review skill bắt buộc.

## 6. Execution plan và scope gate

Đã thêm:

- `ai/schemas/execution-plan.schema.json`
- `ai/templates/execution-plan.json`
- `ai/bin/prepare-plan`

Command:

```bash
./ai/bin/ai task prepare-plan <TASK-ID>
./ai/bin/ai task prepare-plan <TASK-ID> --force
```

`prepare-plan` đọc heading và unchecked checkbox trong `task.md`, sau đó tạo vertical slices deterministic. Mỗi slice có ID, title, dependency, acceptance criteria, deliverables, tests, validation và status.

`prepare-context` không chấp nhận plan draft, sai schema hoặc thuộc cycle cũ. Khi requirement thay đổi, plan cũ được archive và plan template được reset; operator phải chạy lại `prepare-plan --force`.

Task hiện tại đã được chuẩn bị:

- `MEMORIES-0001`: 1 slice, 1 primary criterion, 2 detailed requirements.
- `MEMORIES-0002`: 21 slices, 21 primary criteria, 229 detailed requirements.
- `MEMORIES-0003`: 10 slices, 10 primary criteria, 66 detailed requirements.

## 7. Context integrity gate

`prepare-context` hiện:

- Validate `task.yaml` và `context.yaml` bằng schema.
- Từ chối registered worktree không có `context.repositories.<repo>`.
- Từ chối repository knowledge list rỗng.
- Từ chối neutral-domain placeholder còn được khai báo trong context.
- Validate execution plan và cycle.
- Khóa required skill.
- Ghi `scope_assessment`: số requirement, risk dimensions và cờ `large`.

`register-worktree` tự bổ sung repository knowledge có sẵn:

```text
INDEX.md
architecture.md
conventions.md
testing.md
source-map.md
```

Context của `MEMORIES-0002` và `MEMORIES-0003` đã được sửa để không còn `repositories: {}`. Neutral example domain không phù hợp đã được bỏ khỏi `MEMORIES-0001` và `MEMORIES-0003`.

## 8. Implement gates

`run-claude` hiện:

1. Đọc required implement skills từ task và context lock.
2. Xác minh skill hash.
3. Đưa skill và execution plan vào prompt.
4. Yêu cầu làm từng slice và cập nhật checkpoint.
5. Yêu cầu `implementation.json.applied_skills`.
6. Validate handoff schema sau khi Claude kết thúc.
7. Xác minh applied-skill name/hash.
8. Chạy Nest port-binding checker khi task yêu cầu.
9. Chỉ chuyển về `prepared` nếu tất cả gate pass.

Checkpoint có thêm `current_slice` để resume đúng vertical slice.

## 9. Review gates

Trước khi gọi Codex, `run-codex-review` hiện:

1. Xác minh current-cycle implementation và validation.
2. Xác minh implementation đã áp dụng mọi required skill với đúng hash.
3. Chạy lại Nest port-binding checker.
4. Sinh `validation/skills/acceptance-evidence.json`.
5. Chặn review nếu criterion/slice thiếu evidence hoặc chưa pass.
6. Đưa required review skill và deterministic evidence vào prompt.
7. Validate review output và applied review skill.

Điều này chuyển lỗi completeness từ review suy luận muộn sang gate có bằng chứng trước review.

## 10. Change-cycle và resume

`request-change` archive thêm execution plan, checkpoint, validation skill evidence và exchange/session logs. Sau đó plan/checkpoint được reset theo implementation/change cycle mới, session ID cũ bị xóa.

```bash
./ai/bin/ai task request-change <ID> --title "..."
# hoàn thiện addendum
./ai/bin/ai task prepare-plan <ID> --force
./ai/bin/ai task prepare-context <ID>
./ai/bin/ai task implement <ID>
```

Cơ chế checkpoint/session resume đã triển khai trước đó vẫn được giữ: log theo attempt, trạng thái `interrupted`, resume session nếu có ID và fallback bằng checkpoint + Git snapshot.

## 11. Validation và self-check

`self-check` kiểm tra thêm execution-plan schema/template, skill directory, frontmatter/name, `agents/openai.yaml` và syntax Python script. Smoke pipeline chạy `prepare-plan` trong initial, correction và reopened cycle.

Validation đã chạy:

```text
4/4 skill quick_validate: pass
MEMORIES-0002 execution-plan validation: pass
MEMORIES-0002 Nest port-binding check: pass (28 injected Symbol tokens)
Static self-check: pass
End-to-end smoke pipeline: pass
```

Không gọi Claude hoặc Codex thật trong validation, nên không tiêu thụ agent quota.

## 12. Workflow vận hành mới

### Task mới

```bash
./ai/bin/ai task create PROJ-1234 --type task --parent PROJ-1200 --epic PROJ-1000 --repos backend --title "..."
# chỉnh task.md và thay neutral domain trong context.yaml
./ai/bin/ai task register-worktree PROJ-1234 --repo backend --path worktrees/PROJ-1234/backend
./ai/bin/ai task prepare-plan PROJ-1234 --force
./ai/bin/ai task prepare-context PROJ-1234
./ai/bin/ai task implement PROJ-1234
./ai/bin/ai task validate-code PROJ-1234
./ai/bin/ai task review PROJ-1234
```

Task backend NestJS thông thường dùng decomposition + Nest vertical-slice + review completeness. Task auth/security thêm `implement-auth-security-change`. Không thêm auth skill cho task không liên quan; progressive disclosure tránh nạp context/token không cần thiết.

## 13. Giới hạn còn lại

- Static checker không thay thế module boot/integration test cho dynamic module/provider factory phức tạp.
- `prepare-plan` phân nhóm theo Markdown, không tự hiểu dependency nghiệp vụ; Agent phải refine dependency khi cần.
- Metrics chỉ có token khi CLI trả usage trong machine-readable output.
- Semantic forward-test bằng model thật chưa được tự động hóa; fake-agent E2E và raw fixtures hiện kiểm tra orchestration/gate deterministic mà không tiêu thụ quota.

## 14. Chỉ số nên theo dõi

- Review cycles trung bình mỗi implementation cycle.
- Tỷ lệ implement pass deterministic gate lần đầu.
- Số port thiếu provider/adapter.
- Số criterion/slice thiếu evidence.
- Validation pass lần đầu.
- Token và số attempt trên mỗi slice.
- Số lần resume và phần việc bị làm lại.

Mục tiêu là giảm review cycle, giảm lỗi wiring phát hiện muộn và làm cho các Agent độc lập tạo ra cùng cấu trúc deliverable khi xử lý cùng loại task.

## 15. Cải tiến bổ sung sau vòng đánh giá thứ hai

- Thêm `implement-nextjs-vertical-slice` cho routing/rendering, API client, TanStack Query, form/Zod, token safety, accessibility, responsive states và tests.
- Thêm `check_frontend_security.py` để chặn lưu token/credential/password trong localStorage hoặc sessionStorage.
- Thêm `classify-skills`; mặc định chỉ đề xuất, `--apply` mới sửa `task.yaml`.
- Chuyển plan sang hai tầng: primary criterion theo scope section và field-level checkbox trong `requirement_details`. `MEMORIES-0002` còn 21 primary criteria, trong khi 229 detailed requirements vẫn được bảo toàn.
- `prepare-plan` đọc task gốc cùng requirement addenda và loại duplicate requirement.
- Thêm `check_module_wiring.py` cho use-case/controller reachability và migration registration.
- Thêm `check_auth_invariants.py` cho database uniqueness evidence và credential logging.
- Recompute delivery gates tại review, report và accept; artifact tự tạo thủ công và `--force` không bỏ qua skill/security/evidence gates.
- Giữ khả năng regenerate report cho task legacy completed trước skill locking bằng marker `legacy_grandfathered`.
- Thêm metrics JSONL và `ai metrics <ID>` với cycle, attempt, resume, duration và token usage khi có.
- Thêm fake Claude/Codex E2E kiểm tra quota interruption, session resume, applied skill, review, report, accept và metrics.
- Thêm forward fixtures cho missing provider, weak auth uniqueness và complete vertical slice.
- `self-check --smoke` chạy skill fixtures, orchestration smoke và fake-agent gate pipeline.

Validation bổ sung:

```text
Skill gate fixtures: pass
Fake Claude quota → interrupted: pass
Fake Claude session resume: pass
Fake Codex review lifecycle: pass
Report/accept anti-bypass gates: pass
Aggregate reference-file hash invalidation: pass
Nest module wiring trên MEMORIES-0002: pass
Auth invariant trên MEMORIES-0002: pass
Frontend credential-storage trên MEMORIES-0003: pass
```

## 16. Autonomous implement-review loop

Thêm command:

```bash
./ai/bin/ai task run <ID>
./ai/bin/ai task run <ID> --dry-run
./ai/bin/ai task run <ID> --max-attempts 5
./ai/bin/ai task run <ID> --resume-interrupted --max-interrupted-retries 1
```

Luồng tự động:

```text
implement → validate → review
   ↑                     │
   └──── request-fixes ──┘
```

- Codex `changes_requested`: tạo fix request rồi implement lại.
- Validation fail: tạo `fix-request-validation-attempt-NNN.md` chứa command, status và output tail rồi implement lại.
- Claude `interrupted`: mặc định dừng; chỉ retry session khi operator bật `--resume-interrupted`.
- Codex pass: chạy report và dừng ở `awaiting_user_acceptance`.
- `blocked`, `needs_input`, pipeline failure, max attempts hoặc max review cycles: dừng và giữ đầy đủ state/log/checkpoint.
- Không tự chạy `accept`, không thay đổi requirement, không tăng max cycle và không bỏ qua gate.

`state.yaml.automation` ghi trạng thái, thời điểm bắt đầu/kết thúc, max attempts và số attempt. Fake-agent E2E hiện buộc vòng review đầu trả finding major, xác minh `request-fixes`, chạy implementation lần hai, review pass, report và chờ user acceptance.

Mặc định `review.max_cycles` cho task mới được điều chỉnh từ 10 xuống 5. Task đã tồn tại giữ cấu hình riêng để không âm thầm thay đổi chính sách cycle đang hoạt động.
