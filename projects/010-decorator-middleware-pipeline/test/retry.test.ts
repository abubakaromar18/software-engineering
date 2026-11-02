import { describe, expect, it } from "vitest";
import { ConfigError, RetryExhaustedError } from "../src/core/errors.js";
import { exponentialBackoff, retry } from "../src/middleware/retry.js";
import { FakeClock, flaky } from "./support/fakes.js";

describe("retry", () => {
  it("returns the first success and stops retrying", async () => {
    const inner = flaky<string>(2);
    const handler = retry<string, string>({ maxAttempts: 5, clock: new FakeClock() }).wrap(inner);
    await expect(handler("ok")).resolves.toBe("ok");
    expect(inner.calls).toBe(3);
  });

  it("throws RetryExhaustedError carrying every attempt's error", async () => {
    const inner = flaky<string>(10);
    const handler = retry<string, string>({ maxAttempts: 3, clock: new FakeClock() }).wrap(inner);

    const error = await handler("x").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(RetryExhaustedError);
    const exhausted = error as RetryExhaustedError;
    expect(exhausted.attempts).toBe(3);
    expect(exhausted.errors.map((e) => (e as Error).message)).toEqual(["boom #1", "boom #2", "boom #3"]);
    expect((exhausted.cause as Error).message).toBe("boom #3");
    expect(inner.calls).toBe(3);
  });

  it("propagates non-retryable errors immediately and unwrapped", async () => {
    const inner = flaky<string>(10);
    const permanent = retry<string, string>({
      maxAttempts: 5,
      shouldRetry: () => false,
      clock: new FakeClock(),
    }).wrap(inner);

    await expect(permanent("x")).rejects.toThrow("boom #1");
    expect(inner.calls).toBe(1);
  });

  it("passes the attempt number to shouldRetry", async () => {
    const seen: number[] = [];
    const handler = retry<string, string>({
      maxAttempts: 10,
      shouldRetry: (_e, attempt) => {
        seen.push(attempt);
        return attempt < 2;
      },
      clock: new FakeClock(),
    }).wrap(flaky(10));
    await expect(handler("x")).rejects.toThrow("boom #2");
    expect(seen).toEqual([1, 2]);
  });

  it("sleeps according to the back-off strategy between attempts only", async () => {
    const clock = new FakeClock();
    const handler = retry<string, string>({
      maxAttempts: 4,
      backoff: exponentialBackoff({ baseMs: 100 }),
      clock,
    }).wrap(flaky(3));

    await handler("x");
    expect(clock.sleeps).toEqual([100, 200, 400]);
  });

  it("rejects invalid configuration at build time", () => {
    expect(() => retry({ maxAttempts: 0 })).toThrow(ConfigError);
    expect(() => retry({ maxAttempts: 1.5 })).toThrow(ConfigError);
  });
});

describe("exponentialBackoff", () => {
  it("doubles and caps", () => {
    const backoff = exponentialBackoff({ baseMs: 50, maxMs: 300 });
    expect([1, 2, 3, 4, 5].map(backoff)).toEqual([50, 100, 200, 300, 300]);
  });

  it("applies full jitter within [0, capped] using the injected random source", () => {
    const backoff = exponentialBackoff({ baseMs: 100, jitter: true, random: () => 0.5 });
    expect([1, 2, 3].map(backoff)).toEqual([50, 100, 200]);
  });

  it("rejects negative delays", () => {
    expect(() => exponentialBackoff({ baseMs: -1 })).toThrow(ConfigError);
  });
});
