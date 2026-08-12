---
name: create-backend-migration
description: Create TypeORM migrations for the Memories NestJS backend exclusively through its npm migration scripts. Use whenever a backend task creates or generates a migration, changes the database schema, or requires a new file under libs/platform/database/src/migrations. Never create or write a migration file directly.
---

# Create a backend migration

1. Work from the backend repository root containing `package.json`.
2. Finish the entity/schema-model changes that TypeORM must compare before generating a migration.
3. Choose one command:
   - Generate schema SQL from entity changes: `npm run migration:generate -- <PascalCaseName>`.
   - Create an intentionally empty migration for data backfills or SQL TypeORM cannot infer: `npm run migration:create -- <PascalCaseName>`.
4. Never create, copy, rename, or hand-write a new migration file before running the npm command. The npm script owns the timestamp, filename, and output directory.
5. After the command creates the file, inspect and edit that generated file only as needed for correctness. Keep both `up` and `down` paths safe and complete.
6. After any migration content changes, run a fresh isolated lifecycle: apply every migration to an empty database, seed, run database tests, revert every migration, reapply, reseed, and rerun the tests.
7. Record current source/migration hashes and commands with `$validate-evidence-provenance`; never cite lifecycle results from before the latest migration edit.
8. Run `npm run migration:show` and the task's configured database validation.
9. Record the exact npm command and generated path in implementation evidence.

Pass only the migration name, not a filesystem path. Use PascalCase letters and digits, beginning with an uppercase letter. If the npm command fails, fix its reported cause and rerun it; do not bypass the script by creating the file yourself.
