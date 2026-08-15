# Proposed update

Target: `ai/repos/backend/conventions.md`

Document that every `@ApiResponse({...})` decorator on a handler must stay on one line (put `description` text in a `//` comment above instead) — `check_openapi_contract.py`'s boundary heuristic truncates the captured block at any multi-line decorator's closing `})` right before the handler, and a useful `description` almost always exceeds printWidth 100, so the two mandatory gates conflict unless description text is kept out of the decorator.


