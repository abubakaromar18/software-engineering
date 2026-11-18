/**
 * Typed errors so callers can branch on *what* went wrong, not on HTTP codes.
 * The mapping from the provider's `{ error: { code } }` envelope lives in
 * catalogClient.js - the only place that knows about the wire format.
 */

export class CatalogError extends Error {
  constructor(message, { status, code } = {}) {
    super(message);
    this.name = this.constructor.name;
    this.status = status;
    this.code = code;
  }
}

export class ProductNotFoundError extends CatalogError {}

export class OutOfStockError extends CatalogError {}

export class UnauthorizedError extends CatalogError {}
