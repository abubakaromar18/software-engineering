/**
 * A handler is the unit everything in this library decorates: an async
 * function from a request to a response. Services, HTTP clients and
 * repository calls can all be adapted to this shape.
 */
export type Handler<Req, Res> = (request: Req) => Promise<Res>;

/**
 * A middleware is a decorator over handlers: it receives the next handler in
 * the chain and returns a new handler with the same signature. Because the
 * signature is preserved, middlewares can be stacked in any order.
 *
 * The `name` is only used for introspection (`Pipeline.describe()`), logs and
 * error messages; it has no effect on behaviour.
 */
export interface Middleware<Req, Res> {
  readonly name: string;
  wrap(next: Handler<Req, Res>): Handler<Req, Res>;
}
