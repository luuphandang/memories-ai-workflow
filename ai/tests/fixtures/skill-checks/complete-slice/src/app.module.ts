import { Module } from '@nestjs/common';
import { USER_REPOSITORY } from './user.repository';
import { UserRepositoryAdapter } from './user.repository.adapter';
import { CreateUserUseCase } from './create-user.use-case';
@Module({ providers: [CreateUserUseCase, { provide: USER_REPOSITORY, useClass: UserRepositoryAdapter }] })
export class AppModule {}
