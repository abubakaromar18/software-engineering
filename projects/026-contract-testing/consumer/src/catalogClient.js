import { CatalogError, OutOfStockError, ProductNotFoundError, UnauthorizedError } from './errors.js';
import { Money } from './money.js';

/**
 * HTTP client for the Catalog API.
 *
 * This is the code under test in the Pact suite: every field read here is a
 * field the contract asks the provider to keep. Fields the storefront doesn't
 * read (e.g. `warehouseLocation`) are deliberately ignored so the provider is
 * free to change them.
 */
export class CatalogClient {
  /**
   * @param {object} options
   * @param {string} options.baseUrl   e.g. "http://localhost:8000"
   * @param {string} options.token     bearer token for the Authorization header
   * @param {typeof fetch} [options.fetch] injectable for tests
   */
  constructor({ baseUrl, token, fetch: fetchImpl = globalThis.fetch }) {
    if (!baseUrl) throw new TypeError('baseUrl is required');
    if (!token) throw new TypeError('token is required');
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.token = token;
    this.fetch = fetchImpl;
  }

  async getProduct(id) {
    const body = await this.#request('GET', `/products/${encodeURIComponent(id)}`);
    return toProduct(body);
  }

  async listProducts({ category } = {}) {
    const query = category ? `?${new URLSearchParams({ category })}` : '';
    const body = await this.#request('GET', `/products${query}`);
    return body.items.map(toProduct);
  }

  /** @param {{productId: string, quantity: number}[]} items */
  async placeOrder(items) {
    const body = await this.#request('POST', '/orders', { items });
    return {
      id: body.id,
      status: body.status,
      total: new Money(body.totalCents, body.currency),
      createdAt: new Date(body.createdAt),
    };
  }

  async #request(method, path, payload) {
    const headers = { Accept: 'application/json', Authorization: `Bearer ${this.token}` };
    if (payload !== undefined) headers['Content-Type'] = 'application/json';

    const response = await this.fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: payload === undefined ? undefined : JSON.stringify(payload),
    });
    const body = await response.json().catch(() => null);
    if (response.ok) return body;
    throw toError(response.status, body);
  }
}

function toProduct(body) {
  return {
    id: body.id,
    name: body.name,
    price: new Money(body.priceCents, body.currency),
    inStock: body.inStock,
  };
}

const ERRORS_BY_CODE = {
  NOT_FOUND: ProductNotFoundError,
  INSUFFICIENT_STOCK: OutOfStockError,
  UNAUTHORIZED: UnauthorizedError,
};

function toError(status, body) {
  const code = body?.error?.code;
  const message = body?.error?.message ?? `Catalog API responded with HTTP ${status}`;
  const ErrorType = ERRORS_BY_CODE[code] ?? CatalogError;
  return new ErrorType(message, { status, code });
}
