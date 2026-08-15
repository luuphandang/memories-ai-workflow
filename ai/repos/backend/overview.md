# Memories Backend Overview

- Mục tiêu repository: monorepo backend NestJS cho dự án Memories, được khởi tạo trong task `MEMORIES-0001` theo kiến trúc modular monolith và Clean Architecture. Repository cung cấp các process độc lập `api`, `worker`, `realtime`, `scheduler`, `cli`; lớp hạ tầng dùng chung trong `libs/platform/*`; các bounded context nghiệp vụ trong `libs/modules/*`; luồng media mẫu hoàn chỉnh từ upload trực tiếp lên S3-compatible storage đến xử lý bất đồng bộ bằng BullMQ. Business module chỉ phụ thuộc abstraction/application port, không phụ thuộc trực tiếp BullMQ, TypeORM, Redis, S3 hay framework adapter, để các tính năng sau có thể mở rộng theo cùng module boundary.
- Runtime/framework/version: Node.js `>=20.0.0`; NestJS `^10.4.0` (`@nestjs/core`/`@nestjs/common`); TypeScript `^5.5.4` (strict mode, `exactOptionalPropertyTypes`).
- Package manager: npm (có `package-lock.json`, không dùng yarn/pnpm).
- Entry point và cách chạy local: 5 ứng dụng độc lập trong `apps/` — `api`, `worker`, `realtime`, `scheduler`, `cli` — mỗi app chạy development qua `npm run dev:<app>` (`api`, `worker`, `realtime`, `scheduler` dùng watch mode qua `nest start`; `cli` chạy bản build trong `dist`) hoặc build qua `npm run build:<app>`; hạ tầng phụ thuộc chạy qua `docker/docker-compose.yml`.
- Phụ thuộc hạ tầng: PostgreSQL (TypeORM), Redis (cache client + BullMQ + Socket.IO realtime pub/sub — có thể tách connection riêng qua config), object storage tương thích S3 (MinIO ở local/dev, S3 thật ở production).
- Chủ sở hữu/maintainer: chưa xác định cụ thể trong dự án hiện tại.
