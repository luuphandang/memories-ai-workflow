export async function createAccount(repo: any, provider: string, identifier: string) {
  if (await repo.existsByProviderAndIdentifier(provider, identifier)) throw new Error('exists');
}
