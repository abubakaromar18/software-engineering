import type { Handler, Middleware } from "./types.js";

/**
 * Compose middlewares into a single decorator.
 *
 * Ordering rule ("onion"): the FIRST middleware in the list is the OUTERMOST
 * layer. A request passes through the list left-to-right on the way in and the
 * response passes back right-to-left on the way out:
 *
 *   compose([a, b, c])(h)  ===  a.wrap(b.wrap(c.wrap(h)))
 *
 * This matches how the list reads top-to-bottom in code and how most
 * middleware frameworks (Koa, Express, tower) behave.
 */
export function compose<Req, Res>(
  middlewares: readonly Middleware<Req, Res>[],
): (handler: Handler<Req, Res>) => Handler<Req, Res> {
  return (handler) => middlewares.reduceRight((next, middleware) => middleware.wrap(next), handler);
}

/**
 * An immutable, fluent builder over `compose`. Each `use()` returns a new
 * pipeline, so a base pipeline can be shared and specialised safely.
 */
export class Pipeline<Req, Res> {
  private constructor(private readonly middlewares: readonly Middleware<Req, Res>[]) {}

  static create<Req, Res>(): Pipeline<Req, Res> {
    return new Pipeline<Req, Res>([]);
  }

  /** Append a middleware as the new innermost layer (closest to the handler). */
  use(middleware: Middleware<Req, Res>): Pipeline<Req, Res> {
    return new Pipeline([...this.middlewares, middleware]);
  }

  /** Wrap `handler` with every layer, outermost first. */
  build(handler: Handler<Req, Res>): Handler<Req, Res> {
    return compose(this.middlewares)(handler);
  }

  /** Human-readable layer order, e.g. "logging → retry → handler". */
  describe(): string {
    return [...this.middlewares.map((m) => m.name), "handler"].join(" → ");
  }
}
