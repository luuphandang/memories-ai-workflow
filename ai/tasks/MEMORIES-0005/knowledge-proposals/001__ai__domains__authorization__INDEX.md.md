# Proposed update

Target: `ai/domains/authorization/INDEX.md`

Google and Facebook OAuth are both implemented end to end at the provider-client/use-case level (authorization-code flow, profile exchange, account linking by (provider, providerSubject)) but as of 2026-08-18 BOTH are deliberately deferred/disabled on the PUBLIC portal's public HTTP surface — OAuthController fails every provider closed before contacting OAuthClientRegistry, regardless of env config. Only LOCAL phone/password is live on the public surface today. Link/create rule: an AuthIdentity resolves an Account strictly by (provider, providerSubject) — provider-supplied email is never used to cross-link to an existing LOCAL or other-provider Account. Apple remains contract-only/unimplemented.


