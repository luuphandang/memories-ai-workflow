export interface UserRepository { save(): Promise<void>; }
export const USER_REPOSITORY = Symbol('USER_REPOSITORY');
