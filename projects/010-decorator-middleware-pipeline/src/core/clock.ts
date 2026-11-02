/**
 * Time is an external dependency. Retry back-off, cache TTLs and timing all
 * read it through this interface so tests can substitute a deterministic
 * clock instead of sleeping for real.
 */
export interface Clock {
  /** Milliseconds on a monotonic-ish timeline. Only differences matter. */
  now(): number;
  /** Resolve after `ms` milliseconds. */
  sleep(ms: number): Promise<void>;
}

export const systemClock: Clock = {
  now: () => performance.now(),
  sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
};
