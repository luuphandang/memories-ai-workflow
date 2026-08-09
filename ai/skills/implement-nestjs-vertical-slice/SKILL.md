---
name: implement-nestjs-vertical-slice
description: Implement or modify a NestJS feature as a complete Clean Architecture vertical slice, including domain, application ports/use cases, infrastructure adapters, TypeORM persistence, dependency injection, module/public API wiring, migrations, controllers and tests. Use for backend NestJS tasks and whenever repository interfaces, injection tokens, modules or persistence are changed.
---

# Implement a NestJS vertical slice

1. Select the current slice from `execution-plan.json`; do not start a second slice until its completion checks pass.
2. Build a layer matrix using [clean-architecture.md](references/clean-architecture.md).
3. Trace every consumed port to an adapter and every injection token to a reachable Nest provider using [dependency-injection.md](references/dependency-injection.md).
4. For persistence changes, apply [persistence.md](references/persistence.md), including mapper, migration, constraints and transaction behavior.
5. Add tests following [testing.md](references/testing.md).
6. Run `scripts/check_port_bindings.py <worktree>` and `scripts/check_module_wiring.py <worktree>` before declaring the slice complete.
7. Record files, validation and evidence in the checkpoint and final handoff.

Never consider an interface, use case or entity alone to be a completed feature. Verify runtime reachability from the application module to the implementation.
