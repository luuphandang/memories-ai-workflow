# Memories Backend Source Map

| Khái niệm | Đường dẫn | Ghi chú |
|---|---|---|
| Bootstrap | `apps/{api,worker,realtime,scheduler,cli}/src/main.ts` | Mỗi app 1 entry point riêng, dùng chung `AppConfig`/`configureApp()` |
| Module nghiệp vụ | `libs/modules/media`, `libs/modules/identity-access` | `media` là module mẫu triển khai đầy đủ; `identity-access` mới chỉ là khung rỗng (chưa có use case/controller thật) |
| Controller/API | `libs/modules/media/src/presentation/http/media.controller.ts` | |
| Service/use case | `libs/modules/media/src/application/use-cases/*.use-case.ts` | |
| Entity/model | `libs/modules/media/src/domain/media-asset/media-asset.ts` (domain), `libs/modules/media/src/infrastructure/persistence/media-asset.orm-entity.ts` (TypeORM) | |
| Migration | `libs/platform/database/src/migrations/*.ts` | |
| Test | `libs/**/test/*.spec.ts` (unit), `apps/api/test/*.e2e-spec.ts` (e2e, chạy với Postgres/Redis/MinIO thật) | |
