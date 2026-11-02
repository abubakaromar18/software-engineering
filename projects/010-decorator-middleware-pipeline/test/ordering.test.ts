/**
 * The point of this project: the same four decorators produce different,
 * observable behaviour depending on where they sit in the chain. Each test
 * builds the same stack in two orders and asserts the difference.
 */
import { describe, expect, it } from "vitest";
import { Pipeline } from "../src/core/compose.js";
import { cache } from "../src/middleware/cache.js";
import { logging } from "../src/middleware/logging.js";
import { retry } from "../src/middleware/retry.js";
import { type TimingSample, timing } from "../src/middleware/timing.js";
import { FakeClock, flaky, MemoryLogger } from "./support/fakes.js";

type P = Pipeline<string, string>;
const pipeline = (): P => Pipeline.create<string, string>();

describe("ordering semantics", () => {
  describe("logging vs retry", () => {
    it("logging OUTSIDE retry logs one logical call", async () => {
      const logger = new MemoryLogger();
      const clock = new FakeClock();
      const handler = pipeline()
        .use(logging({ logger }))
        .use(retry({ maxAttempts: 3, clock }))
        .build(flaky(2));

      await handler("x");
      expect(logger.messages()).toEqual(["call start", "call ok"]);
    });

    it("logging INSIDE retry logs every attempt, including failed ones", async () => {
      const logger = new MemoryLogger();
      const clock = new FakeClock();
      const handler = pipeline()
        .use(retry({ maxAttempts: 3, clock }))
        .use(logging({ logger }))
        .build(flaky(2));

      await handler("x");
      expect(logger.messages()).toEqual([
        "call start",
        "call failed",
        "call start",
        "call failed",
        "call start",
        "call ok",
      ]);
    });
  });

  describe("timing vs retry", () => {
    const run = async (build: (clock: FakeClock, sink: (s: TimingSample) => void) => P) => {
      const clock = new FakeClock();
      const samples: TimingSample[] = [];
      await build(clock, (s) => samples.push(s)).build(flaky(2, clock, 10))("x");
      return samples;
    };

    it("timing OUTSIDE retry measures the whole call, including back-off", async () => {
      const samples = await run((clock, sink) =>
        pipeline()
          .use(timing({ metric: "t", sink, clock }))
          .use(retry({ maxAttempts: 3, backoff: () => 100, clock })),
      );
      // 3 attempts x 10ms + 2 back-offs x 100ms
      expect(samples).toEqual([{ metric: "t", durationMs: 230, outcome: "ok" }]);
    });

    it("timing INSIDE retry measures each attempt and excludes back-off", async () => {
      const samples = await run((clock, sink) =>
        pipeline()
          .use(retry({ maxAttempts: 3, backoff: () => 100, clock }))
          .use(timing({ metric: "t", sink, clock })),
      );
      expect(samples.map((s) => [s.durationMs, s.outcome])).toEqual([
        [10, "error"],
        [10, "error"],
        [10, "ok"],
      ]);
    });
  });

  describe("cache vs retry", () => {
    it("cache OUTSIDE retry: a hit skips the retry machinery entirely", async () => {
      const clock = new FakeClock();
      const inner = flaky<string>(1);
      const handler = pipeline()
        .use(cache({ key: (s) => s, ttlMs: 1_000, clock }))
        .use(retry({ maxAttempts: 2, backoff: () => 50, clock }))
        .build(inner);

      await handler("x");
      await handler("x");
      expect(inner.calls).toBe(2); // 1 failure + 1 success, then a hit
      expect(clock.sleeps).toEqual([50]);
    });

    it("cache INSIDE retry: transient failures still reach the cache on each attempt", async () => {
      const clock = new FakeClock();
      const lookups: boolean[] = [];
      const inner = flaky<string>(1);
      const handler = pipeline()
        .use(retry({ maxAttempts: 2, clock }))
        .use(cache({ key: (s) => s, ttlMs: 1_000, clock, onLookup: ({ hit }) => lookups.push(hit) }))
        .build(inner);

      await handler("x");
      await handler("x");
      // attempt 1 miss (fails), attempt 2 miss (succeeds), second call hit
      expect(lookups).toEqual([false, false, true]);
      expect(inner.calls).toBe(2);
    });
  });

  describe("logging/timing vs cache", () => {
    it("observers OUTSIDE the cache see hits; INSIDE they only see misses", async () => {
      const outerLog = new MemoryLogger();
      const innerLog = new MemoryLogger();
      const clock = new FakeClock();
      const handler = pipeline()
        .use(logging({ logger: outerLog }))
        .use(cache({ key: (s) => s, ttlMs: 1_000, clock }))
        .use(logging({ logger: innerLog }))
        .build(flaky(0));

      await handler("x");
      await handler("x");
      await handler("x");
      expect(outerLog.messages()).toHaveLength(6); // 3 calls
      expect(innerLog.messages()).toHaveLength(2); // 1 miss
    });
  });
});
