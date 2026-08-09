# Data and forms

- Consume the established/generated API client rather than duplicating request contracts.
- Use stable query-key factories and invalidate the narrowest affected keys.
- Keep access tokens in the existing in-memory token store; refresh via the established HttpOnly-cookie flow.
- Use React Hook Form with Zod for client feedback while preserving backend validation as authoritative.
- Map field and form errors without exposing sensitive backend details.
- Prevent duplicate submissions and define optimistic-update rollback when used.
