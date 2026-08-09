# Review gates

Request changes when any applicable condition holds:

- A declared/consumed port lacks an adapter or DI provider.
- A provider/use case/controller is unreachable from the application module graph.
- Persistence shape changed without a migration or explicit evidence that none is needed.
- Uniqueness, authorization or concurrency relies only on a preflight application check.
- API behavior lacks DTO validation, authorization or compatibility analysis.
- A core acceptance criterion has no executable test or justified verification evidence.
- Required-skill checks or current-cycle deterministic validation are missing.
- Handoff files do not match the diff or current execution-plan cycle.

Do not request speculative architecture changes unrelated to an effective requirement or demonstrated risk.
