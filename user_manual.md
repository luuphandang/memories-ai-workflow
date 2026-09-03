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

## Cài đặt và sử dụng CodeGraph — hướng dẫn nhanh

CodeGraph là lớp knowledge graph cục bộ giúp Claude và Codex tìm symbol, call path và
phạm vi ảnh hưởng của thay đổi mà không phải khám phá toàn bộ repository bằng grep/read.
Workflow tạo một CodeGraph MCP server riêng cho mỗi repository trong task.

### Bước 1 — Cài CodeGraph

Chọn một cách cài:

```bash
# macOS/Linux: standalone bundle chính thức
curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh

# Hoặc cài qua npm
npm install -g @colbymchenry/codegraph
```

Mở terminal mới nếu cần, rồi kiểm tra:

```bash
codegraph --version
codegraph help
```

Không cần chạy `codegraph install`: AI workflow tự sinh MCP config theo task và không
sửa global config của Claude/Codex.

### Bước 2 — Cấu hình `.env.ai`

```bash
export CODEGRAPH_COMMAND="codegraph"
export AI_CODEGRAPH_MODE="optional"
```

Chọn mode phù hợp:

| Mode | Hành vi |
|---|---|
| `optional` | Mặc định; thiếu CLI/index thì agent fallback sang công cụ đọc source thông thường |
| `required` | Dừng workflow nếu bất kỳ repository nào chưa có CodeGraph sẵn sàng |
| `off` | Tắt kiểm tra, sync và MCP CodeGraph |

Sau khi sửa `.env.ai`:

```bash
source .env.ai
./ai/bin/ai self-check
```

### Bước 3 — Khởi tạo graph cho task

Chỉ chạy sau khi developer đã tạo và đăng ký worktree:

```bash
# Tạo index còn thiếu, sync và health-check mọi worktree của task
./ai/bin/ai task codegraph <TASK-ID> --init

# Khóa trạng thái graph cùng requirements/skills/plan
./ai/bin/ai task prepare-context <TASK-ID>
```

Không chạy `codegraph init` ở workspace root. Mỗi worktree cần index `.codegraph/` riêng
để task đa repository không bị trỏ nhầm source.

### Bước 4 — Sử dụng hằng ngày

```bash
# Incremental sync + status
./ai/bin/ai task codegraph <TASK-ID>

# Chỉ status, không sync
./ai/bin/ai task codegraph <TASK-ID> --no-sync

# Chạy pipeline; MCP CodeGraph được gắn tự động vào Claude và Codex
./ai/bin/ai task run <TASK-ID>
```

Sau khi CodeGraph ready, không cần gọi CLI thủ công trong mỗi agent session. Claude và
Codex nhận MCP server `codegraph_<repo>` tự động. File watcher của CodeGraph cập nhật
graph khi source thay đổi; `prepare-context` cũng sync và health-check trước khi khóa
context.

### Kiểm tra trạng thái và xử lý lỗi

Lệnh `task codegraph` in JSON cho từng repository. Trạng thái tốt có:

```json
{
  "available": true,
  "indexed": true,
  "ready": true
}
```

Các lỗi thường gặp:

| Hiện tượng | Cách xử lý |
|---|---|
| `codegraph command is not available on PATH` | Mở terminal mới, kiểm tra `codegraph --version` hoặc đặt `CODEGRAPH_COMMAND` bằng đường dẫn tuyệt đối |
| `index is missing` | Chạy `./ai/bin/ai task codegraph <TASK-ID> --init` |
| Sync/status lỗi | Chạy `codegraph status <worktree-path>` để xem chi tiết, sau đó chạy lại command theo task |
| Graph bị xóa sau khi khóa context | Khởi tạo lại index và chạy lại `prepare-context` |
| Chưa muốn dùng CodeGraph | Đặt `AI_CODEGRAPH_MODE=off` |

Thông tin chi tiết còn được nhắc lại tại mục **4.2 Cài CodeGraph CLI**, mục **5 Khởi tạo
một lần**, mục **11 Chuẩn bị CodeGraph, plan, skill và context**, và mục **21 Tham chiếu
đầy đủ toàn bộ lệnh**.

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
| Execution-plan slice | Phần việc độc lập nhỏ nhất được xử lý trong một Claude session |
| Quick validation | Kiểm tra nhanh giữa các slice: lint, typecheck và architecture check khi được cấu hình |
| Full validation | Toàn bộ validation bắt buộc trước khi Codex review |
| Delta review | Review correction và dependency trực tiếp, chỉ dùng khi phạm vi không nhạy cảm |
| Full review | Review đầy đủ bảy lượt trên toàn bộ implementation hiện hành |
| Review baseline | Contract requirement/risk/test được khóa từ full review đầu tiên để review sau không âm thầm mở rộng goalpost |
| Implementation checklist | Danh sách machine-readable trong `implementation-progress.json`, mỗi item có trạng thái và evidence |

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
- CodeGraph CLI (khuyến nghị; bắt buộc khi `AI_CODEGRAPH_MODE=required`). CodeGraph chạy
  cục bộ, cung cấp knowledge graph cho Claude/Codex qua MCP và không yêu cầu API key.
