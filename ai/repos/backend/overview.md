# Memories Backend Overview

- Mục tiêu repository: monorepo backend NestJS cho dự án Memories, khởi tạo theo `initialize_project.md` (task MEMORIES-0001) — cung cấp bộ khung Clean Architecture dùng chung (`libs/platform/*`), 1 business module mẫu đầy đủ vòng đời (`libs/modules/media` — upload trực tiếp S3 rồi xử lý bất đồng bộ qua BullMQ) và 1 module rỗng minh hoạ boundary (`libs/modules/identity-access`), để các tính năng nghiệp vụ sau này build tiếp theo cùng convention.
- Runtime/framework/version: Node.js `>=20.0.0`; NestJS `^10.4.0` (`@nestjs/core`/`@nestjs/common`); TypeScript `^5.5.4` (strict mode, `exactOptionalPropertyTypes`).
- Package manager: npm (có `package-lock.json`, không dùng yarn/pnpm).
- Entry point và cách chạy local: 5 ứng dụng độc lập trong `apps/` — `api`, `worker`, `realtime`, `scheduler`, `cli` — mỗi app build/chạy qua Nest CLI: `npm run start:<app>` (watch mode qua `nest start`) hoặc `npm run build:<app>` rồi `node dist/apps/<app>/main.js`; hạ tầng phụ thuộc chạy qua `docker/docker-compose.yml`.
- Phụ thuộc hạ tầng: PostgreSQL (TypeORM), Redis (cache client + BullMQ + Socket.IO realtime pub/sub — có thể tách connection riêng qua config), object storage tương thích S3 (MinIO ở local/dev, S3 thật ở production).
- Chủ sở hữu/maintainer: chưa xác định cụ thể trong dự án hiện tại.
