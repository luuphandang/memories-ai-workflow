# Dependency-injection checks

For every `@Inject(TOKEN)` or constructor dependency:

1. Locate the token declaration and interface.
2. Locate the concrete adapter or service.
3. Locate a provider using `provide`, `useClass`, `useFactory`, `useExisting` or a directly injectable class.
4. Verify its module imports dependencies required by the provider.
5. Verify the consuming use case/controller is registered.
6. Verify exports when another module consumes the token.
7. Compile a testing module or boot the relevant application in an integration/E2E test.

A TypeScript compile does not prove the Nest runtime graph is resolvable.
