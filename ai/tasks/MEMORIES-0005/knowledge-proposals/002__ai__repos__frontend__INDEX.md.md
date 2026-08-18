# Proposed update

Target: `ai/repos/frontend/INDEX.md`

packages/auth's AuthContextValue gained loginWithPhone(phone, password, portal)/registerLocal(input) alongside the pre-existing login(email, password) (kept only for apps/admin-web, whose real backend contract mismatch is a separate pre-existing issue out of this task's scope). isAuthenticated is now derived from access-token presence alone, not a `user` object — neither /auth/login, /auth/register nor /auth/refresh's real response includes one.