- Toolchain của từng repository: Node.js `>=20.0.0` + npm (workspaces) cho cả `apps/backend` và `apps/frontend`; backend cần thêm PostgreSQL, Redis và 1 S3-compatible storage (MinIO ở local/dev) chạy qua `apps/backend/docker/docker-compose.yml`.

### 4.1 Cài Claude Code và Codex CLI

macOS/Linux/WSL, cài Claude Code bằng native installer chính thức:

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude --version
claude doctor
claude
```

Lần chạy `claude` đầu tiên, hoàn tất đăng nhập trong trình duyệt. Có thể dùng Homebrew
`brew install --cask claude-code`, nhưng bản Homebrew phải được cập nhật thủ công bằng
`brew upgrade claude-code`. Tham khảo tài liệu chính thức:
<https://code.claude.com/docs/en/setup>.

macOS/Linux, cài Codex CLI bằng standalone installer chính thức:

```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex --version
codex
```

Lần chạy `codex` đầu tiên, chọn **Sign in with ChatGPT** hoặc phương thức đăng nhập phù
hợp. Tham khảo tài liệu chính thức: <https://learn.chatgpt.com/docs/codex/cli>.

Không đặt API key vào repository. Workflow gọi hai executable qua `CLAUDE_COMMAND` và
`CODEX_COMMAND`; nếu executable không nằm trên `PATH`, dùng đường dẫn tuyệt đối trong
`.env.ai`.

Kiểm tra:

```bash
git --version
python3 --version
claude --version
codex --version
codegraph --version
```

### 4.2 Cài CodeGraph CLI

Chọn **một** trong hai cách sau.

macOS/Linux, dùng standalone bundle chính thức:

```bash
curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh
```

Nếu máy đã có Node.js/npm:

```bash
npm install -g @colbymchenry/codegraph
```

Mở terminal mới nếu `codegraph` chưa xuất hiện trên `PATH`, sau đó kiểm tra:

```bash
codegraph --version
codegraph help
```

Workflow này tự sinh MCP config riêng cho từng task/worktree khi gọi Claude và Codex,
do đó **không cần** chạy `codegraph install` để sửa global config của agent. Không chạy
`codegraph init` tại workspace root; mỗi repository phải có index riêng trong worktree
đã đăng ký, được tạo bằng lệnh `ai task codegraph <ID> --init` ở mục 11.

## 5. Khởi tạo một lần

```bash
cd /duong-dan/toi/project
python3 -m venv .venv
source .venv/bin/activate
pip install -r ai/requirements.txt
cp .env.ai.example .env.ai
```

Không chạy `sudo pip`. Mỗi terminal vận hành workflow phải activate `.venv` và source
`.env.ai`; nếu mở terminal mới, chạy lại:

```bash
cd /duong-dan-tuyet-doi/toi/project
source .venv/bin/activate
source .env.ai
```

Cập nhật `.env.ai`:

```bash
export AI_WORKSPACE_ROOT="/duong-dan-tuyet-doi/toi/project"
export AI_ROOT="$AI_WORKSPACE_ROOT/ai"
export CLAUDE_CONFIG_DIR="$HOME/.project-ai/claude"
export CODEX_HOME="$HOME/.project-ai/codex"
export CLAUDE_COMMAND="claude"
export CODEX_COMMAND="codex"
export CODEGRAPH_COMMAND="codegraph"
export AI_CODEGRAPH_MODE="optional"
export CLAUDE_TIMEOUT_SECONDS="3600"
export CODEX_TIMEOUT_SECONDS="1800"
export AI_WARN_CONTEXT_TOKENS="60000"
export AI_MAX_CONTEXT_TOKENS="80000"
```

Nạp biến và cấu hình:

```bash
source .env.ai
./ai/bin/bootstrap
./ai/bin/ai self-check
./ai/bin/ai self-check --smoke
```

`bootstrap` tạo symlink cấu hình và skill của dự án vào
`~/.project-ai/{claude,codex}`, đồng thời cấp executable bit cho các script trong
`ai/bin/`. Lệnh này có thể chạy lại sau khi thêm skill/cấu hình mới. Nó thay thế các
symlink do chính workspace quản lý, nhưng từ chối ghi đè một thư mục skill thật đã tồn
tại. `self-check` kiểm tra cấu hình/schema/skill/policy; `--smoke` chạy pipeline giả lập
trong thư mục tạm, không gọi Claude/Codex thật.

Không lưu token, secret hoặc credential trong workspace. `CLAUDE_TIMEOUT_SECONDS` và `CODEX_TIMEOUT_SECONDS` phải là số nguyên dương. Khi Claude implement bị timeout, quota hoặc session limit, task chuyển sang `interrupted`; mỗi attempt có log riêng và lần `implement` sau resume session nếu có, hoặc phục hồi từ `implementation-progress.json` cùng Git diff. Timeout của các bước khác vẫn được xử lý theo script tương ứng.

Các biến `AI_*` kiểm soát ngân sách context:

- `AI_WARN_CONTEXT_TOKENS`: ngưỡng ghi cảnh báo token vào `state.yaml`; mặc định `60000`.
- `AI_MAX_CONTEXT_TOKENS`: ngưỡng ghi nhận budget breach và buộc phần việc tiếp theo dùng fresh bounded session; mặc định `80000`.

Mỗi giá trị phải là số nguyên dương. Workflow không áp đặt giới hạn số agent turn cho Claude; phiên implement tiếp tục cho tới khi hoàn tất, timeout, hoặc gặp lỗi dịch vụ thực sự.

Các biến CodeGraph:

- `CODEGRAPH_COMMAND`: tên command trên `PATH` hoặc đường dẫn tuyệt đối tới executable;
  mặc định `codegraph`.
- `AI_CODEGRAPH_MODE=optional`: chế độ mặc định; thiếu CLI/index thì workflow vẫn chạy
  và agent dùng công cụ khám phá source thông thường.
- `AI_CODEGRAPH_MODE=required`: `prepare-context`, implement hoặc review dừng nếu CLI hay
  index của bất kỳ repository nào không sẵn sàng. Khuyến nghị cho CI hoặc team đã chuẩn
  hóa CodeGraph.
- `AI_CODEGRAPH_MODE=off`: không kiểm tra, sync hoặc nối CodeGraph MCP vào agent.

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
  max_fix_cycles: 5
  fail_on: [blocker, major]
report:
  language: vi
  include_diff_stat: true
  include_changed_files: true
  include_test_results: true
  include_review_findings: true
  include_knowledge_updates: true
```

