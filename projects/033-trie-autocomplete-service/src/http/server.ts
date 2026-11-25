import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { AutocompleteService, ValidationError } from "../autocomplete-service.js";

/** Bodies above this size are rejected before parsing; the API only takes one short word. */
const MAX_BODY_BYTES = 1024;

/** An error that already knows its HTTP status; anything else becomes a 500. */
class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly headers: Record<string, string> = {},
  ) {
    super(message);
  }
}

type Handler = (req: IncomingMessage, url: URL) => Promise<Response>;

interface Response {
  readonly status: number;
  readonly body?: unknown;
}

interface Route {
  readonly method: string;
  readonly match: (path: string) => boolean;
  readonly handle: Handler;
}

export interface ServerOptions {
  /** Called for unexpected errors (500s). Defaults to console.error. */
  readonly onError?: (err: unknown) => void;
}

/**
 * Creates (but does not start) an HTTP server exposing the service.
 *
 *   GET    /health                 liveness + index size
 *   GET    /suggest?q=ty&limit=5   ranked completions
 *   POST   /select {"word":"..."}  record a pick, boosting its rank
 *   DELETE /words/:word            remove a word
 *
 * Uses only node:http to keep the project dependency-free; the tiny routing
 * table below is all a four-endpoint API needs.
 */
export function createAutocompleteServer(service: AutocompleteService, options: ServerOptions = {}): Server {
  const onError = options.onError ?? ((err: unknown) => console.error(err));

  const routes: Route[] = [
    {
      method: "GET",
      match: (p) => p === "/health",
      handle: async () => ({ status: 200, body: { status: "ok", words: service.size } }),
    },
    {
      method: "GET",
      match: (p) => p === "/suggest",
      handle: async (_req, url) => {
        const q = url.searchParams.get("q") ?? "";
        const suggestions = service.suggest(q, parseLimit(url.searchParams.get("limit")));
        return { status: 200, body: { query: q, suggestions } };
      },
    },
    {
      method: "POST",
      match: (p) => p === "/select",
      handle: async (req) => {
        const body = await readJson(req);
        const word = isRecord(body) ? body["word"] : undefined;
        if (typeof word !== "string") throw new ValidationError('body must be {"word": string}');
        return { status: 200, body: service.recordSelection(word) };
      },
    },
    {
      method: "DELETE",
      match: (p) => p.startsWith("/words/") && p.length > "/words/".length,
      handle: async (_req, url) => {
        const word = decodePathSegment(url.pathname.slice("/words/".length));
        if (!service.remove(word)) throw new HttpError(404, `word not found: ${word}`);
        return { status: 204 };
      },
    },
  ];

  return createServer((req, res) => {
    void dispatch(routes, req, res, onError);
  });
}

async function dispatch(
  routes: readonly Route[],
  req: IncomingMessage,
  res: ServerResponse,
  onError: (err: unknown) => void,
): Promise<void> {
  try {
    const url = new URL(req.url ?? "/", "http://localhost");
    const candidates = routes.filter((r) => r.match(url.pathname));
    if (candidates.length === 0) throw new HttpError(404, "not found");
    const route = candidates.find((r) => r.method === req.method);
    if (!route) {
      const allow = candidates.map((r) => r.method).join(", ");
      throw new HttpError(405, "method not allowed", { Allow: allow });
    }
    send(res, await route.handle(req, url));
  } catch (err) {
    if (err instanceof HttpError) {
      send(res, { status: err.status, body: { error: err.message } }, err.headers);
    } else if (err instanceof ValidationError) {
      send(res, { status: 400, body: { error: err.message } });
    } else {
      onError(err);
      // Never leak internals (stack traces, paths) to clients.
      send(res, { status: 500, body: { error: "internal server error" } });
    }
  }
}

function send(res: ServerResponse, { status, body }: Response, headers: Record<string, string> = {}): void {
  if (body === undefined) {
    res.writeHead(status, headers).end();
    return;
  }
  const payload = JSON.stringify(body);
  res
    .writeHead(status, {
      ...headers,
      "Content-Type": "application/json; charset=utf-8",
      "Content-Length": Buffer.byteLength(payload),
    })
    .end(payload);
}

function parseLimit(raw: string | null): number | undefined {
  if (raw === null || raw === "") return undefined;
  if (!/^\d+$/u.test(raw)) throw new ValidationError("limit must be a positive integer");
  return Number(raw);
}

function decodePathSegment(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    throw new ValidationError("malformed percent-encoding in path");
  }
}

async function readJson(req: IncomingMessage): Promise<unknown> {
  const type = req.headers["content-type"] ?? "";
  if (!type.toLowerCase().startsWith("application/json")) {
    throw new HttpError(415, "content-type must be application/json");
  }
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    // Stop buffering as soon as the limit is crossed rather than after the fact.
    if (size > MAX_BODY_BYTES) throw new HttpError(413, `body exceeds ${MAX_BODY_BYTES} bytes`, { Connection: "close" });
    chunks.push(chunk as Buffer);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new ValidationError("body is not valid JSON");
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
