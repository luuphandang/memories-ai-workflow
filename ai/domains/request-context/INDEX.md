# Request Context Domain Index

Domain quản lý execution-context runtime dùng chung của backend — request/correlation/actor
context và transaction context lan truyền qua async call chain — hiện dựa trên 3 instance
`AsyncLocalStorage` viết tay, đang migrate sang `nestjs-cls` (epic `MEMORIES-0006`).

- `overview.md`: phạm vi, thuật ngữ và các thành phần source liên quan.
- `data-flow.md`: luồng seed/đọc/ghi context qua middleware, guard, use case, background job, CLI.
- `decisions.md`: quyết định kiến trúc về việc gộp context store và migrate sang `nestjs-cls`.
