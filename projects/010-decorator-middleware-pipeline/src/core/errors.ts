/** Thrown when a middleware factory receives invalid options. Fails fast at build time. */
export class ConfigError extends Error {
  override readonly name = "ConfigError";
}

/**
 * Thrown by the retry middleware when every attempt failed. The final error is
 * kept as `cause` (standard ES2022 error chaining) and every attempt's error is
 * available for diagnostics.
 */
export class RetryExhaustedError extends Error {
  override readonly name = "RetryExhaustedError";

  constructor(
    readonly attempts: number,
    readonly errors: readonly unknown[],
  ) {
    super(`All ${attempts} attempt(s) failed: ${describeError(errors.at(-1))}`, {
      cause: errors.at(-1),
    });
  }
}

export function describeError(error: unknown): string {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}