- `review.max_fix_cycles`: số fix request thực tế tối đa trong một implementation cycle;
  delta/full review invocation không tiêu thụ counter này. `max_cycles` cũ vẫn là fallback tương thích.
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

## 11. Chuẩn bị CodeGraph, plan, skill và context

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

# Tạo index nếu worktree chưa có .codegraph/, đồng thời sync và health-check.
./ai/bin/ai task codegraph PROJ-1002 --init

# Luôn khóa context sau khi CodeGraph đã sẵn sàng.
./ai/bin/ai task prepare-context PROJ-1002
```

`task codegraph` xử lý tất cả worktree đã khai báo trong `task.yaml` và in trạng thái
JSON theo repository. Các biến thể:

```bash
# Tạo index còn thiếu, sync index hiện có và kiểm tra status
./ai/bin/ai task codegraph PROJ-1002 --init

# Chỉ sync và kiểm tra; trả mã lỗi nếu CLI/index chưa sẵn sàng
./ai/bin/ai task codegraph PROJ-1002

# Chỉ kiểm tra index, không chạy incremental sync
./ai/bin/ai task codegraph PROJ-1002 --no-sync
```

Sau `--init`, mỗi worktree có thư mục `.codegraph/`. Khi agent chạy, workflow sinh một
MCP server riêng cho mỗi repository với tên đã chuẩn hóa `codegraph_<repo>` và trỏ
`--path` đúng worktree. Ví dụ repository `backend-api` dùng server
`codegraph_backend_api`. Cách này ngăn Claude/Codex truy vấn nhầm graph khi một task có
nhiều repository.

`prepare-context` tự chạy incremental sync và `codegraph status --json` đối với index
hiện có, sau đó ghi kết quả vào:

```text
ai/tasks/PROJ-1002/context.lock.json
└── codegraph
    ├── mode
    └── repositories.<repo>
        ├── available
        ├── indexed
        └── ready
