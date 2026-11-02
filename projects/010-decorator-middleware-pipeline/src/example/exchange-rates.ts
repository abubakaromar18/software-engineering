import type { Clock } from "../core/clock.js";
import { Pipeline } from "../core/compose.js";
import type { Handler } from "../core/types.js";
import { cache } from "../middleware/cache.js";
import { type Logger, logging } from "../middleware/logging.js";
import { exponentialBackoff, retry } from "../middleware/retry.js";
import { type TimingSample, timing } from "../middleware/timing.js";

export interface RateRequest {
  base: string;
  quote: string;
}

export interface Rate extends RateRequest {
  rate: number;
}

/** A transient failure (timeout, 503...). Worth retrying. */
export class UpstreamUnavailableError extends Error {
  override readonly name = "UpstreamUnavailableError";
}

/** A permanent failure. Retrying cannot help. */
export class UnknownCurrencyError extends Error {
  override readonly name = "UnknownCurrencyError";
}

/**
 * A mocked remote rate provider. It fails according to a scripted schedule so
 * that the demo and tests are deterministic; no network is involved.
 */
export class FakeRateProvider {
  calls = 0;

  constructor(
    private readonly rates: Readonly<Record<string, number>>,
    /** `true` at index i means call number i (0-based) fails transiently. */
    private readonly failureSchedule: readonly boolean[] = [],
  ) {}

  readonly fetchRate: Handler<RateRequest, Rate> = async (request) => {
    const call = this.calls++;
    if (this.failureSchedule[call]) throw new UpstreamUnavailableError("rate provider returned 503");
    const rate = this.rates[`${request.base}/${request.quote}`];
    if (rate === undefined) throw new UnknownCurrencyError(`no rate for ${request.base}/${request.quote}`);
    return { ...request, rate };
  };
}

export interface RateServiceDeps {
  logger: Logger;
  clock: Clock;
  metrics: (sample: TimingSample) => void;
}

/**
 * The recommended layer order for a read-mostly remote lookup, outermost first:
 *
 *  1. timing  — measure what the caller actually experiences (hits, misses, retries).
 *  2. logging — one log line pair per logical call, not per attempt.
 *  3. cache   — a hit short-circuits everything below, including retries.
 *  4. retry   — only the remote call is repeated; permanent errors are not retried.
 */
export function rateServicePipeline(deps: RateServiceDeps): Pipeline<RateRequest, Rate> {
  return Pipeline.create<RateRequest, Rate>()
    .use(timing({ metric: "rates.lookup", sink: deps.metrics, clock: deps.clock }))
    .use(
      logging({
        logger: deps.logger,
        label: "rates.lookup",
        describeRequest: (r) => ({ pair: `${r.base}/${r.quote}` }),
      }),
    )
    .use(cache({ key: (r) => `${r.base}/${r.quote}`, ttlMs: 60_000, clock: deps.clock }))
    .use(
      retry({
        maxAttempts: 3,
        backoff: exponentialBackoff({ baseMs: 100, maxMs: 1_000 }),
        shouldRetry: (error) => error instanceof UpstreamUnavailableError,
        clock: deps.clock,
      }),
    );
}
