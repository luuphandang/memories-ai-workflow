# Memories Backend Database Rules

- Database/ORM/version: PostgreSQL + TypeORM `^0.3.20`; `synchronize` tắt ở MỌI environment (kể cả test/e2e).
- Naming/index/constraint: tên cột/bảng snake_case (ví dụ `current_job_id`, `correlation_id`, `actor_id`); entity TypeORM đặt tại `libs/platform/database`-adjacent module hoặc `<module>/src/infrastructure/persistence/*.orm-entity.ts`.
- Migration generation/run/rollback: qua `typeorm-ts-node-commonjs` chạy trực tiếp trên `libs/platform/database/src/data-source.ts` — `npm run migration:generate`, `migration:create`, `migration:run`, `migration:revert`, `migration:show`; migration file đặt tại `libs/platform/database/src/migrations/`.
- Transaction/isolation: `UnitOfWork.withTransaction()` (`TypeOrmUnitOfWork`) mở 1 `QueryRunner`/transaction, join ngầm qua `TypeOrmQueryRunnerContext` (`AsyncLocalStorage`) — repository tự phát hiện transaction đang mở thay vì nhận tham số truyền tay; isolation level dùng mặc định của Postgres/TypeORM (chưa cấu hình riêng).
- Soft delete/audit/multi-tenant: chưa triển khai trong dự án hiện tại (chưa có cột `deleted_at`, audit trail, hay tenant scoping nào).
- Thay đổi schema cho tính năng: `[BỔ SUNG THEO TÍNH NĂNG]`

## Runtime metadata and concurrency

- Property optional/union có thể bị `reflect-metadata` suy thành `Object`; khai báo `type` tường minh cho TypeORM column và Swagger property.
- Nest monorepo build với webpack bundle dependency vào `dist/apps/<app>/main.js`; runtime discovery không được dựa vào glob `dist/libs/**/*.orm-entity.js`. Dùng `autoLoadEntities`/DI graph; CLI migration chạy từ source vẫn dùng data source tường minh.
- Ambient transaction context phải dùng `AsyncLocalStorage`, không dùng mutable field trên singleton.
- Transition có concurrent writer dùng conditional `UPDATE ... WHERE` và kiểm tra affected rows. Khi cần xóa nullable column, dùng `null`; `undefined` nghĩa là bỏ field khỏi `SET`.
- Bọc resource trong `try/finally` ngay sau acquisition thành công, trước bước initialization tiếp theo có thể lỗi.