```

Sau khi agent bắt đầu, CodeGraph MCP theo dõi thay đổi source và tự cập nhật graph.
Agent ưu tiên CodeGraph cho kiến trúc, symbol flow, caller/callee và impact analysis;
agent vẫn đọc file trực tiếp để xác minh nội dung vừa sửa, file phi mã nguồn hoặc phần
CodeGraph báo thiếu/stale.

`classify-skills` xác định skill implement/review cần dùng. `prepare-plan` tạo execution plan từ requirements và skill đã chọn. `prepare-context` là bước khóa cuối cùng, vì vậy phải chạy lại sau mọi thay đổi trong `task.md`, requirement addendum, `task.yaml.skills` hoặc execution plan.

Script sẽ:

- Kiểm tra file knowledge.
- Kiểm tra worktree và branch.
- Đưa `task.md` và mọi change addendum vào requirement manifest.
- Tạo SHA-256 cho tài liệu.
- Khóa aggregate hash của các skill bắt buộc và execution plan.
- Ghi `context.lock.json`.
- Sync/health-check CodeGraph và khóa trạng thái từng repository trong
  `context.lock.json.codegraph`.

Nếu active change cycle còn marker chưa xử lý, script dừng để tránh agent làm theo yêu cầu thiếu.

## 12. Chạy pipeline ban đầu

### 12.1 Luồng tự động khuyến nghị

```bash
./ai/bin/ai task run PROJ-1002 --dry-run
./ai/bin/ai task run PROJ-1002
```

Pipeline vận hành theo luồng tiết kiệm token:

```text
chọn một runnable slice
→ fresh bounded Claude session cho đúng một slice
→ implementation_ready_for_validation
→ quick validation
→ slice tiếp theo
→ full validation sau slice cuối
→ full Codex review
→ correction bằng bounded implement session
→ delta review khi an toàn
→ final full review
→ report
```

Mỗi Claude session chỉ được xử lý một slice. Script tạo compact context bundle tại `worktrees/<ID>/.ai/input/slice-context-<slice>.json`; agent đọc bundle trước và chỉ mở knowledge/requirement liên quan khi cần. Evidence và changed files của slice đã hoàn thành phải được merge vào `implementation.json`, không được ghi đè bằng dữ liệu của riêng slice hiện tại.

Claude chỉ sửa source, test, handoff và checkpoint; không sở hữu trạng thái trong
`execution-plan.json`. Chỉ orchestrator được chuyển slice sang `completed` sau quick
validation. Nếu pipeline dừng sau handoff, trạng thái `implementation_ready_for_validation`
giúp lần chạy sau tiếp tục thẳng từ validation, không gọi Claude lại cho cùng slice.
Task cũ/interrupted có slice completed nhưng thiếu progress/handoff evidence sẽ được tự
reconcile về `in_progress` hoặc `pending`.

Danh sách requirement document đưa vào implement/review chỉ gồm `task.md` cùng
addendum của các cycle *chưa gộp* (xem mục 17 về `consolidate-requirements`); addendum
đã gộp không bị đọc lại mỗi session nữa.

Validation failure được chuyển thành structured checklist và fix request giới hạn tối đa
40 dòng output liên quan. Correction được phân loại `code_or_test`, `evidence_or_handoff`
hoặc `validation`; evidence-only correction bị cấm sửa source để tránh tự làm stale evidence.
Khi Codex pass, reviewer vẫn giữ trạng thái `reviewing`; chỉ `report` sinh thành công mới
chuyển sang `awaiting_user_acceptance`. Pipeline không tự accept task.

Tuỳ chọn kiểm soát:

```bash
./ai/bin/ai task run PROJ-1002 --max-attempts 5
./ai/bin/ai task run PROJ-1002 --resume-interrupted --max-interrupted-retries 1
```

Không bật `--resume-interrupted` cho đến khi quota hoặc lỗi availability đã được giải quyết. Pipeline dừng khi chạm `review.max_fix_cycles`, `--max-attempts`, gặp `blocked`/`needs_input`, hoặc gặp lỗi không thể retry.

Xem metrics cục bộ bằng:

```bash
./ai/bin/ai metrics PROJ-1002
```

Dữ liệu runtime gồm:

- Số implement/review attempt và resume.
- Thời lượng.
- Input token, cache creation token, cache-read token và output token — cho cả Claude
  (implement) và Codex (review, trích từ `codex exec --json`).
- Tổng context token, agent turn và chi phí khi CLI cung cấp.
- Tổng hợp chi phí/token theo execution-plan slice.
- Review mode và reasoning effort của Codex.

Khi đánh giá chi phí, không chỉ nhìn `input_tokens`: với session dài, phần lớn chi phí có thể nằm trong `cache_read_input_tokens`.

### 12.1.1 Luồng thủ công để chẩn đoán hoặc can thiệp

```bash
./ai/bin/ai task implement PROJ-1002 --dry-run
./ai/bin/ai task implement PROJ-1002
./ai/bin/ai task validate-code PROJ-1002 --tier quick
./ai/bin/ai task validate-code PROJ-1002 --tier full
./ai/bin/ai task review PROJ-1002 --mode auto
./ai/bin/ai task request-fixes PROJ-1002  # khi review yêu cầu sửa
./ai/bin/ai task report PROJ-1002         # khi validation và review đã pass
```

Luồng này hữu ích khi cần xem hoặc xử lý riêng từng gate. Bình thường nên dùng `task run` để tránh bỏ sót validation, fix request hoặc report.

### 12.2 Validation

```bash
./ai/bin/ai task validate-code PROJ-1002 --dry-run
./ai/bin/ai task validate-code PROJ-1002 --tier quick
./ai/bin/ai task validate-code PROJ-1002 --tier full
```

`--dry-run` chỉ hiển thị/kế hoạch hóa command. Kết quả dry-run không được phép dùng để review, sinh acceptance report hoặc accept task.

- `--tier quick`: chạy các static/architecture check phù hợp để phản hồi sớm giữa các slice. Kết quả này không đủ điều kiện để review.
- `--tier full`: chạy toàn bộ command bắt buộc và là tier duy nhất được dùng trước Codex review.

Command thật lấy từ `ai/repos/<repo>/commands.yaml`.

### 12.3 Codex review

```bash
./ai/bin/ai task review PROJ-1002 --dry-run
./ai/bin/ai task review PROJ-1002 --mode auto
```

Review mode:

- `auto` — khuyến nghị: full review lần đầu; delta review cho correction an toàn.
- `delta` — chỉ review finding mới nhất, diff bị ảnh hưởng, dependency trực tiếp, test và regression. Script từ chối mode này nếu fix request liên quan auth, security, API contract, database, migration, transaction hoặc concurrency.
- `full` — đủ bảy lượt requirements, diff, architecture, behavior, tests, security và regression.

Codex reasoning effort được chọn theo risk trong context lock: task ít rủi ro dùng `low`, task lớn dùng `medium`, còn security/database/API/background dùng `high`. Delta review dùng `medium`. Trong pipeline tự động, delta pass luôn được xác nhận lại bằng một final full review trước khi sinh report.

Full review đầu tiên sinh `review-baseline.json`, khóa acceptance criteria, risk area và
test contract. Review sau phải gắn finding mới với correction diff; nếu cần mở rộng input/
behavior contract thì trả `blocked` như requirement gap, không âm thầm gửi goalpost mới cho Claude.

Nếu Codex yêu cầu sửa, `review.max_fix_cycles` áp dụng cho số fix request thực tế trong
implementation cycle hiện hành. Mặc định là `5`; review retry/delta/final-full có counter riêng.

```bash
./ai/bin/ai task request-fixes PROJ-1002
./ai/bin/ai task implement PROJ-1002
./ai/bin/ai task validate-code PROJ-1002 --tier full
./ai/bin/ai task review PROJ-1002 --mode auto
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
# Cách tối giản (`--accepted-by` mặc định là `user`)
./ai/bin/ai task accept PROJ-1002

