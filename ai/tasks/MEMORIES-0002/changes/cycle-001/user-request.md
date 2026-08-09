# MEMORIES-0002 — Yêu cầu thay đổi cycle 1

## Loại thay đổi

`correction`

## Người dùng phát hiện/yêu cầu

Người dùng yêu cầu loại bỏ hoàn toàn các yêu cầu về frontend ra khỏi phạm vi epic MEMORIES-0002. Epic này chỉ còn là backend-only.

## Kết quả hiện tại

`task.md` mục 18 "Frontend integration" (checklist form login public/admin, payload theo portal, quy tắc lưu token trên client, cập nhật API client...) vẫn nằm trong scope. AC36 ("API client frontend được cập nhật hoặc regenerate") và AC39 ("Mock authentication được xóa khỏi backend và frontend") vẫn yêu cầu phần frontend. `execution-plan.json` có slice `frontend-integration` tương ứng. `task.yaml` chỉ đăng ký worktree `backend`, không có worktree `frontend` — nên trước đây implementation cycle 1 đã tự diễn giải (sai) là frontend "ngoài phạm vi" dù task.md không liệt kê nó trong mục "Out of scope", gây mâu thuẫn giữa self-report và review.

## Kết quả mong muốn

MEMORIES-0002 chỉ còn yêu cầu backend. Mục 18 "Frontend integration" không còn là một phần scope phải triển khai/verify trong epic này. AC36 và AC39 được diễn giải lại chỉ áp dụng cho backend (API/Swagger cho AC36 nếu còn ý nghĩa backend-only; xóa mock authentication ở backend cho AC39). Slice `frontend-integration` trong execution plan không còn được yêu cầu.

## Lý do thay đổi

Quyết định nghiệp vụ của người dùng: tách frontend ra khỏi epic này (có thể xử lý ở epic/task khác sau).

## Bằng chứng

- Screenshot/video/log/tài liệu: không áp dụng — đây là quyết định phạm vi trực tiếp từ người dùng trong phiên làm việc.
- Cách tái hiện: không áp dụng.

## Mức độ ảnh hưởng

- `task.md`: mục 18 và các dòng liên quan tới frontend trong AC36/AC39 không còn bắt buộc (xem `requirement-addendum.md`).
- `execution-plan.json`: cần loại slice `frontend-integration` khi `prepare-plan` chạy lại.
- `task.yaml`: không cần đăng ký worktree frontend.
- Không ảnh hưởng tới các AC/slice backend khác đã được review/fix ở implementation cycle 1.
