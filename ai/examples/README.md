# Ví dụ Jira hierarchy và change cycle

```text
PROJ-1000 (epic)
└── PROJ-1001 (story)
    └── PROJ-1002 (task)
        ├── cycle-001: correction trước user acceptance
        └── cycle-002: requirement change sau completed
```

Mọi nội dung đều trung lập và chỉ dùng minh họa. Ví dụ không đại diện cho sản phẩm, domain hoặc source code thực tế.

- `cycle-001` minh họa người dùng phát hiện vấn đề sau Codex pass nhưng trước khi accept.
- `cycle-002` minh họa task đã completed được mở lại và tiếp tục trên worktree cũ.
- `baseline/` minh họa cách giữ lại kết quả của vòng trước.

Không chạy pipeline trực tiếp trong `ai/examples/`. Hãy dùng `./ai/bin/ai task create ...` để tạo hồ sơ thật trong `ai/tasks/`.