# Hoặc ghi rõ người nghiệm thu và ghi chú
./ai/bin/ai task accept PROJ-1002 \
  --accepted-by "Tên người xác nhận" \
  --note "Đã kiểm tra trên môi trường local/dev"
```

Thay `PROJ-1002` bằng ID task thực tế, ví dụ:

```bash
./ai/bin/ai task accept MEMORIES-0009
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

Không xóa/sửa lịch sử cycle cũ để “làm sạch” yêu cầu — các file `requirement-addendum.md`
trong `changes/cycle-*/` không bao giờ bị xóa.

Để tránh mỗi implement/review session phải đọc lại toàn bộ chuỗi addendum khi task đã
qua nhiều cycle, có thể **gộp** (không xóa) các addendum đã được chấp nhận vào `task.md`
khi task ở trạng thái `completed`:

```bash
./ai/bin/ai task consolidate-requirements PROJ-1002
# review requirements-consolidation-draft.md
./ai/bin/ai task apply-requirements-consolidation PROJ-1002 --approved-by "Tên người duyệt"
```

`consolidate-requirements` archive draft/manifest cũ (nếu còn sót) rồi mới gọi Claude
soạn draft mới, kèm `requirements-consolidation-manifest.json` ghi sha256 của `task.md`
nguồn, từng addendum được gộp và chính draft — không tự ghi `task.md`.

`apply-requirements-consolidation` đối chiếu lại toàn bộ manifest với trạng thái hiện tại
trước khi áp dụng: `task_id`, cycle range, sha256 của `task.md`/từng addendum/draft. Nếu
bất kỳ phần nào đã bị sửa, thiếu, hoặc thuộc cycle khác (vd. có cycle mới mở ra sau khi
tạo draft) — lệnh từ chối áp dụng thay vì âm thầm dùng dữ liệu cũ/sai. `--approved-by`
không được rỗng. Khi hợp lệ: ghi đè `task.md`, backup bản cũ **cùng với** draft và
manifest đã dùng vào `task-md-history/<khoảng cycle>/` (giữ nguyên để audit, không xóa
provenance), rồi ghi nhận cycle đã gộp vào `state.yaml`. Từ lần `implement`/`review` kế
tiếp, các addendum đã gộp không còn bị bắt buộc đọc lại (file gốc vẫn còn trên đĩa để tra
cứu); `report` vẫn luôn liệt kê đầy đủ lịch sử addendum. Luôn review draft trước khi áp
dụng — đây là bước gộp nội dung bằng ngôn ngữ tự nhiên, không có schema kiểm chứng được
tính đúng đắn ngữ nghĩa (chỉ kiểm chứng được tính toàn vẹn/không bị tamper qua sha256).

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
| `implementation_ready_for_validation` | Handoff slice hợp lệ; lần chạy/restart tiếp tục từ validation, không gọi lại Claude |
| `interrupted` | Implementation bị gián đoạn; có thể resume session hoặc tiếp tục từ checkpoint và Git diff |
| `validating` | Đang chạy kiểm tra deterministic |
| `reviewing` | Codex đang/đã review, chưa sinh acceptance report |
| `changes_requested_by_codex` | Codex yêu cầu sửa kỹ thuật |
| `changes_requested_by_validation` | Validation đã tạo checklist lỗi và chờ remediation tự động |
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
└── (runtime nằm tại worktrees/<ID>/.ai/)

