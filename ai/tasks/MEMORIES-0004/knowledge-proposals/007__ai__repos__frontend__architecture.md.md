# Proposed update

Target: `ai/repos/frontend/architecture.md`

The 'chưa có page nào thật sự gọi useQuery/useMutation' statement is now outdated — /mau-thiep and /qua-ky-niem are the first real consumers. Document the ApiClientProvider (apps/public-web/lib/api/api-client-context.tsx) pattern for exposing the single ApiClient instance to hooks, and the useUrlFilterState URL-as-source-of-truth pattern, as the reference for future data-driven pages.


