export async function createAccount(repo: any, provider: string, identifier: string) {
  return repo.existsByProviderAndIdentifier(provider, identifier);
}