worktrees/<ID>/.ai/
├── input/                          # Slice context và bounded fix request
├── exchange/                       # Claude/Codex session log
├── validation/                     # Quick/full validation và skill evidence hiện hành
└── metrics/                        # Token, turn, cost và attempt metrics
```

## 21. Tham chiếu đầy đủ toàn bộ lệnh

Luôn gọi qua `./ai/bin/ai`; các file executable khác trong `ai/bin/` là implementation
detail. Xem danh sách ngắn bằng `./ai/bin/ai --help`. Bảng dưới đây là nguồn tham chiếu
đầy đủ hơn vì dispatcher hiện chỉ in usage tổng quát khi truyền `--help` cho subcommand.

### 21.1 Workspace và chẩn đoán

| Lệnh | Chức năng và tùy chọn |
|---|---|
| `ai bootstrap` | Cài symlink config/skill cục bộ vào `~/.project-ai/`; chạy lại sau khi đổi config hoặc thêm skill. |
| `ai self-check` | Kiểm tra JSON/schema, skill, quyền Claude, Codex trust, path và cấu hình CodeGraph. |
| `ai self-check --smoke` | Thêm pipeline giả lập end-to-end trong temp; không gọi agent thật. |
| `ai indexes rebuild` | Sinh lại năm index `backlog`, `in-progress`, `review`, `completed`, `failed` từ mọi `state.yaml`. |
| `ai metrics <ID>` | Tổng hợp attempt, thời gian, token, turn và cost từ runtime metrics của task. |

### 21.2 Tạo task và chuẩn bị context

| Lệnh | Chức năng và tùy chọn |
|---|---|
| `ai task create <ID> --type epic|story|task --title <TITLE>` | Tạo hồ sơ task. Tùy chọn: `--parent`, `--epic`, `--priority lowest|low|medium|high|highest|critical` (mặc định `medium`), `--repos backend,frontend`. ID chỉ gồm chữ hoa, số và dấu gạch theo schema của workspace. |
| `ai task register-worktree <ID> --repo <NAME> --path <PATH>` | Đăng ký worktree do developer đã tạo, ghi branch/base SHA và tự thêm knowledge repo vào context. `--base-ref` mặc định `origin/develop`; `--read-only` đặt `writable: false`; `--allow-missing` chỉ dùng để khai báo trước path chưa tồn tại và sẽ khiến các gate sau chưa thể chạy. |
| `ai task classify-skills <ID>` | Chỉ in các skill được đề xuất từ scope. `--apply` ghi đề xuất vào `task.yaml`; phải review trước khi apply. |
| `ai task prepare-plan <ID>` | Sinh `execution-plan.json`; từ chối ghi đè plan hiện có trừ khi dùng `--force`. Sau mỗi thay đổi requirement/skill phải tạo lại plan. |
| `ai task codegraph <ID>` | Sync incremental và in status JSON cho mọi worktree. `--init` tạo index còn thiếu; `--no-sync` chỉ kiểm tra. |
| `ai task prepare-context <ID>` | Kiểm tra requirement, knowledge, worktree/branch, skill, plan và CodeGraph rồi khóa `context.lock.json`. `--allow-placeholders` chỉ dành cho template/demo; không dùng cho task thật vì cho phép marker chưa được điền. |

### 21.3 Implement, validation, review và report

| Lệnh | Chức năng và tùy chọn |
|---|---|
| `ai task run <ID>` | Pipeline tự động implement → resume-at-validation → quick/full validation → review/fix → final full review → report. Handoff hợp lệ không bị implement lại khi restart. `--dry-run` không tạo bằng chứng đủ điều kiện nghiệm thu; `--max-attempts N` giới hạn attempt trong lần chạy; `--resume-interrupted` cho phép retry phiên Claude bị gián đoạn; `--max-interrupted-retries N` mặc định `1`. |
| `ai task implement <ID>` | Chạy một Claude implement session/slice. `--dry-run` không gọi CLI; `--print-command` in command đã dựng để chẩn đoán. Nếu có session/checkpoint hợp lệ, lần gọi sau có thể resume. |
| `ai task validate-code <ID>` | Chạy command trong `ai/repos/<repo>/commands.yaml`. `--tier quick|full` (mặc định `full`); `--dry-run` chỉ lập kế hoạch; `--include-optional` chạy cả command `required: false`; `--command <NAME>` chỉ chạy tên được chọn và có thể lặp option. Chỉ full validation thật mới đủ gate review/accept. |
| `ai task review <ID>` | Chạy Codex read-only review. `--mode auto|full|delta` (mặc định `auto`); `--dry-run` không tạo verdict dùng được; `--print-command` in command để debug. Delta bị từ chối với scope nhạy cảm và trước report vẫn cần final full review. |
| `ai task request-fixes <ID>` | Chuyển findings chặn thành checklist/fix request có correction scope và remediation type; tăng `fix_cycle` hoặc block khi đạt `review.max_fix_cycles`. |
| `ai task report <ID>` | Kiểm gate rồi sinh `final-report.md` và chuyển sang `awaiting_user_acceptance`. `--report-only` chỉ render lại báo cáo, thường được `accept` gọi nội bộ; `--force` bỏ qua một số guard validation và chỉ dành cho phục hồi có kiểm soát, không dùng để nghiệm thu kết quả chưa pass. |

### 21.4 Nghiệm thu, thay đổi yêu cầu và knowledge

| Lệnh | Chức năng và tùy chọn |
|---|---|
| `ai task accept <ID>` | Chỉ accept khi validation thật + Codex pass + quality gate hợp lệ. `--accepted-by <NAME>` mặc định `user`; `--note <TEXT>` lưu ghi chú nghiệm thu. |
| `ai task request-change <ID> --title <TITLE>` | Tạo cycle mới và snapshot baseline. `--kind auto|correction|requirement_change`; `auto` suy ra theo trạng thái. `--from-file <FILE>` chép nội dung phản hồi có sẵn vào `user-request.md`. Không tự tạo/checkout worktree. |
| `ai task consolidate-requirements <ID>` | Với task completed, dùng Claude tạo draft gộp addendum nhưng chưa sửa `task.md`. `--dry-run` hoặc `--print-command` để kiểm tra trước. |
| `ai task apply-requirements-consolidation <ID> --approved-by <NAME>` | Kiểm hash/cycle/manifest rồi áp dụng draft đã được người duyệt xác nhận; backup lịch sử để audit. |
| `ai task update-knowledge <ID>` | Hiển thị kế hoạch cập nhật knowledge đã approved. `--apply` mới ghi vào `ai/shared`, `ai/repos`, `ai/domains`; `--force` là escape hatch có kiểm soát khi cần vượt guard trạng thái. |

Ví dụ vận hành hằng ngày:

```bash
source .venv/bin/activate
source .env.ai
./ai/bin/ai self-check
./ai/bin/ai task codegraph PROJ-1002
./ai/bin/ai task run PROJ-1002
./ai/bin/ai metrics PROJ-1002
```

## 22. Xử lý sự cố thường gặp

Trước tiên luôn thu thập trạng thái, không sửa artifact máy đọc bằng tay:

```bash
source .venv/bin/activate
source .env.ai
./ai/bin/ai self-check
sed -n '1,240p' ai/tasks/<ID>/state.yaml
find worktrees/<ID>/.ai -maxdepth 3 -type f | sort
```

| Hiện tượng | Kiểm tra và cách xử lý |
|---|---|
| `ModuleNotFoundError: yaml` hoặc `jsonschema` | Activate đúng `.venv`, rồi chạy `python -m pip install -r ai/requirements.txt`. Xác minh bằng `python -c 'import yaml, jsonschema'`. |
| `claude/codex/codegraph: command not found` | Chạy `command -v <cmd>` và `<cmd> --version`; mở terminal mới hoặc đặt đường dẫn tuyệt đối vào `CLAUDE_COMMAND`, `CODEX_COMMAND`, `CODEGRAPH_COMMAND`, rồi `source .env.ai`. |
| Claude Code không đăng nhập/chạy bất thường | Chạy `claude doctor`, sau đó `claude` để đăng nhập lại. Kiểm tra `CLAUDE_CONFIG_DIR` sau khi source `.env.ai`. |
| Codex chưa đăng nhập | Chạy `codex` tương tác và hoàn tất **Sign in with ChatGPT**, sau đó `codex --version`. Kiểm tra `CODEX_HOME` đúng `~/.project-ai/codex`. |
| `self-check` báo Codex không trust workspace | Cập nhật path tuyệt đối hiện tại trong `ai/config/codex/config.toml`, chạy lại `bootstrap`, rồi `self-check`. Đặc biệt cần làm sau khi di chuyển workspace. |
| `self-check` báo path không khớp | Sửa `AI_WORKSPACE_ROOT` trong `.env.ai` và path project trong Codex config; `source .env.ai`, `bootstrap`, `self-check`. |
| Worktree path không tồn tại/không phải Git worktree | `git -C apps/<repo> worktree list`; khôi phục worktree đúng branch, rồi đăng ký lại có chủ đích. Không dùng `--allow-missing` để vượt gate chạy thật. |
| Branch hiện tại khác branch đã đăng ký | `git -C worktrees/<ID>/<repo> branch --show-current`; quay lại branch đúng theo Git policy hoặc đăng ký lại sau khi xác nhận. Script không tự checkout. |
| `prepare-context` báo context/skill/plan stale | Chạy lại `classify-skills --apply` khi cần, `prepare-plan --force`, `codegraph --init` và cuối cùng `prepare-context`. Luôn khóa context sau thay đổi cuối. |
| Placeholder chưa xử lý | Tìm bằng `rg 'BỔ SUNG THEO' ai/tasks/<ID> ai/domains/<domain>` và điền dữ liệu thật. Không dùng `--allow-placeholders` cho production task. |
| CodeGraph thiếu index/stale | `ai task codegraph <ID> --init`; kiểm tra JSON `available/indexed/ready`. Nếu vẫn lỗi, chạy `codegraph status <worktree-path>` và kiểm tra `CODEGRAPH_COMMAND`. Tạm fallback bằng `AI_CODEGRAPH_MODE=optional` hoặc tắt bằng `off`. |
| Validation fail | Đọc `worktrees/<ID>/.ai/validation/summary.json` và file `<repo>.json`; chạy riêng command lỗi bằng `ai task validate-code <ID> --command <NAME> --tier full`. Sửa source/config rồi chạy lại full validation. |
| Dry-run pass nhưng review/report bị chặn | Đây là hành vi đúng: chạy validation thật `--tier full`, rồi review thật. Dry-run không phải evidence. |
| Task ở `interrupted` | Đọc log mới nhất trong `worktrees/<ID>/.ai/exchange/`, xử lý quota/network/timeout, rồi chạy `ai task run <ID> --resume-interrupted --max-interrupted-retries 1`. Không resume liên tục khi nguyên nhân chưa hết. |
| Claude lặp lại slice đã hoàn tất | Kiểm `state.status`. Với handoff hợp lệ phải là `implementation_ready_for_validation`; chạy `task run` để resume validation, không gọi `task implement` thủ công. Workflow sẽ tự sửa plan completed sai nếu thiếu progress/handoff evidence. |
| Claude timeout | Tăng `CLAUDE_TIMEOUT_SECONDS` bằng số nguyên dương nếu slice hợp lý nhưng cần lâu hơn; nếu slice quá lớn, sửa execution plan và `prepare-context` lại. |
| Codex timeout | Tăng `CODEX_TIMEOUT_SECONDS`, source env và chạy lại review; kiểm tra log exchange trước. |
| Review yêu cầu sửa | Ưu tiên `task run`; correction được tự phân loại code/evidence/validation. Khi đạt `review.max_fix_cycles`, task block. Finding mở rộng contract ngoài `review-baseline.json` phải được xử lý như requirement gap. |
| Delta review bị từ chối | Chạy `ai task review <ID> --mode full`; đây là bắt buộc với auth/security/API/database/migration/transaction/concurrency. |
| Report/accept bị chặn | Kiểm `state.yaml`, cycle trong implementation/review/validation, verdict, `review.fail_on`, và full-validation không phải dry-run. Không dùng `--force` chỉ để vượt nghiệm thu. |
| Requirement consolidation báo hash/cycle mismatch | Không sửa manifest. Tạo lại draft bằng `consolidate-requirements`, review lại rồi apply với người duyệt. |
| Index trạng thái sai | Chạy `ai indexes rebuild`; index là dữ liệu sinh, `state.yaml` mới là nguồn thật. |

Log/artifact cần gửi khi nhờ hỗ trợ: command đầy đủ đã chạy, exit code, `state.yaml`,
`context.lock.json`, validation `summary.json`, và log exchange liên quan. Xóa/redact secret
trước khi chia sẻ; không gửi `.env.ai` hoặc file cấu hình chứa bí mật.

## 23. Tự kiểm tra workspace

Chạy kiểm tra tĩnh:

```bash
./ai/bin/ai self-check
```

Chạy smoke test end-to-end trong thư mục tạm, không gọi dịch vụ Claude/Codex thật và không thay đổi task/worktree thật:

```bash
./ai/bin/ai self-check --smoke
```

Smoke test tạo repository và worktree dùng một lần, dùng fake Claude/Codex CLI để kiểm tra skill fixtures, resume/checkpoint, vòng tự động implement–validate–review–request-fixes, `review.fail_on`, correction, reopening, report và user acceptance.

## 24. Dữ liệu ví dụ

Xem:

```text
ai/examples/tasks/PROJ-1002/
```

- `cycle-001`: correction trước acceptance.
- `cycle-002`: requirement change sau completed.

Toàn bộ nội dung ví dụ là trung lập và không dùng dữ liệu dự án thật.

## 25. Checklist vận hành

### Trước Claude

- [ ] Jira hierarchy đúng.
- [ ] `task.md` đầy đủ.
- [ ] Worktree đúng path và branch.
- [ ] Context không chứa secret.
- [ ] Active change addendum không còn placeholder chưa xử lý.
- [ ] Skill implement/review đã được classify, kiểm tra và apply.
- [ ] `execution-plan.json` phản ánh requirements hiện hành.
- [ ] Mỗi slice đủ nhỏ để hoàn thành trong ngân sách turn; dependency giữa các slice đúng.
- [ ] Nếu dùng CodeGraph, `./ai/bin/ai task codegraph <ID> --init` đã pass cho mọi worktree.
- [ ] `context.lock.json.codegraph.repositories.<repo>.ready` là `true` khi chạy ở mode
  `required`.
- [ ] `context.lock.json` được tạo sau lần sửa requirements/skill/plan cuối cùng.

### Trước Codex

- [ ] `implementation.json` hợp lệ.
- [ ] Full validation của cycle hiện hành đã chạy; quick validation không được dùng thay thế.
- [ ] Không dùng validation cũ trong baseline.
- [ ] Implementation progress và Git diff của attempt hiện hành đã được ghi nhận.
- [ ] Mọi checklist item được giao đã `completed` với evidence; không tự sửa execution-plan status.
- [ ] `review-baseline.json` đã được tạo từ full review đầu tiên và không bị mở rộng âm thầm.
- [ ] Nếu đã dùng delta review, final full review cũng đã pass.

### Trước accept

- [ ] Codex pass.
- [ ] Validation pass.
- [ ] Pipeline đang ở `awaiting_user_acceptance`, không phải `interrupted` hoặc `blocked`.
- [ ] `final-report.md` và finalized implementation/change/review cycle khớp trạng thái hiện hành.
- [ ] Người dùng đã test kết quả.
- [ ] Không còn correction cần thực hiện.

### Sau accept

- [ ] `acceptance.yaml` là accepted.
- [ ] `state.yaml` là completed.
- [ ] Knowledge proposal được review trước khi apply.
- [ ] Giữ worktree nếu có khả năng cần mở lại task; xóa theo Git policy khi không còn cần.
