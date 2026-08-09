# Identity and credential rules

- Normalize identifiers before lookup and persistence; store one canonical representation.
- Enforce `(provider, identifier)` and provider-subject uniqueness in the database where applicable.
- Handle duplicate-key races and return a stable conflict without exposing database details.
- Hash passwords using the configured adaptive password hasher; never encrypt or log plaintext credentials.
- Keep password hashes and provider secrets out of API responses, events and logs.
- Compare secrets through established libraries and avoid custom cryptography.
- Allow multiple provider identities per account without conflating profile data with authentication identity.
