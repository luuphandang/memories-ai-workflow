# Proposed update

Target: `ai/repos/backend/architecture.md`

Verifying a third-party OIDC ID token (signature + issuer/audience/expiry/nonce claims) does not require adding a JWT/JWKS dependency to this backend: Node 20's built-in `node:crypto` already covers it end to end — `crypto.createPublicKey({key: jwk, format:'jwk'})` accepts a provider's published JWKS key object directly (no PEM conversion needed), and the one-shot `crypto.verify(algorithm, data, key, signature)` checks an RS256 signature without `jsonwebtoken`/`jose`/`jwks-rsa`. See GoogleOAuthClient.verifyIdToken (libs/modules/identity-access/src/infrastructure/security/google-oauth.client.ts) for the reference implementation: base64url-decode the three JWT segments, match `kid` against a cached JWKS fetch, verify the signature over `${header}.${payload}`, then check `iss`/`aud`/`exp`/`nonce` as plain claim comparisons.


