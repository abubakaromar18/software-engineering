import { describe, expect, it } from "vitest";
import { ConfigError } from "../src/core/errors.js";
import { cache } from "../src/middleware/cache.js";
import { deferred, FakeClock, flaky } from "./support/fakes.js";

const byValue = (s: string) => s;

describe("cache", () => {
  it("serves repeated keys from cache and reports hits/misses", async () => {
    const lookups: boolean[] = [];
    const inner = flaky<string>(0);
    const handler = cache<string, string>({
      key: byValue,
      ttlMs: 1_000,
      clock: new FakeClock(),
      onLookup: ({ hit }) => lookups.push(hit),
    }).wrap(inner);

    await handler("a");
    await handler("a");
    await handler("b");
    expect(inner.calls).toBe(2);
    expect(lookups).toEqual([false, true, false]);
  });

  it("expires entries after the TTL", async () => {
    const clock = new FakeClock();
    const inner = flaky<string>(0);
    const handler = cache<string, string>({ key: byValue, ttlMs: 1_000, clock }).wrap(inner);

    await handler("a");
    clock.advance(999);
    await handler("a");
    expect(inner.calls).toBe(1);
    clock.advance(1);
    await handler("a");
    expect(inner.calls).toBe(2);
  });

  it("does not cache failures", async () => {
    const inner = flaky<string>(1);
    const handler = cache<string, string>({ key: byValue, ttlMs: 1_000, clock: new FakeClock() }).wrap(inner);

    await expect(handler("a")).rejects.toThrow("boom #1");
    await expect(handler("a")).resolves.toBe("a");
    expect(inner.calls).toBe(2);
  });

  it("coalesces concurrent misses for the same key into one inner call", async () => {
    const gate = deferred<string>();
    let calls = 0;
    const handler = cache<string, string>({ key: byValue, ttlMs: 1_000, clock: new FakeClock() }).wrap(() => {
      calls++;
      return gate.promise;
    });

    const results = Promise.all([handler("a"), handler("a"), handler("a")]);
    gate.resolve("value");
    await expect(results).resolves.toEqual(["value", "value", "value"]);
    expect(calls).toBe(1);
  });

  it("shares an in-flight failure with every waiter, then allows a fresh attempt", async () => {
    const gate = deferred<string>();
    let calls = 0;
    const handler = cache<string, string>({ key: byValue, ttlMs: 1_000, clock: new FakeClock() }).wrap((s) => {
      calls++;
      return calls === 1 ? gate.promise : Promise.resolve(s);
    });

    const first = handler("a");
    const second = handler("a");
    gate.reject(new Error("down"));
    await expect(first).rejects.toThrow("down");
    await expect(second).rejects.toThrow("down");
    await expect(handler("a")).resolves.toBe("a");
    expect(calls).toBe(2);
  });

  it("evicts the least-recently-used entry when full", async () => {
    const inner = flaky<string>(0);
    const handler = cache<string, string>({ key: byValue, ttlMs: 1_000, maxEntries: 2, clock: new FakeClock() }).wrap(
      inner,
    );

    await handler("a");
    await handler("b");
    await handler("a"); // touch "a" so "b" becomes least recently used
    await handler("c"); // evicts "b"
    expect(inner.calls).toBe(3);

    await handler("a");
    expect(inner.calls).toBe(3); // still cached
    await handler("b");
    expect(inner.calls).toBe(4); // was evicted
  });

  it("keeps state per wrapped handler", async () => {
    const middleware = cache<string, string>({ key: byValue, ttlMs: 1_000, clock: new FakeClock() });
    const one = flaky<string>(0);
    const two = flaky<string>(0);
    await middleware.wrap(one)("a");
    await middleware.wrap(two)("a");
    expect([one.calls, two.calls]).toEqual([1, 1]);
  });

  it("rejects invalid configuration", () => {
    expect(() => cache({ key: byValue, ttlMs: 0 })).toThrow(ConfigError);
    expect(() => cache({ key: byValue, ttlMs: 1, maxEntries: 0 })).toThrow(ConfigError);
  });
});
