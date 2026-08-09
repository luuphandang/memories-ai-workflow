# Project AI Workspace

Bộ khung điều phối hai AI agent trong một dự án phần mềm:

- **Claude** triển khai yêu cầu trong Git worktree do developer tạo.
- **Codex** review độc lập ở chế độ chỉ đọc.
- **Người dùng** là cổng nghiệm thu cuối cùng.
- **Script** tạo hồ sơ Jira, khóa context, chạy validation, quản lý change cycle và sinh báo cáo.

## Hai marker bắt buộc

- `[BỔ SUNG THEO DỰ ÁN]`: chỉ điền sau khi đọc source/config/convention thực tế.
- `[BỔ SUNG THEO TÍNH NĂNG]`: chỉ điền từ Jira, thiết kế, API contract hoặc quyết định nghiệp vụ đã xác nhận.

## Lifecycle cốt lõi

```text
implement → validate → review → awaiting_user_acceptance
                            ├─ accept → completed
                            └─ correction → sửa trên cùng worktree
completed → requirement change → reopened → tiếp tục trên cùng worktree
```

## Bắt đầu nhanh

```bash
cd project
python3 -m venv .venv
source .venv/bin/activate
pip install -r ai/requirements.txt
cp .env.ai.example .env.ai
source .env.ai
./ai/bin/bootstrap
./ai/bin/ai self-check --smoke
./ai/bin/ai task create PROJ-1000 --type epic --title "Example epic"
```

- Hướng dẫn thao tác: [`user_manual.md`](user_manual.md)
- Chức năng từng file/folder: [`folder_structure_guide.md`](folder_structure_guide.md)

## An toàn

Agent không quản lý worktree/branch, không commit/push, không đọc secret. Knowledge base chỉ được áp dụng sau Codex pass **và** người dùng xác nhận task completed. Agent có timeout cấu hình được; dry-run validation không thể vượt qua cổng acceptance.
