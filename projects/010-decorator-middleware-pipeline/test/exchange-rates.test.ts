import { describe, expect, it } from "vitest";
import { RetryExhaustedError } from "../src/core/errors.js";
import {
  FakeRateProvider,
  rateServicePipeline,
  UnknownCurrencyError,
  UpstreamUnavailableError,
} from "../src/example/exchange-rates.js";
import type { TimingSample } from "../src/middleware/timing.js";
import { FakeClock, MemoryLogger } from "./support/fakes.js";

const RATES = { "USD/EUR": 0.92 };

function setup(schedule: boolean[] = []) {
  const clock = new FakeClock();
  const logger = new MemoryLogger();
  const samples: TimingSample[] = [];
  const provider = new FakeRateProvider(RATES, schedule);
  const pipeline = rateServicePipeline({ logger, clock, metrics: (s) => samples.push(s) });
  return { clock, logger, samples, provider, pipeline, lookup: pipeline.build(provider.fetchRate) };
}

describe("rate service pipeline", () => {
  it("declares the recommended order", () => {
    expect(setup().pipeline.describe()).toBe("timing → logging → cache → retry → handler");
  });

  it("recovers from transient failures with back-off and caches the result", async () => {
    const { lookup, provider, clock, logger, samples } = setup([true, true]);
    const request = { base: "USD", quote: "EUR" };

    await expect(lookup(request)).resolves.toEqual({ ...request, rate: 0.92 });
    await expect(lookup(request)).resolves.toEqual({ ...request, rate: 0.92 });

    expect(provider.calls).toBe(3);
    expect(clock.sleeps).toEqual([100, 200]);
    expect(logger.messages()).toEqual(["rates.lookup start", "rates.lookup ok", "rates.lookup start", "rates.lookup ok"]);
    expect(logger.lines[0]?.fields).toEqual({ pair: "USD/EUR" });
    expect(samples.map((s) => s.durationMs)).toEqual([300, 0]);
  });

  it("does not retry permanent errors", async () => {
    const { lookup, provider, clock } = setup();
    await expect(lookup({ base: "XXX", quote: "YYY" })).rejects.toBeInstanceOf(UnknownCurrencyError);
    expect(provider.calls).toBe(1);
    expect(clock.sleeps).toEqual([]);
  });

  it("gives up after three transient failures", async () => {
    const { lookup, logger, samples } = setup([true, true, true]);
    const error = await lookup({ base: "USD", quote: "EUR" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(RetryExhaustedError);
    expect((error as RetryExhaustedError).cause).toBeInstanceOf(UpstreamUnavailableError);
    expect(logger.lines.at(-1)?.level).toBe("error");
    expect(samples.at(-1)?.outcome).toBe("error");
  });
});
