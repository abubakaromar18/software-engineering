import { describe, expect, it } from "vitest";
import { logging } from "../src/middleware/logging.js";
import { type TimingSample, timing } from "../src/middleware/timing.js";
import { FakeClock, flaky, MemoryLogger } from "./support/fakes.js";

describe("logging", () => {
  it("logs start and ok with request fields", async () => {
    const logger = new MemoryLogger();
    const handler = logging<number, number>({ logger, label: "op", describeRequest: (n) => ({ n }) }).wrap(
      async (n) => n,
    );
    await handler(7);
    expect(logger.lines).toEqual([
      { level: "info", message: "op start", fields: { n: 7 } },
      { level: "info", message: "op ok", fields: { n: 7 } },
    ]);
  });

  it("logs failures and rethrows the original error unchanged", async () => {
    const logger = new MemoryLogger();
    const original = new TypeError("bad");
    const handler = logging<void, never>({ logger }).wrap(async () => {
      throw original;
    });

    await expect(handler()).rejects.toBe(original);
    expect(logger.lines[1]).toEqual({ level: "error", message: "call failed", fields: { error: "TypeError: bad" } });
  });

  it("does not log request payloads unless asked to", async () => {
    const logger = new MemoryLogger();
    await logging<string, string>({ logger }).wrap(async (s) => s)("secret-token");
    expect(JSON.stringify(logger.lines)).not.toContain("secret-token");
  });
});

describe("timing", () => {
  it("reports duration and outcome for success and failure", async () => {
    const clock = new FakeClock();
    const samples: TimingSample[] = [];
    const handler = timing<string, string>({ metric: "m", sink: (s) => samples.push(s), clock }).wrap(
      flaky(1, clock, 25),
    );

    await expect(handler("x")).rejects.toThrow();
    await handler("x");
    expect(samples).toEqual([
      { metric: "m", durationMs: 25, outcome: "error" },
      { metric: "m", durationMs: 25, outcome: "ok" },
    ]);
  });
});
