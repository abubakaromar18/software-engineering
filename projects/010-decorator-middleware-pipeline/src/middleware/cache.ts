import { type Clock, systemClock } from "../core/clock.js";
import { ConfigError } from "../core/errors.js";
import type { Middleware } from "../core/types.js";

export interface CacheOptions<Req> {
  /** Derive a cache key. Two requests with the same key must be interchangeable. */
  key: (request: Req) => string;
  /** Time-to-live for a successful response. */
  ttlMs: number;
  /** Upper bound on stored entries; the least-recently-used entry is evicted first. */
  maxEntries?: number;
  clock?: Clock;
  /** Optional hook for hit/miss metrics. */
  onLookup?: (event: { key: string; hit: boolean }) => void;
}

interface Entry<Res> {
  value: Res;
  expiresAt: number;
}

/**
 * Read-through cache with TTL, LRU eviction and in-flight request coalescing
 * ("single flight"): concurrent misses for the same key share one call to the
 * inner handler instead of stampeding it.
 *
 * Only successes are cached. A failure is propagated to every waiter and the
 * next call tries again.
 */
export function cache<Req, Res>(options: CacheOptions<Req>): Middleware<Req, Res> {
  const { key, ttlMs, maxEntries = 1_000, clock = systemClock, onLookup = () => {} } = options;
  if (ttlMs <= 0) throw new ConfigError(`ttlMs must be positive, got ${ttlMs}`);
  if (!Number.isInteger(maxEntries) || maxEntries < 1) {
    throw new ConfigError(`maxEntries must be an integer >= 1, got ${maxEntries}`);
  }

  return {
    name: "cache",
    wrap: (next) => {
      // State lives per wrapped handler, so two pipelines never share entries.
      // A Map iterates in insertion order, which gives us LRU for free:
      // re-inserting on read moves an entry to the "most recent" end.
      const entries = new Map<string, Entry<Res>>();
      const inFlight = new Map<string, Promise<Res>>();

      const store = (k: string, value: Res): void => {
        entries.delete(k);
        entries.set(k, { value, expiresAt: clock.now() + ttlMs });
        if (entries.size > maxEntries) {
          const oldest = entries.keys().next().value as string;
          entries.delete(oldest);
        }
      };

      return async (request) => {
        const k = key(request);
        const entry = entries.get(k);
        if (entry && entry.expiresAt > clock.now()) {
          entries.delete(k);
          entries.set(k, entry);
          onLookup({ key: k, hit: true });
          return entry.value;
        }
        if (entry) entries.delete(k);
        onLookup({ key: k, hit: false });

        const pending = inFlight.get(k);
        if (pending) return pending;

        const call = next(request)
          .then((value) => {
            store(k, value);
            return value;
          })
          .finally(() => inFlight.delete(k));
        inFlight.set(k, call);
        return call;
      };
    },
  };
}
