# Review passes

## Full review

Complete all seven passes:

1. `requirements`: map each effective criterion to code paths and verification evidence.
2. `diff`: read the complete tracked diff, untracked implementation files and direct dependencies.
3. `architecture`: trace changed contracts, boundaries, persistence and runtime wiring across layers and repositories.
4. `behavior`: check happy, error, boundary, state-transition and compatibility behavior.
5. `tests`: inspect assertions, branch coverage, fixtures and command output independently of the handoff.
6. `security`: inspect authorization, validation, secrets/PII, injection, session and privilege boundaries when applicable.
7. `regression`: retest prior findings and adjacent behavior affected by the blast radius.

Inventory every changed implementation file in `review_coverage.changed_files`. Record each risk surface as `reviewed` or `not_applicable` with evidence. A full review is required before final acceptance.

## Delta review

Use delta mode only immediately after a full review returned `changes_requested` and the surrounding workflow explicitly selects delta mode. Review the newest fix request, affected diff and direct dependencies. Complete `diff`, `behavior`, `tests` and `regression`; include other passes when the correction touches them.

A delta pass proves only that the correction survived its focused review. Require a new passing full review before final acceptance.

## Coverage integrity

- Do not stop at the first issue or release findings incrementally.
- Mark the verdict `blocked` if a required pass, changed file, risk area or prior finding cannot be verified.
- Use current-cycle source and validation evidence only.
- Prefer architecture/symbol tools for impact discovery when the repository declares them ready; use direct reads for live changes and graph gaps.
