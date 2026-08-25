import { BullMqConfig } from '@memories/platform/configuration';
import { CorrelationContext } from '@memories/platform/observability';
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JobsOptions } from 'bullmq';

import { BackgroundJobEnvelope } from '../contracts/background-job-envelope';
import { BackgroundJobOptions } from '../contracts/background-job-options';
import { BackgroundJobPublisher } from '../contracts/background-job-publisher';
import { QueueRegistry } from '../registry/queue.registry';

import { BullMqQueueFactory } from './bullmq-queue.factory';

const JOB_NAME_PATTERN = /^[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.v\d+$/;

@Injectable()
export class BullMqPublisher implements BackgroundJobPublisher {
  constructor(
    private readonly queueFactory: BullMqQueueFactory,
    private readonly queueRegistry: QueueRegistry,
    private readonly configService: ConfigService,
  ) {}

  async publish<TPayload>(
    jobName: string,
    payload: TPayload,
    options: BackgroundJobOptions = {},
  ): Promise<string> {
    if (!JOB_NAME_PATTERN.test(jobName)) {
      throw new Error(
        `Invalid job name "${jobName}": expected "<domain>.<action>.v<version>", e.g. "media.generate-thumbnail.v1"`,
      );
    }

    const queueName = this.queueRegistry.queueNameForJob(jobName);
    const queue = this.queueFactory.getQueue(queueName);
    const version = Number(jobName.split('.v').pop());

    const jobId = options.jobId ?? crypto.randomUUID();
    const envelope: BackgroundJobEnvelope<TPayload> = {
      jobId,
      jobName,
      version,
      createdAt: new Date().toISOString(),
      // Defaults to the ambient HTTP request's correlation ID (set by CorrelationMiddleware) so
      // a job published while handling a request carries the same ID into the worker's logs.
      correlationId:
        options.correlationId ?? CorrelationContext.correlationId() ?? crypto.randomUUID(),
      causationId: options.causationId,
      actorId: options.actorId,
      payload,
    };

    const jobOptions = this.resolveJobOptions(queueName, options, jobId);
    const job = await queue.add(jobName, envelope, jobOptions);
    return job.id ?? jobId;
  }

  private resolveJobOptions(
    queueName: string,
    options: BackgroundJobOptions,
    jobId: string,
  ): JobsOptions {
    const platformDefaults =
      this.configService.getOrThrow<BullMqConfig>('bullmq').defaultJobOptions;
    const queueOverrides = this.queueRegistry.get(queueName).overrides?.defaultJobOptions;

    const attempts = options.attempts ?? queueOverrides?.attempts ?? platformDefaults.attempts;
    const backoffMs = options.backoffMs ?? queueOverrides?.backoffMs ?? platformDefaults.backoffMs;
    const removeOnComplete =
      options.removeOnComplete ??
      queueOverrides?.removeOnComplete ??
      platformDefaults.removeOnComplete;
    const removeOnFail =
      options.removeOnFail ?? queueOverrides?.removeOnFail ?? platformDefaults.removeOnFail;

    // bullmq's JobsOptions type does not itself opt into exactOptionalPropertyTypes, so an
    // explicit `key: undefined` is a type error — omit optional keys instead of setting them.
    return {
      jobId,
      attempts,
      backoff: { type: 'exponential', delay: backoffMs },
      removeOnComplete,
      removeOnFail,
      ...(options.delayMs !== undefined && { delay: options.delayMs }),
      ...(options.priority !== undefined && { priority: options.priority }),
    };
  }
}
