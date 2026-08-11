# Handoff review: Tích hợp CodeGraph vào AI workflow

Ngày tổng hợp: 2026-08-10  
Reviewer đề xuất: Claude  
Trạng thái: đã triển khai trong working tree, chưa commit

## 1. Mục tiêu thay đổi

Tích hợp [CodeGraph](https://github.com/colbymchenry/codegraph) vào AI control plane hiện
tại để Claude implementer và Codex reviewer có thể dùng knowledge graph theo đúng
repository/worktree của từng task.

Yêu cầu thiết kế:

- Hỗ trợ task có nhiều repository mà không truy vấn nhầm graph.
- Không tự tải hoặc cài binary bên ngoài khi người dùng chưa cho phép.
- Không làm hỏng workflow hiện tại nếu team chưa cài CodeGraph.
- Có thể bật fail-fast cho môi trường đã chuẩn hóa CodeGraph.
- Khóa trạng thái CodeGraph cùng task context để agent biết graph nào sẵn sàng.
- Ưu tiên graph cho architecture/symbol-flow/impact, nhưng vẫn cho phép đọc source trực
  tiếp khi cần xác minh nội dung vừa thay đổi hoặc graph thiếu/stale.

## 2. Thiết kế đã triển khai

### 2.1 Chế độ vận hành

Hai biến môi trường mới:

```bash
export CODEGRAPH_COMMAND="codegraph"
export AI_CODEGRAPH_MODE="optional"
```

`AI_CODEGRAPH_MODE` hỗ trợ:

- `optional`: mặc định; thiếu CLI/index thì workflow tiếp tục bằng công cụ khám phá
  source thông thường.
- `required`: fail-fast nếu CLI hoặc index của bất kỳ repository nào không sẵn sàng ở
  lúc prepare-context hay lúc agent bắt đầu.
- `off`: không kiểm tra, sync hoặc nối MCP.

### 2.2 Index theo task/worktree

CLI mới:

```bash
./ai/bin/ai task codegraph <TASK-ID> --init
./ai/bin/ai task codegraph <TASK-ID>
./ai/bin/ai task codegraph <TASK-ID> --no-sync
```

Ý nghĩa:

- `--init`: tạo index còn thiếu, sync và kiểm tra status cho mọi worktree trong
  `task.yaml`.
- Không option: sync index hiện có và kiểm tra status.
- `--no-sync`: chỉ kiểm tra status.
- Command in ra JSON trạng thái theo repository và trả exit code khác `0` nếu có repository
  chưa ready.

Không tạo một graph chung tại workspace root. Mỗi repository dùng `.codegraph/` nằm
trong worktree tương ứng.

### 2.3 Context locking

`prepare-context` gọi incremental sync và `codegraph status --json` trước khi tạo lock.
Kết quả được ghi thêm vào:

```text
context.lock.json
└── codegraph
    ├── mode
    └── repositories.<repo>
        ├── path
        ├── available
        ├── indexed
        ├── ready
        └── status | status_text | reason
```

Ở `required` mode, prepare-context dừng khi CLI, worktree, index, sync hoặc status không
hợp lệ. Ở `optional` mode, nguyên nhân fallback được ghi vào lock.

### 2.4 MCP động theo repository

Khi chạy Claude/Codex, chỉ repository được lock với `ready: true`, còn tồn tại
`.codegraph/` và có CLI trên `PATH` mới được nối MCP.

Tên server được chuẩn hóa:

```text
repository backend-api → MCP server codegraph_backend_api
```

Mỗi server chạy:

```bash
codegraph serve --mcp --path <absolute-worktree-path>
```

- Claude nhận JSON MCP config được sinh tại runtime qua `--mcp-config`.
- Codex nhận `mcp_servers.<name>.command/args` bằng các config override `-c`.
- Không sửa global Claude/Codex MCP config.
- Runtime kiểm tra lại CLI và `.codegraph/` để tránh dùng lock cũ khi graph đã bị xóa.

### 2.5 Hướng dẫn agent

Prompt và instruction chung yêu cầu:

- Dùng `codegraph_<repo>` trước cho architecture, symbol flow, callers/callees và impact.
- Dùng grep/read để kiểm tra live edits, non-code files hoặc graph gap/staleness.
- Fallback rõ ràng khi task không có graph sẵn sàng.

Claude permission cho MCP server động được thêm bằng:

```text
mcp__codegraph_*__*
```

## 3. File đã thêm

| File | Vai trò |
|---|---|
| `ai/bin/lib/codegraph.py` | Mode validation, CLI discovery, init/sync/status, runtime readiness, sinh Claude/Codex MCP config và prompt guidance |
| `ai/bin/manage-codegraph` | Entry point cho `ai task codegraph` |
| `ai/tests/test_codegraph.py` | Test optional fallback và MCP config theo worktree |

## 4. File đã cập nhật

| File | Nội dung thay đổi |
|---|---|
| `.env.ai.example` | Thêm `CODEGRAPH_COMMAND`, `AI_CODEGRAPH_MODE` và hướng dẫn ngắn |
| `ai/bin/ai` | Đăng ký command `task codegraph` và cập nhật usage |
| `ai/bin/prepare-context` | Sync/health-check và ghi CodeGraph status vào context lock |
| `ai/bin/run-claude` | Sinh MCP JSON động, truyền `--mcp-config`, thêm graph guidance |
| `ai/bin/run-codex-review` | Sinh Codex MCP overrides theo task, thêm graph guidance |
| `ai/bin/bootstrap` | Báo CodeGraph CLI detected/not found và lệnh init tiếp theo |
| `ai/bin/self-check` | Validate mode, required binary và Claude MCP permission |
| `ai/config/claude/settings.json` | Cho phép MCP tools của các CodeGraph server động |
| `ai/config/claude/CLAUDE.md` | Quy tắc sử dụng CodeGraph cho implementer |
| `ai/config/codex/AGENTS.md` | Quy tắc sử dụng CodeGraph cho reviewer |
| `ai/agents/common.md` | Quy tắc chung ưu tiên graph và fallback |
| `README.md`, `ai/README.md`, `ai/bin/README.md` | Tài liệu tổng quan và command reference |
| `user_manual.md` | Hướng dẫn cài CLI, cấu hình mode, init/sync/status và lifecycle |
| `implement-draft.md` | Runbook/cheat sheet command thường dùng, gồm CodeGraph |

## 5. Luồng vận hành sau thay đổi

```text
developer tạo + đăng ký worktree
→ classify skills
→ prepare execution plan
→ ai task codegraph <ID> --init
→ prepare-context sync/health-check + lock graph status
→ run-claude nhận MCP server riêng từng repo
→ CodeGraph watcher cập nhật graph trong lúc implement
→ validation
→ run-codex-review nhận MCP server riêng từng repo
→ report
→ user acceptance
```

Luồng command khuyến nghị:

```bash
source .env.ai
./ai/bin/ai task classify-skills <TASK-ID> --apply
./ai/bin/ai task prepare-plan <TASK-ID> --force
./ai/bin/ai task codegraph <TASK-ID> --init
./ai/bin/ai task prepare-context <TASK-ID>
./ai/bin/ai task run <TASK-ID>
```

## 6. Kiểm thử đã chạy

```text
python3 -m unittest discover -s ai/tests -p 'test_*.py'
→ Ran 33 tests: OK

./ai/bin/ai self-check
→ Static self-check PASSED

./ai/bin/ai self-check --smoke
→ Skill gate fixtures PASSED
→ Smoke pipeline PASSED
→ Agent gate pipeline PASSED

git diff --check
→ PASSED
```

Kiểm tra tương thích CLI bổ sung:

- Codex CLI chấp nhận TOML overrides động cho `mcp_servers.<name>.command/args`.
- Claude CLI hiện tại có option `--mcp-config`.
- `manage-codegraph` ở optional mode trả JSON fallback đúng khi máy chưa có binary.

## 7. Trạng thái môi trường hiện tại

`codegraph` chưa được cài trên máy tại thời điểm triển khai. Vì vậy:

- Chưa chạy indexing thật trên các worktree dự án.
- Không tải/cài binary ngầm.
- Unit tests dùng mock để kiểm tra MCP config.
- Smoke pipeline xác nhận backward compatibility trong `optional` mode.

Cách cài được ghi trong `user_manual.md`:

```bash
# Standalone bundle trên macOS/Linux
curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh

# Hoặc qua npm
npm install -g @colbymchenry/codegraph
```

Sau khi cài:

```bash
source .env.ai
codegraph --version
./ai/bin/ai task codegraph <TASK-ID> --init
./ai/bin/ai task prepare-context <TASK-ID>
```

## 8. Phạm vi đề nghị Claude review

Claude cần review độc lập và **không sửa code trong lượt review này**. Tập trung vào:

1. `codegraph.py` có xử lý đúng `off`/`optional`/`required`, subprocess error, timeout,
   invalid JSON và index biến mất sau context lock hay không.
2. Lệnh `codegraph init/sync/status` và thứ tự arguments có khớp CLI chính thức không.
3. MCP config của Claude và Codex có đúng schema/escaping khi đường dẫn chứa khoảng trắng,
   repository name có dấu `-`, `_` hoặc ký tự đặc biệt hay không.
4. Việc dùng một MCP server cho mỗi worktree có phù hợp task đa repository không.
5. Có rủi ro command injection, path escape, đọc secret hoặc vượt Git/worktree policy không.
6. `prepare-context` có nên ghi toàn bộ CodeGraph status vào lock hay chỉ một health summary
   ổn định để tránh lock thay đổi không cần thiết.
7. Optional fallback có thực sự không làm Claude/Codex fail khi CLI hoặc index vắng mặt.
8. Required mode có fail đủ sớm và thông báo phục hồi rõ ràng không.
9. Test coverage còn thiếu case nào: init/sync failure, required mode, multi-repo, name
   collision, stale index, binary biến mất, path có khoảng trắng.
10. Documentation có thống nhất với behavior thực tế và không hướng dẫn sửa global MCP
    config ngoài ý muốn hay không.

## 9. Output mong muốn từ Claude

Trả về review theo severity:

- `blocker`: có thể gây mất an toàn, trỏ nhầm repository hoặc phá pipeline.
- `major`: behavior sai hoặc thiếu gate quan trọng.
- `minor`: robustness/test/documentation chưa đầy đủ.
- `note`: cải tiến không bắt buộc.

Mỗi finding cần có:

```text
severity
file:line
mô tả vấn đề
tình huống tái hiện
đề xuất sửa ngắn gọn
```

Nếu không có finding chặn, xác nhận rõ implementation có sẵn sàng để cài CodeGraph và
chạy integration test thật hay chưa.
