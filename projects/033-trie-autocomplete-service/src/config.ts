import type { AutocompleteOptions } from "./autocomplete-service.js";

export interface AppConfig extends AutocompleteOptions {
  readonly host: string;
  readonly port: number;
  readonly corpusPath: string;
}

export const DEFAULT_CONFIG: AppConfig = {
  host: "127.0.0.1",
  port: 3000,
  corpusPath: "data/words.tsv",
  defaultLimit: 5,
  maxLimit: 50,
  maxQueryLength: 100,
};

/**
 * Builds configuration from environment variables, falling back to defaults.
 * Taking `env` as a parameter (instead of reading process.env directly) keeps
 * this function pure and trivially testable.
 */
export function loadConfig(env: Readonly<Record<string, string | undefined>>): AppConfig {
  return {
    host: env["HOST"] ?? DEFAULT_CONFIG.host,
    port: intFrom(env, "PORT", DEFAULT_CONFIG.port, 0, 65_535),
    corpusPath: env["CORPUS_PATH"] ?? DEFAULT_CONFIG.corpusPath,
    defaultLimit: intFrom(env, "DEFAULT_LIMIT", DEFAULT_CONFIG.defaultLimit, 1, 1_000),
    maxLimit: intFrom(env, "MAX_LIMIT", DEFAULT_CONFIG.maxLimit, 1, 1_000),
    maxQueryLength: intFrom(env, "MAX_QUERY_LENGTH", DEFAULT_CONFIG.maxQueryLength, 1, 10_000),
  };
}

function intFrom(
  env: Readonly<Record<string, string | undefined>>,
  key: string,
  fallback: number,
  min: number,
  max: number,
): number {
  const raw = env[key];
  if (raw === undefined || raw === "") return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new Error(`${key} must be an integer in [${min}, ${max}], got "${raw}"`);
  }
  return value;
}
