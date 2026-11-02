import { type Clock, systemClock } from "../core/clock.js";
import { ConfigError, RetryExhaustedError } from "../core/errors.js";
import type { Middleware } from "../core/types.js";

/** Returns the delay in ms before retry number `retry` (1-based). */
export type BackoffStrategy = (retry: number) => number;

export interface RetryOptions {
  /** Total attempts including the first. Must be an integer >= 1. */
  maxAttempts: number;
  /** Delay policy between attempts. Defaults to no delay. */
  backoff?: BackoffStrategy;
  /** Decide whether an error is transient. Non-retryable errors propagate immediately and unwrapped. */
  shouldRetry?: (error: unknown, attempt: number) => boolean;
  clock?: Clock;
}

/**
 * Capped exponential back-off with optional jitter.
 * `random` is injectable so the jitter is deterministic in tests.
 */
export function exponentialBackoff(options: {
  baseMs: number;
  maxMs?: number;
  jitter?: boolean;
  random?: () => number;
}): BackoffStrategy {
  const { baseMs, maxMs = Number.POSITIVE_INFINITY, jitter = false, random = Math.random } = options;
  if (baseMs < 0 || maxMs < 0) throw new ConfigError("backoff delays must be non-negative");
  return (retry) => {
    const capped = Math.min(maxMs, baseMs * 2 ** (retry - 1));
    // "Full jitter": pick uniformly in [0, capped] to spread out synchronized retries.
    return jitter ? Math.round(random() * capped) : capped;
  };
}

/**
 * Re-invokes the inner handler when it throws a retryable error.
 *
 * Ordering matters: everything INSIDE this layer runs once per attempt;
 * everything OUTSIDE runs once per logical call.
 */
export function retry<Req, Res>(options: RetryOptions): Middleware<Req, Res> {
  const { maxAttempts, backoff = () => 0, shouldRetry = () => true, clock = systemClock } = options;
  if (!Number.isInteger(maxAttempts) || maxAttempts < 1) {
    throw new ConfigError(`maxAttempts must be an integer >= 1, got ${maxAttempts}`);
  }

  return {
    name: "retry",
    wrap: (next) => async (request) => {
      const errors: unknown[] = [];
      for (let attempt = 1; ; attempt++) {
        try {
          return await next(request);
        } catch (error) {
          if (!shouldRetry(error, attempt)) throw error;
          errors.push(error);
          if (attempt >= maxAttempts) throw new RetryExhaustedError(attempt, errors);
          await clock.sleep(backoff(attempt));
        }
      }
    },
  };
}
