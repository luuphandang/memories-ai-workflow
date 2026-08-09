# MEMORIES-0001: [TECH] Initialize Project Architecture and Folder Structure

## Jira

- Type: `epic`
- Parent: `-`
- Epic: `MEMORIES-0001`

## Goal

Khởi tạo kiến trúc nền tảng và cấu trúc thư mục chuẩn cho toàn bộ hệ thống MEMORIES, bao gồm:

* Backend NestJS.
* Website public Next.js.
* Website admin Next.js.
* Background worker sử dụng BullMQ.
* PostgreSQL, TypeORM, Redis và AWS S3.
* Realtime communication.
* Logging, monitoring và health check.
* Docker cho môi trường phát triển và triển khai.
* CI/CD cho kiểm tra chất lượng, build và phát hành theo phiên bản.

Kiến trúc cần đáp ứng các mục tiêu:

1. Hỗ trợ phát triển nhanh trong giai đoạn đầu dưới dạng modular monolith.
2. Phân tách rõ ràng giữa business domain và infrastructure.
3. Hạn chế coupling giữa các module nghiệp vụ.
4. Cho phép dùng lại các cấu hình và thành phần hạ tầng trong nhiều module.
5. Cho phép mở rộng thêm application process, worker hoặc integration mới mà không phải thay đổi lớn cấu trúc hiện tại.
6. Chuẩn bị sẵn ranh giới module để có thể tách thành microservice khi hệ thống phát triển đủ lớn.
7. Chuẩn hóa cách tổ chức source code, cấu hình, testing, migration, documentation và deployment cho toàn bộ đội ngũ phát triển.
8. Đảm bảo source code có thể được kiểm tra, build và triển khai nhất quán giữa local, development, staging và production.

Toàn bộ nội dung Goal/Background/Scope/Acceptance criteria/Out of scope gốc được lưu tại `/Users/cmc/Documents/Memories/initialize_project.md` (nguồn gốc yêu cầu, giữ nguyên không chỉnh sửa).

## Background

MEMORIES là nền tảng phục vụ ba nhóm nghiệp vụ chính: Tạo kỷ niệm (thiệp), Trao gửi kỷ niệm (quà tặng/thương mại), Lưu giữ kỷ niệm (bộ sưu tập/nhắc nhở). Hệ thống dùng BullMQ + Redis cho toàn bộ background job trong giai đoạn này; RabbitMQ/Kafka chưa được tích hợp. Chi tiết đầy đủ xem `initialize_project.md`.

## Current system

Giai đoạn khởi tạo, chưa có cấu trúc thống nhất cho backend và frontend. Chi tiết đầy đủ xem mục "Current system" trong `initialize_project.md`.

## Scope

Toàn bộ 26 mục Scope (Repository structure, Backend workspace, Backend business modules, Clean Architecture, Shared abstractions, Platform modules, Configuration management, BullMQ architecture, Database/TypeORM, Redis/cache, S3/media storage, Realtime, Authentication, Swagger, Observability, Health check, Frontend workspace, Public website, Admin website, Frontend technical foundation, Code quality, Testing foundation, Docker, CI pipeline, Release pipeline, Documentation) như mô tả trong `initialize_project.md`.

- [x] Khởi tạo cấu trúc thư mục/file skeleton đầy đủ cho `apps/backend` và `apps/frontend` (không `git init`, thực hiện trực tiếp trong `apps/` theo yêu cầu người dùng — ngoại lệ so với worktree policy mặc định).
- [ ] Test thay đổi liên quan.
- [ ] Tài liệu/knowledge update nếu phát sinh kiến thức bền vững.

## Acceptance criteria

Xem đầy đủ 62 acceptance criteria trong `initialize_project.md`, mục "Acceptance criteria".

## Out of scope

Xem mục "Out of scope" trong `initialize_project.md` (không triển khai đầy đủ business logic, không tích hợp RabbitMQ/Kafka, không tách microservice, không pentest, v.v.).

## Technical notes

- Module/file liên quan: `apps/backend/`, `apps/frontend/` (thư mục con trực tiếp trong workspace này, không phải Git worktree riêng).
- API/database/UI convention: theo mô tả trong `initialize_project.md` (Clean Architecture 4 layer, BullMQ job contract có version, TypeORM domain/persistence entity tách biệt, Tailwind/shadcn/Radix cho frontend).
- Luồng và edge case: xem mục 8 (BullMQ architecture) và mục 11 (S3 và media storage) của `initialize_project.md`.

## Scope amendments (approved by user, 2026-08-02)

These explicitly amend `initialize_project.md`'s original text for this task's effective
requirements — recorded here (the sole file `context.lock.json.requirements` currently locks,
`change_cycle: 0`, no separate addendum cycle open) per the user's direct instruction to update the
directive files rather than open a formal `ai/bin/request-change` cycle (which cannot run while
`state.yaml.status` is `changes_requested_by_codex`, a state that script does not accept).

1. **Branch convention (supersedes `initialize_project.md`'s main/develop git-flow model, §"Sử dụng
   branch convention"):** both `apps/backend` and `apps/frontend` repositories use a **single-branch
   model** — `master` is the sole long-lived branch. Neither repository has ever had a `main` or
   `develop` branch (confirmed via `git branch -a`), so `release.yml`/`deploy-production.yml`/CI
   trigger lists and the post-tag merge step must target `master` only, not `main`/`develop`.
   `docs/adr/0007-versioned-release-branch-deployment.md` and `docs/guides/{deployment,
   release-process}.md` (both repos) have been updated to reflect this and are the authoritative
   description of the branch/merge flow going forward.
2. **AC #56/#58/#59 (deployment infrastructure) — clarified, not waived:** the actual production
   infrastructure target (Kubernetes/ECS/VM/PaaS/...) was never chosen anywhere in
   `initialize_project.md`, so the steps that would apply a promoted image digest to a real running
   environment remain `TODO` placeholders in `release.yml`/`deploy-production.yml`/
   `rollback-production.yml` (both repos) — this is a pending infrastructure decision, out of this
   task's scope to make unilaterally. Everything around that gap that *can* be implemented in code
   has been (build/tag/push, digest tracking and cross-check between staging/production requests,
   mandatory smoke-test gating, release manifest, rollback reading the correct prior manifest,
   branch merge per amendment 1 above) and has been validated across 17 Codex review cycles.
   AC #57 (manual production approval) is met at the mechanism level (`environment: production` is
   correctly declared in the workflow); configuring actual required reviewers on that GitHub
   Environment is a one-time operational action outside what any workflow YAML in this repo can
   itself prove.

## Constraints

- Không quản lý worktree/branch (chưa có worktree cho task này — thao tác khởi tạo được thực hiện trực tiếp trong `apps/` theo chỉ định tường minh của người dùng, xem ghi chú ngoại lệ ở trên).
- Không commit hoặc push.
- Không đọc secret.
- Không tạo git repository mới trong `apps/backend` hoặc `apps/frontend` (chỉ tạo cấu trúc thư mục/file).
