import type { Clock } from "../../src/core/clock.js";
import type { Handler, Middleware } from "../../src/core/types.js";
import type { Logger, LogLevel } from "../../src/middleware/logging.js";

/** Deterministic clock: `sleep` advances virtual time instantly and is recorded. */
export class FakeClock implements Clock {
  readonly sleeps: number[] = [];
  constructor(private time = 0) {}
  now(): number {
    return this.time;
  }
  advance(ms: number): void {
    this.time += ms;
  }
  async sleep(ms: number): Promise<void> {
    this.sleeps.push(ms);
    this.time += ms;
  }
}

export class MemoryLogger implements Logger {
  readonly lines: { level: LogLevel; message: string; fields: Readonly<Record<string, unknown>> }[] = [];
  log(level: LogLevel, message: string, fields: Readonly<Record<string, unknown>>): void {
    this.lines.push({ level, message, fields });
  }
  messages(): string[] {
    return this.lines.map((l) => l.message);
  }
}

/** A handler that fails `failures` times, then echoes; optionally takes virtual time per call. */
export function flaky<T>(failures: number, clock?: FakeClock, costMs = 0): Handler<T, T> & { calls: number } {
  const handler = Object.assign(
    async (request: T): Promise<T> => {
      handler.calls++;
      clock?.advance(costMs);
      if (handler.calls <= failures) throw new Error(`boom #${handler.calls}`);
      return request;
    },
    { calls: 0 },
  );
  return handler;
}

/** Middleware that records enter/exit events into a shared trace. */
export function tracer<Req, Res>(name: string, trace: string[]): Middleware<Req, Res> {
  return {
    name,
    wrap: (next) => async (request) => {
      trace.push(`${name}:in`);
      try {
        return await next(request);
      } finally {
        trace.push(`${name}:out`);
      }
    },
  };
}

/** A promise whose resolution is controlled by the test. */
export function deferred<T>(): { promise: Promise<T>; resolve: (v: T) => void; reject: (e: unknown) => void } {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
