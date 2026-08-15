# Hướng dẫn chức năng từng file/folder

Tài liệu này mô tả toàn bộ cấu trúc được đóng gói. Các đường dẫn dưới đây tính từ thư mục `project/`.

## 1. Nguyên tắc đọc cấu trúc

- `apps/` giữ repo gốc; `worktrees/` giữ nơi code thật được thay đổi.
- `ai/tasks/<ID>/` là source of truth của một Jira item.
- `changes/cycle-NNN/` giữ lịch sử yêu cầu mới mà không sửa mất yêu cầu cũ.
- `baseline/` chỉ là lịch sử; agent phải dùng output của cycle hiện hành.
- `domains/example/` là mẫu trung lập, cần sao chép/đổi tên cho tính năng thật.

## 2. Thư mục

| Đường dẫn | Chức năng |
|---|---|
| `./` | Thư mục gốc của workspace, chứa source gốc, worktree, AI control plane và tài liệu sử dụng. |
| `ai/` | AI control plane và knowledge base dùng chung. |
| `apps/` | Chứa các Git repository gốc; AI không chỉnh code trực tiếp tại đây. |
| `worktrees/` | Chứa task workspace và các Git worktree do developer tạo. |
| `ai/agents/` | Mô tả vai trò, trách nhiệm và ranh giới của Claude/Codex. |
| `ai/bin/` | CLI, script điều phối và self-check. |
| `ai/config/` | Cấu hình CLI và policy cục bộ cho các agent. |
| `ai/domains/` | Knowledge nghiệp vụ theo tính năng/domain. |
| `ai/examples/` | Dữ liệu minh họa trung lập. |
| `ai/indexes/` | Chỉ mục trạng thái tự động sinh từ state.yaml. |
| `ai/integrations/` | Adapter cho hệ thống ngoài (hiện tại: TencentDB Agent Memory); không phải source of truth. |
| `ai/repos/` | Knowledge template theo từng repository. |
| `ai/runtime/` | Dữ liệu runtime cục bộ không phải source of truth. |
| `ai/schemas/` | JSON Schema xác thực structured output và metadata. |
| `ai/shared/` | Policy, workflow, quality checklist và glossary dùng chung. |
| `ai/tasks/` | Hồ sơ task thực tế theo Jira ID; đường dẫn task không thay đổi theo trạng thái. |
| `ai/templates/` | Mẫu dùng khi tạo task, report đa ngôn ngữ, acceptance và change cycle. |
| `ai/bin/lib/` | Thư viện Python dùng chung cho script. |
| `ai/bin/lib/memory/` | Package `MemoryProvider` trung lập vendor và adapter TencentDB. |
| `ai/integrations/memory/` | Contract vendor-neutral và policy recall/publish cho Claude/Codex. |
| `ai/integrations/memory/policies/` | Danh sách allow/forbid cho recall và publish. |
| `ai/integrations/tencentdb-memory/` | Cấu hình, upstream notes và prompt fragment cho adapter TencentDB. |
| `ai/integrations/tencentdb-memory/local-index/` | Sổ supersession cục bộ (upstream không có API deprecate asset). |
| `ai/integrations/tencentdb-memory/prompts/` | Đoạn hướng dẫn ngắn chèn vào prompt khi memory sẵn sàng. |
| `ai/config/claude/` | Cấu hình Claude Code. |
| `ai/config/codex/` | Cấu hình Codex và profile review read-only. |
| `ai/domains/example/` | Domain mẫu trung lập duy nhất để sao chép cho tính năng thật. |
| `ai/examples/tasks/` | Ví dụ hồ sơ Jira epic → story → task. |
| `ai/repos/backend/` | Knowledge template dành cho repository `backend`. |
| `ai/repos/frontend/` | Knowledge template dành cho repository `frontend`. |
| `ai/runtime/cache/` | Cache cục bộ. |
| `ai/runtime/locks/` | Lock tránh chạy trùng. |
| `ai/runtime/logs/` | Log điều phối. |
| `ai/runtime/sessions/` | Metadata phiên agent. |
| `ai/shared/glossary/` | Thuật ngữ chuẩn của workspace. |
| `ai/shared/policies/` | Ranh giới an toàn, Git, worktree và quyền agent. |
| `ai/shared/quality/` | Definition of Done, severity và checklist review. |
| `ai/shared/workflows/` | Quy trình Jira, triển khai, review, acceptance, change cycle và knowledge update. |
| `ai/templates/change/` | Mẫu hồ sơ cho một correction/requirement-change cycle. |
| `ai/config/claude/hooks/` | Hook chặn lệnh phá hoại. |
| `ai/examples/tasks/PROJ-1000/` | Hồ sơ ví dụ của Jira item `PROJ-1000`. |
| `ai/examples/tasks/PROJ-1001/` | Hồ sơ ví dụ của Jira item `PROJ-1001`. |
| `ai/examples/tasks/PROJ-1002/` | Hồ sơ ví dụ của Jira item `PROJ-1002`. |
| `ai/examples/tasks/PROJ-1000/changes/` | Chứa lịch sử change cycle của task. |
| `ai/examples/tasks/PROJ-1001/changes/` | Chứa lịch sử change cycle của task. |
| `ai/examples/tasks/PROJ-1002/changes/` | Chứa lịch sử change cycle của task. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/` | Một vòng correction hoặc requirement change độc lập. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/` | Một vòng correction hoặc requirement change độc lập. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/attachments/` | Bằng chứng hoặc liên kết tham chiếu cho change cycle. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/` | Snapshot kết quả của vòng trước khi tạo change cycle. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/attachments/` | Bằng chứng hoặc liên kết tham chiếu cho change cycle. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/` | Snapshot kết quả của vòng trước khi tạo change cycle. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/validation/` | Snapshot validation của baseline. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/validation/` | Snapshot validation của baseline. |

