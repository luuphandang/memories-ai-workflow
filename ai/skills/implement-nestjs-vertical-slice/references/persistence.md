# TypeORM persistence checks

- When a business module persists multiple entities, group persistence files by domain concept/aggregate instead of keeping a flat directory or grouping by technical role. Use a kebab-case directory per concept and colocate its ORM entity, mapper (when needed), and TypeORM repository; association concepts such as `account-role` and `role-permission` get their own directories. For example:

  ```text
  persistence/
  ├── account/
  │   ├── account.orm-entity.ts
  │   ├── account.mapper.ts
  │   └── typeorm-account.repository.ts
  ├── auth-identity/
  │   ├── auth-identity.orm-entity.ts
  │   ├── auth-identity.mapper.ts
  │   └── typeorm-auth-identity.repository.ts
  ├── refresh-session/
  │   ├── refresh-session.orm-entity.ts
  │   ├── refresh-session.mapper.ts
  │   └── typeorm-refresh-session.repository.ts
  ├── role/
  │   ├── role.orm-entity.ts
  │   ├── role.mapper.ts
  │   └── typeorm-role.repository.ts
  ├── permission/
  │   ├── permission.orm-entity.ts
  │   ├── permission.mapper.ts
  │   └── typeorm-permission.repository.ts
  ├── account-role/
  │   ├── account-role.orm-entity.ts
  │   └── typeorm-account-role.repository.ts
  └── role-permission/
      ├── role-permission.orm-entity.ts
      └── typeorm-role-permission.repository.ts
  ```

  After creating or moving these files, update all imports, exports, Nest providers, and TypeORM entity registration to their new paths.
- Keep domain objects independent of TypeORM decorators.
- Map explicitly between ORM and domain representations.
- Implement every repository method used by application code.
- Put uniqueness and referential integrity in database constraints, not only preflight queries.
- For soft-deletable entities, enforce business-key uniqueness with a partial unique index over the business-key columns and `WHERE deleted_at IS NULL` (using the actual soft-delete column name). Never add soft-delete columns such as `deleted_at` or `deleted_by` to the unique key; PostgreSQL nullable-column semantics would allow duplicate active rows.
- Translate expected constraint violations to stable domain/application errors.
- Analyze concurrent writes and transaction isolation.
- Add forward and reversible migrations; register entities and migrations with the real datasource.
- Test adapters against PostgreSQL when behavior depends on SQL, constraints or transactions.
