import { describeError } from "../core/errors.js";
import type { Middleware } from "../core/types.js";

export type LogLevel = "info" | "error";

/** Minimal structured-logger port; adapt pino/winston/console to it. */
export interface Logger {
  log(level: LogLevel, message: string, fields: Readonly<Record<string, unknown>>): void;
}

export interface LoggingOptions<Req> {
  logger: Logger;
  /** Prefix that identifies this layer in log output. */
  label?: string;
  /** Turn a request into loggable fields. Defaults to logging nothing, so payloads are never leaked by accident. */
  describeRequest?: (request: Req) => Readonly<Record<string, unknown>>;
}

/**
 * Logs one "start" line per call and one "ok"/"failed" line per outcome.
 * Errors are logged and then re-thrown unchanged: observation must never
 * alter behaviour.
 */
export function logging<Req, Res>(options: LoggingOptions<Req>): Middleware<Req, Res> {
  const { logger, label = "call", describeRequest = () => ({}) } = options;
  return {
    name: "logging",
    wrap: (next) => async (request) => {
      const fields = describeRequest(request);
      logger.log("info", `${label} start`, fields);
      try {
        const response = await next(request);
        logger.log("info", `${label} ok`, fields);
        return response;
      } catch (error) {
        logger.log("error", `${label} failed`, { ...fields, error: describeError(error) });
        throw error;
      }
    },
  };
}

/** Adapter from the Logger port to the console, used by the demo. */
export const consoleLogger: Logger = {
  log(level, message, fields) {
    const line = Object.keys(fields).length > 0 ? `${message} ${JSON.stringify(fields)}` : message;
    (level === "error" ? console.error : console.log)(`[${level}] ${line}`);
  },
};