## 3. File

| Đường dẫn | Chức năng |
|---|---|
| `.env.ai.example` | Mẫu biến môi trường để định vị workspace và cấu hình Claude/Codex. |
| `.gitignore` | Loại trừ repository thật, worktree, runtime, secret và file tạm khỏi AI control-plane repository. |
| `README.md` | Giới thiệu nhanh, lifecycle cốt lõi và liên kết tài liệu. |
| `ai/README.md` | Tổng quan AI control plane và thứ tự source of truth. |
| `ai/agents/claude-implementer.md` | Vai trò, trình tự và giới hạn của Claude implementer. |
| `ai/agents/codex-reviewer.md` | Vai trò, checklist và output contract của Codex reviewer. |
| `ai/agents/common.md` | Quy tắc chung và thứ tự ưu tiên yêu cầu cho cả hai agent. |
| `ai/bin/README.md` | Danh mục và chức năng các script. |
| `ai/bin/accept-task` | Ghi acceptance và chuyển task sang completed. |
| `ai/bin/ai` | CLI router cho các subcommand. |
| `ai/bin/bootstrap` | Tạo symlink cấu hình local cho Claude/Codex. |
| `ai/bin/self-check` | Kiểm tra JSON/schema/config và tùy chọn chạy smoke pipeline cô lập. |
| `ai/bin/create-task` | Tạo hồ sơ epic/story/task, acceptance và changes directory. |
| `ai/bin/finalize-task` | Sinh report; technical pass chỉ chuyển sang awaiting_user_acceptance. |
| `ai/bin/lib/__init__.py` | Đánh dấu thư mục lib là Python package. |
| `ai/bin/lib/ai_common.py` | Hàm dùng chung: I/O, path safety, Git, schema, cycle và archive. |
| `ai/bin/lib/memory/__init__.py` | Orchestration: config precedence, recall/publish/sync cho task, sổ supersession. |
| `ai/bin/lib/memory/models.py` | Dataclass `MemoryQuery`/`MemoryItem`/`MemorySnapshot`/`MemoryPublishEntry`/`MemoryHealth`. |
| `ai/bin/lib/memory/provider.py` | ABC `MemoryProvider` và factory `get_provider()` theo `AI_MEMORY_PROVIDER`. |
| `ai/bin/lib/memory/tencentdb.py` | Adapter HTTP (urllib) cho TencentDB MemoryCore/MemoryKnowledge. |
| `ai/bin/lib/memory/fake.py` | Provider giả offline dùng cho `self-check --smoke` và unit test. |
| `ai/bin/memory-health` | In trạng thái provider/service/capability; exit 1 nếu không sẵn sàng. |
| `ai/bin/memory-recall` | Chạy recall cho một task, ghi `memory/recall.json` và `recall.md`. |
| `ai/bin/memory-publish` | Publish knowledge-updates.json đã approved thành persistent memory (yêu cầu completed+accepted). |
| `ai/bin/memory-sync` | Đồng bộ CodeGraph cho `apps/<repo>` (không bao giờ nhận worktree path). |
| `ai/bin/prepare-context` | Xác minh requirement/knowledge/worktree, chạy memory recall và khóa context. |
| `ai/bin/rebuild-indexes` | Sinh lại các file index theo state.yaml. |
| `ai/bin/register-worktree` | Đăng ký worktree do developer tạo và lưu branch ban đầu. |
| `ai/bin/request-change` | Lưu baseline và tạo correction/requirement-change cycle trên worktree cũ. |
| `ai/bin/request-fixes` | Chuyển finding thuộc `review.fail_on`, acceptance criterion lỗi và validation thiếu thành fix request. |
| `ai/bin/run-claude` | Sinh prompt và chạy Claude cho cycle hiện hành. |
| `ai/bin/run-codex-review` | Chạy Codex read-only và ghi structured review. |
| `ai/bin/update-knowledge` | Preview hoặc áp dụng knowledge đã duyệt sau completed. |
| `ai/bin/validate` | Chạy lint/typecheck/test/build và ghi cycle identity. |
| `ai/config/claude/CLAUDE.md` | Instruction root được Claude Code nạp. |
| `ai/config/claude/hooks/block-destructive.sh` | Hook chặn command Git/file-system phá hoại. |
| `ai/config/claude/settings.json` | Allow/deny permission cho Claude Code. |
| `ai/config/codex/AGENTS.md` | Instruction root cho Codex review. |
| `ai/config/codex/config.toml` | Cấu hình Codex mặc định. |
| `ai/config/codex/review.config.toml` | Profile Codex review read-only. |
| `ai/domains/example/INDEX.md` | Chỉ mục domain mẫu và hướng dẫn sao chép. |
| `ai/domains/example/api-contract.md` | Mẫu request/response/error contract. |
| `ai/domains/example/business-rules.md` | Mẫu bảng quy tắc nghiệp vụ và edge case. |
| `ai/domains/example/data-flow.md` | Mẫu luồng dữ liệu và điểm cần xác minh. |
| `ai/domains/example/decisions.md` | Mẫu ghi quyết định và hệ quả. |
| `ai/domains/example/overview.md` | Mẫu mô tả mục tiêu, phạm vi, source liên quan và thuật ngữ. |
| `ai/domains/example/validation-rules.md` | Mẫu quy tắc validation. |
| `ai/domains/example/workflow.md` | Mẫu state/workflow của một tính năng. |
| `ai/examples/README.md` | Giải thích hierarchy và hai change cycle mẫu. |
| `ai/examples/tasks/PROJ-1000/acceptance.yaml` | Bản ghi user acceptance mẫu. |
| `ai/examples/tasks/PROJ-1000/context.lock.json` | Context manifest mẫu. |
| `ai/examples/tasks/PROJ-1000/context.yaml` | Context selection của item ví dụ. |
| `ai/examples/tasks/PROJ-1000/final-report.md` | Báo cáo hoặc baseline report mẫu. |
| `ai/examples/tasks/PROJ-1000/implementation.json` | Claude handoff hoặc baseline handoff mẫu. |
| `ai/examples/tasks/PROJ-1000/knowledge-updates.json` | Knowledge proposal mẫu. |
| `ai/examples/tasks/PROJ-1000/review.json` | Codex review hoặc baseline review mẫu. |
| `ai/examples/tasks/PROJ-1000/state.yaml` | Trạng thái/cycle/acceptance mẫu. |
| `ai/examples/tasks/PROJ-1000/task.md` | Yêu cầu người đọc của item ví dụ. |
| `ai/examples/tasks/PROJ-1000/task.yaml` | Metadata Jira/policy của item ví dụ. |
| `ai/examples/tasks/PROJ-1001/acceptance.yaml` | Bản ghi user acceptance mẫu. |
| `ai/examples/tasks/PROJ-1001/context.lock.json` | Context manifest mẫu. |
| `ai/examples/tasks/PROJ-1001/context.yaml` | Context selection của item ví dụ. |
| `ai/examples/tasks/PROJ-1001/final-report.md` | Báo cáo hoặc baseline report mẫu. |
| `ai/examples/tasks/PROJ-1001/implementation.json` | Claude handoff hoặc baseline handoff mẫu. |
| `ai/examples/tasks/PROJ-1001/knowledge-updates.json` | Knowledge proposal mẫu. |
| `ai/examples/tasks/PROJ-1001/review.json` | Codex review hoặc baseline review mẫu. |
| `ai/examples/tasks/PROJ-1001/state.yaml` | Trạng thái/cycle/acceptance mẫu. |
| `ai/examples/tasks/PROJ-1001/task.md` | Yêu cầu người đọc của item ví dụ. |
| `ai/examples/tasks/PROJ-1001/task.yaml` | Metadata Jira/policy của item ví dụ. |
| `ai/examples/tasks/PROJ-1002/acceptance.yaml` | Bản ghi user acceptance mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/attachments/README.md` | Mô tả attachment của cycle mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/acceptance.yaml` | Bản ghi user acceptance mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/final-report.md` | Báo cáo hoặc baseline report mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/implementation.json` | Claude handoff hoặc baseline handoff mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/review.json` | Codex review hoặc baseline review mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/baseline/validation/summary.json` | Validation summary baseline mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/metadata.yaml` | Metadata change cycle mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/requirement-addendum.md` | Yêu cầu bổ sung mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-001/user-request.md` | Phản hồi người dùng mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/attachments/README.md` | Mô tả attachment của cycle mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/acceptance.yaml` | Bản ghi user acceptance mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/final-report.md` | Báo cáo hoặc baseline report mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/implementation.json` | Claude handoff hoặc baseline handoff mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/review.json` | Codex review hoặc baseline review mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/baseline/validation/summary.json` | Validation summary baseline mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/metadata.yaml` | Metadata change cycle mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/requirement-addendum.md` | Yêu cầu bổ sung mẫu. |
| `ai/examples/tasks/PROJ-1002/changes/cycle-002/user-request.md` | Phản hồi người dùng mẫu. |
| `ai/examples/tasks/PROJ-1002/context.lock.json` | Context manifest mẫu. |
| `ai/examples/tasks/PROJ-1002/context.yaml` | Context selection của item ví dụ. |
| `ai/examples/tasks/PROJ-1002/final-report.md` | Báo cáo hoặc baseline report mẫu. |
| `ai/examples/tasks/PROJ-1002/implementation.json` | Claude handoff hoặc baseline handoff mẫu. |
| `ai/examples/tasks/PROJ-1002/knowledge-updates.json` | Knowledge proposal mẫu. |
| `ai/examples/tasks/PROJ-1002/review.json` | Codex review hoặc baseline review mẫu. |
| `ai/examples/tasks/PROJ-1002/state.yaml` | Trạng thái/cycle/acceptance mẫu. |
| `ai/examples/tasks/PROJ-1002/task.md` | Yêu cầu người đọc của item ví dụ. |
| `ai/examples/tasks/PROJ-1002/task.yaml` | Metadata Jira/policy của item ví dụ. |
| `ai/indexes/backlog.md` | Danh sách task backlog được sinh tự động. |
| `ai/indexes/completed.md` | Danh sách task đã được người dùng accept. |
| `ai/indexes/failed.md` | Danh sách task needs_input/blocked/failed. |
| `ai/indexes/in-progress.md` | Danh sách task đang triển khai hoặc reopened. |
| `ai/indexes/review.md` | Danh sách task đang review/chờ acceptance. |
| `ai/integrations/README.md` | Giới thiệu adapter layer và design invariant (Claude/Codex → orchestrator → MemoryProvider → adapter). |
| `ai/integrations/memory/README.md` | Tổng quan memory vendor-neutral, thứ tự ưu tiên canonical vs memory. |
| `ai/integrations/memory/provider-contract.md` | Contract `MemoryProvider`, data model, precedence enabled/required. |
| `ai/integrations/memory/policies/recall-policy.md` | Danh sách nội dung Claude/Codex được/không được nhận từ recall. |
| `ai/integrations/memory/policies/publish-policy.md` | Nguồn nội dung được publish, category, canonical luôn thắng. |
| `ai/integrations/tencentdb-memory/README.md` | Cách chạy service cục bộ và cấu hình adapter. |
| `ai/integrations/tencentdb-memory/upstream-notes.md` | Ghi nhận API/SDK/giới hạn thực tế đọc từ source TencentDB. |
| `ai/integrations/tencentdb-memory/config.yaml` | Provider mặc định: enabled/required/timeout/recall size/fallback. |
| `ai/integrations/tencentdb-memory/asset-mapping.yaml` | Mapping path cục bộ → asset_type TencentDB. |
| `ai/integrations/tencentdb-memory/recall-policy.yaml` | Bản máy đọc của recall-policy.md. |
| `ai/integrations/tencentdb-memory/publish-policy.yaml` | Bảng fallback category theo tên file cho entry cũ chưa có `category`. |
| `ai/integrations/tencentdb-memory/local-index/superseded-assets.json` | Sổ supersession cục bộ theo task/target. |
| `ai/integrations/tencentdb-memory/prompts/recall.md` | Đoạn hướng dẫn recall chèn vào prompt agent. |
| `ai/integrations/tencentdb-memory/prompts/publish.md` | Tóm tắt publish cho operator (không phải prompt agent). |
| `ai/repos/backend/INDEX.md` | Chỉ mục knowledge của repository. |
| `ai/repos/backend/api-rules.md` | Quy tắc API của backend. |
| `ai/repos/backend/architecture.md` | Kiến trúc, module boundary và data flow. |
| `ai/repos/backend/commands.yaml` | Command install/lint/typecheck/test/build deterministic. |
| `ai/repos/backend/conventions.md` | Coding convention và pattern của repository. |
| `ai/repos/backend/database-rules.md` | Quy tắc database/migration/transaction. |
| `ai/repos/backend/known-issues.md` | Known issue có bằng chứng và workaround. |
| `ai/repos/backend/overview.md` | Mục tiêu, runtime, package manager và cách chạy repository. |
| `ai/repos/backend/source-map.md` | Bản đồ vị trí source quan trọng. |
| `ai/repos/backend/testing.md` | Chiến lược, framework và quy tắc test. |
| `ai/repos/frontend/INDEX.md` | Chỉ mục knowledge của repository. |
| `ai/repos/frontend/api-client-rules.md` | Quy tắc API client, error mapping và caching. |
| `ai/repos/frontend/architecture.md` | Kiến trúc, module boundary và data flow. |
| `ai/repos/frontend/commands.yaml` | Command install/lint/typecheck/test/build deterministic. |
| `ai/repos/frontend/conventions.md` | Coding convention và pattern của repository. |
| `ai/repos/frontend/known-issues.md` | Known issue có bằng chứng và workaround. |
| `ai/repos/frontend/overview.md` | Mục tiêu, runtime, package manager và cách chạy repository. |
| `ai/repos/frontend/source-map.md` | Bản đồ vị trí source quan trọng. |
| `ai/repos/frontend/testing.md` | Chiến lược, framework và quy tắc test. |
| `ai/repos/frontend/ui-rules.md` | Quy tắc UI/component/accessibility. |
| `ai/requirements.txt` | Dependency Python cho script, ví dụ PyYAML và jsonschema. |
| `ai/runtime/cache/.gitkeep` | Giữ thư mục cache rỗng. |
| `ai/runtime/locks/.gitkeep` | Giữ thư mục locks rỗng. |
| `ai/runtime/logs/.gitkeep` | Giữ thư mục logs rỗng. |
| `ai/runtime/sessions/.gitkeep` | Giữ thư mục sessions rỗng. |
| `ai/schemas/change.schema.json` | Schema metadata của change cycle. |
| `ai/schemas/context.schema.json` | Schema cho context.yaml. |
| `ai/schemas/implementation.schema.json` | Schema handoff của Claude, gắn cycle identity. |
| `ai/schemas/knowledge-update.schema.json` | Schema proposal cập nhật knowledge. |
| `ai/schemas/review.schema.json` | Schema review của Codex, gắn cycle identity. |
| `ai/schemas/state.schema.json` | Schema trạng thái, cycle và user acceptance. |
| `ai/schemas/task.schema.json` | Schema cho task.yaml. |
| `ai/schemas/user-acceptance.schema.json` | Schema acceptance.yaml. |
| `ai/shared/INDEX.md` | Chỉ mục ngắn dẫn agent tới tài liệu shared cần thiết. |
| `ai/shared/glossary/terms.md` | Định nghĩa technical pass, acceptance, change cycle, baseline và thuật ngữ khác. |
| `ai/shared/policies/agent-boundaries.md` | Phân quyền giữa Claude, Codex, script và người dùng. |
| `ai/shared/policies/git-policy.md` | Các thao tác Git được phép và bị cấm. |
| `ai/shared/policies/security.md` | Policy về secret, dữ liệu nhạy cảm, dependency và command. |
| `ai/shared/policies/worktree-policy.md` | Quy tắc tạo/đăng ký/tái sử dụng worktree, nhất là task reopened. |
| `ai/shared/quality/definition-of-done.md` | Tiêu chí hoàn thành gồm user acceptance. |
| `ai/shared/quality/review-checklist.md` | Checklist review requirement/code/validation/handoff. |
| `ai/shared/quality/severity-levels.md` | Định nghĩa blocker, major, minor và note. |
| `ai/shared/workflows/code-review.md` | Các bước Codex review và nguyên tắc không dùng kết quả cycle cũ. |
| `ai/shared/workflows/implementation.md` | Các bước Claude thực hiện một implementation/change cycle. |
| `ai/shared/workflows/jira-hierarchy.md` | Quy tắc epic → story → task. |
| `ai/shared/workflows/knowledge-update.md` | Quy tắc đề xuất/duyệt/áp dụng knowledge lâu dài. |
| `ai/shared/workflows/requirement-change.md` | Hai luồng correction trước accept và change sau completed. |
| `ai/shared/workflows/task-lifecycle.md` | State machine của task và điều kiện chuyển trạng thái. |
| `ai/shared/workflows/user-acceptance.md` | Cổng nghiệm thu người dùng sau technical pass. |
| `ai/tasks/.gitkeep` | Giữ thư mục tasks khi chưa có task thật. |
| `ai/templates/acceptance.yaml` | Mẫu ghi nhận người dùng xác nhận. |
| `ai/templates/change/attachments-README.md` | Mẫu quy tắc lưu attachment. |
| `ai/templates/change/metadata.yaml` | Mẫu loại change, nguồn trạng thái và worktree policy. |
| `ai/templates/change/requirement-addendum.md` | Mẫu yêu cầu chính thức bổ sung/thay thế. |
| `ai/templates/change/user-request.md` | Mẫu phản hồi/bằng chứng do người dùng cung cấp. |
| `ai/templates/context.lock.json` | Mẫu manifest hash, requirement order và repository state. |
| `ai/templates/context.yaml` | Mẫu chọn knowledge và domain cho task. |
| `ai/templates/final-report.md` | Mẫu báo cáo tiếng Việt với section bật/tắt theo `report.*`. |
| `ai/templates/final-report.en.md` | Mẫu báo cáo tiếng Anh. |
| `ai/tests/smoke_pipeline.py` | Smoke test end-to-end trong workspace tạm, không gọi Claude/Codex. |
| `ai/tests/test_memory.py` | Unit test cho recall/publish/sync, mirror `test_codegraph.py`. |
| `ai/tests/memory_smoke_pipeline.py` | Smoke test memory end-to-end với `AI_MEMORY_PROVIDER=fake`, chạy trong `self-check --smoke`. |
| `ai/templates/implementation.json` | Mẫu handoff Claude. |
| `ai/templates/knowledge-updates.json` | Mẫu danh sách knowledge proposal. |
| `ai/templates/review.json` | Mẫu output Codex. |
| `ai/templates/state.yaml` | Mẫu state có implementation/review/change cycle và acceptance. |
| `ai/templates/task.md` | Mẫu yêu cầu dạng người đọc. |
| `ai/templates/task.yaml` | Mẫu metadata Jira/policy dạng máy đọc. |
| `apps/.gitkeep` | Giữ thư mục apps trong Git khi chưa clone repo. |
| `folder_structure_guide.md` | Tài liệu này; giải thích chức năng của từng file/folder. |
| `user_manual.md` | Hướng dẫn vận hành đầy đủ, gồm hai quy trình thay đổi yêu cầu. |
| `worktrees/.gitkeep` | Giữ thư mục worktrees trong Git khi chưa tạo worktree. |

## 4. Cấu trúc task thực tế sau khi có change cycle

```text
ai/tasks/<TASK-ID>/
├── task.yaml
├── task.md
├── context.yaml
├── context.lock.json
├── state.yaml
├── acceptance.yaml
├── implementation.json
├── review.json
├── knowledge-updates.json
├── final-report.md
├── memory/                      (chỉ có khi AI_MEMORY_ENABLED=true; ghi bởi prepare-context)
│   ├── recall.json
│   └── recall.md
└── changes/
    └── cycle-NNN/
        ├── metadata.yaml
        ├── user-request.md
        ├── requirement-addendum.md
        ├── attachments/README.md
        └── baseline/
            └── memory/          (snapshot của cycle trước, lưu bởi request-change)
```

Xem quy trình thao tác và câu lệnh trong `user_manual.md`.
