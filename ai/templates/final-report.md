# Báo cáo {{TASK_ID}} — {{TITLE}}

## Kết quả kỹ thuật

- Trạng thái workflow: `{{STATUS}}`
- Implementation cycle: `{{IMPLEMENTATION_CYCLE}}`
- Change cycle hiện hành: `{{CHANGE_CYCLE}}`
- Claude implementation: `{{IMPLEMENTATION_STATUS}}`
- Codex verdict: `{{REVIEW_VERDICT}}`
- User acceptance: `{{USER_ACCEPTANCE}}`

{{ACCEPTANCE_NOTICE}}

## Yêu cầu hiệu lực

{{REQUIREMENT_DOCUMENTS}}

## Nội dung triển khai

{{IMPLEMENTATION_SUMMARY}}

{{CHANGED_FILES_SECTION}}

{{DIFF_STAT_SECTION}}

{{VALIDATION_SECTION}}

{{REVIEW_SECTION}}

{{KNOWLEDGE_SECTION}}

## Git

- Script/agent không commit hoặc push.
- Script/agent không đổi branch hoặc quản lý worktree.
- Task reopened tiếp tục dùng worktree đã đăng ký; script không tạo worktree mới.
- Developer chịu trách nhiệm kiểm tra diff và thực hiện Git flow của dự án.
