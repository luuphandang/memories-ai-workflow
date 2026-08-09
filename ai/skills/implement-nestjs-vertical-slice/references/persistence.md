# TypeORM persistence checks

- Keep domain objects independent of TypeORM decorators.
- Map explicitly between ORM and domain representations.
- Implement every repository method used by application code.
- Put uniqueness and referential integrity in database constraints, not only preflight queries.
- Translate expected constraint violations to stable domain/application errors.
- Analyze concurrent writes and transaction isolation.
- Add forward and reversible migrations; register entities and migrations with the real datasource.
- Test adapters against PostgreSQL when behavior depends on SQL, constraints or transactions.
