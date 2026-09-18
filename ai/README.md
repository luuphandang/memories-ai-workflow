# AI Control Plane

`ai/` là nguồn sự thật cho cách Claude, Codex và người dùng phối hợp. Source gốc nằm trong `apps/`; worktree nằm trong `worktrees/<JIRA-ID>/<repo-name>/`.

## Thành phần

| Thư mục | Mục đích |
|---|---|
| `agents/` | Vai trò và ranh giới của từng agent |
| `skills/` | Quy trình kỹ thuật tái sử dụng, reference và checker deterministic |
| `config/` | Cấu hình Claude Code và Codex |
| `shared/` | Policy, workflow, quality và glossary dùng chung |
| `repos/` | Kiến thức bền vững theo repository |
| `domains/example/` | Domain trung lập để sao chép cho tính năng thật |
| `tasks/` | Hồ sơ thực thi cố định theo Jira ID, gồm changes và acceptance |
| `indexes/` | Chỉ mục trạng thái được sinh tự động |
| `schemas/` | JSON Schema cho dữ liệu trao đổi/trạng thái |
| `templates/` | Mẫu task, acceptance và change cycle |
| `bin/` | Script điều phối và self-check |
| `runtime/` | Lock, log, session và cache cục bộ |
| `examples/` | Ví dụ epic → story → task và change cycle |

## Source of truth

1. Yêu cầu gốc: `tasks/<ID>/task.md`.
2. Yêu cầu thay đổi: `tasks/<ID>/changes/cycle-NNN/requirement-addendum.md`.
3. Context: `context.yaml`, `context.lock.json`.
4. Kế hoạch vertical slice: `execution-plan.json`.
5. Claude handoff: `implementation.json`.
6. Validation: `worktrees/<ID>/.ai/validation/`.
7. Codex review: `review.json`.
8. Nghiệm thu: `acceptance.yaml`.
9. Trạng thái: `state.yaml`.
10. Báo cáo: `final-report.md`.

Task không `completed` chỉ vì Codex pass; phải có user acceptance.

## Multi-agent coordination

Worktree writable có single-writer lease. Shared capability/resource phải được publish và
claim trước mutation; dependency phát hiện trong runtime được thêm vào execution plan bằng
versioned Plan Patch. Event JSONL là audit history, còn capability/dependency/resource graph
là projection có thể rebuild.

Task có dependency chưa ready có thể ở trạng thái `partially_blocked`: scheduler tiếp tục
slice độc lập và chỉ resume slice phụ thuộc khi capability/version đã sẵn sàng. Breaking
contract change làm confirmed consumer stale/revalidation-required theo impact graph.

Codex pass chỉ chứng minh review trên task snapshot. `ai integration validate` dựng clone tạm
trên exact target SHA, áp dụng task diff từ registered base và chạy combined validation; chỉ
manifest current có trạng thái `MERGE_READY`. Agent không tự merge/cherry-pick/rebase.

Skill lock dùng aggregate SHA-256 của `SKILL.md`, references, scripts và `agents/openai.yaml`; sửa bất kỳ file skill nào đều yêu cầu chạy lại `prepare-context`.

Chạy pipeline tự động bằng `./ai/bin/ai task run <ID>`. Command không tự accept và không thay
đổi requirement/max cycle. `review.max_fix_cycles` giới hạn số fix request thực tế; trường
`max_cycles` cũ vẫn được dùng làm fallback tương thích, không còn đếm delta/full review invocation.

## CodeGraph trong agent workflow

CodeGraph được nối động vào từng phiên Claude/Codex theo các worktree đã khóa trong
`context.lock.json`; mỗi repository có một MCP server `codegraph_<repo>`, tránh trỏ nhầm
graph khi task có nhiều repo. Cài CLI theo tài liệu CodeGraph, rồi chạy:

```bash
./ai/bin/ai task codegraph PROJ-1000 --init
./ai/bin/ai task prepare-context PROJ-1000
```

`AI_CODEGRAPH_MODE=optional` là mặc định: thiếu CLI/index thì agent fallback sang công cụ
khám phá thông thường. Dùng `required` ở môi trường muốn chặn prepare-context khi graph
không sẵn sàng, hoặc `off` để tắt. Trước khi khóa context, index hiện có được sync và
health-check; trạng thái được lưu tại `context.lock.json.codegraph`.

## Kiểm thử control plane

`./ai/bin/ai self-check --smoke` chạy pipeline mô phỏng trong workspace tạm, không gọi agent và không sửa task/worktree thật.
