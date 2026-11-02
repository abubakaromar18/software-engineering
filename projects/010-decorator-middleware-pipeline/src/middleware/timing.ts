import { type Clock, systemClock } from "../core/clock.js";
import type { Middleware } from "../core/types.js";

export interface TimingSample {
  metric: string;
  durationMs: number;
  outcome: "ok" | "error";
}

export interface TimingOptions {
  /** Metric name reported with every sample. */
  metric: string;
  /** Where samples go: a histogram, StatsD client, array in a test... */
  sink: (sample: TimingSample) => void;
  clock?: Clock;
}

/**
 * Measures wall-clock duration of everything inside this layer and reports it
 * with the outcome. Placed outside `retry` it measures the whole logical call
 * including back-off; placed inside it measures each attempt.
 */
export function timing<Req, Res>(options: TimingOptions): Middleware<Req, Res> {
  const { metric, sink, clock = systemClock } = options;
  return {
    name: "timing",
    wrap: (next) => async (request) => {
      const start = clock.now();
      let outcome: TimingSample["outcome"] = "error";
      try {
        const response = await next(request);
        outcome = "ok";
        return response;
      } finally {
        sink({ metric, durationMs: clock.now() - start, outcome });
      }
    },
  };
}
