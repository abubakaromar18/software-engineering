/**
 * Demo: the same flaky provider behind the same four decorators, in two
 * different orders, to show that ordering changes observable behaviour.
 */
import { systemClock } from "./core/clock.js";
import { Pipeline } from "./core/compose.js";
import { FakeRateProvider, type Rate, type RateRequest, rateServicePipeline } from "./example/exchange-rates.js";
import { cache } from "./middleware/cache.js";
import { consoleLogger, logging } from "./middleware/logging.js";
import { retry } from "./middleware/retry.js";
import { type TimingSample, timing } from "./middleware/timing.js";

const RATES = { "USD/EUR": 0.92, "GBP/USD": 1.27 };
const formatSample = (s: TimingSample): void =>
  console.log(`[metric] ${s.metric} ${s.outcome} ${s.durationMs.toFixed(1)}ms`);

async function run(title: string, pipeline: Pipeline<RateRequest, Rate>, provider: FakeRateProvider): Promise<void> {
  console.log(`\n=== ${title}\n    ${pipeline.describe()}`);
  const lookup = pipeline.build(provider.fetchRate);
  for (const request of [
    { base: "USD", quote: "EUR" },
    { base: "USD", quote: "EUR" },
    { base: "XXX", quote: "YYY" },
  ]) {
    try {
      const { rate } = await lookup(request);
      console.log(`  -> ${request.base}/${request.quote} = ${rate}`);
    } catch (error) {
      console.log(`  -> ${request.base}/${request.quote} threw ${(error as Error).name}`);
    }
  }
  console.log(`  provider was called ${provider.calls} time(s)`);
}

async function main(): Promise<void> {
  // First two provider calls fail transiently.
  const schedule = [true, true];

  await run(
    "Recommended order",
    rateServicePipeline({ logger: consoleLogger, clock: systemClock, metrics: formatSample }),
    new FakeRateProvider(RATES, schedule),
  );

  await run(
    "Inverted order (retry outermost: logs, metrics and cache lookups repeat per attempt)",
    Pipeline.create<RateRequest, Rate>()
      .use(retry({ maxAttempts: 3 }))
      .use(cache({ key: (r) => `${r.base}/${r.quote}`, ttlMs: 60_000 }))
      .use(logging({ logger: consoleLogger, label: "rates.lookup" }))
      .use(timing({ metric: "rates.lookup", sink: formatSample })),
    new FakeRateProvider(RATES, schedule),
  );
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
