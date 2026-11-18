/**
 * Consumer contract tests.
 *
 * Each test (1) registers an expected request/response with the Pact mock
 * server, (2) exercises the *real* CatalogClient against that mock, and
 * (3) on success records the interaction in ../pacts/storefront-catalog-api.json.
 * That file is the contract the Python provider must satisfy.
 *
 * Matchers express *shape*, not exact values ("an integer", "an ISO currency
 * code"), so the provider can return different data without breaking us -
 * but literal values (status "PENDING", error codes) are pinned because the
 * client branches on them.
 */
import assert from 'node:assert/strict';
import { rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { before, describe, test } from 'node:test';
import { fileURLToPath } from 'node:url';

import { MatchersV3, PactV4 } from '@pact-foundation/pact';

import { CatalogClient } from '../src/catalogClient.js';
import { OutOfStockError, ProductNotFoundError } from '../src/errors.js';

const { boolean, eachLike, integer, regex, string } = MatchersV3;

const PACT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'pacts');
const CONSUMER = 'storefront';
const PROVIDER = 'catalog-api';

const pact = new PactV4({ consumer: CONSUMER, provider: PROVIDER, dir: PACT_DIR, logLevel: 'warn' });

// Shared building blocks keep every interaction consistent.
const authHeader = { Authorization: regex('^Bearer \\S+$', 'Bearer example-token') };
const jsonHeaders = { 'Content-Type': regex('^application/json', 'application/json') };
const currency = regex('^[A-Z]{3}$', 'USD');

const productShape = (id) => ({
  id: string(id),
  name: string('Designing Data-Intensive Applications'),
  priceCents: integer(4599),
  currency,
  inStock: boolean(true),
});

const errorShape = (code) => ({ error: { code, message: string('human readable detail') } });

const clientFor = (mockServer) => new CatalogClient({ baseUrl: mockServer.url, token: 'example-token' });

before(() => {
  // Start from a clean contract so removed interactions don't linger in the file.
  rmSync(join(PACT_DIR, `${CONSUMER}-${PROVIDER}.json`), { force: true });
});

describe('CatalogClient <-> catalog-api contract', () => {
  test('fetches a product by id', async () => {
    await pact
      .addInteraction()
      .given('a product with id exists', { id: 'P-100' })
      .uponReceiving('a request for product P-100')
      .withRequest('GET', '/products/P-100', (req) => req.headers(authHeader))
      .willRespondWith(200, (res) => res.headers(jsonHeaders).jsonBody(productShape('P-100')))
      .executeTest(async (mockServer) => {
        const product = await clientFor(mockServer).getProduct('P-100');

        assert.equal(product.id, 'P-100');
        assert.equal(product.price.cents, 4599);
        assert.equal(product.price.format(), '$45.99');
        assert.equal(product.inStock, true);
      });
  });

  test('maps a 404 to ProductNotFoundError', async () => {
    await pact
      .addInteraction()
      .given('no product with id exists', { id: 'P-999' })
      .uponReceiving('a request for a product that does not exist')
      .withRequest('GET', '/products/P-999', (req) => req.headers(authHeader))
      .willRespondWith(404, (res) => res.headers(jsonHeaders).jsonBody(errorShape('NOT_FOUND')))
      .executeTest(async (mockServer) => {
        await assert.rejects(clientFor(mockServer).getProduct('P-999'), (err) => {
          assert.ok(err instanceof ProductNotFoundError);
          assert.equal(err.status, 404);
          return true;
        });
      });
  });

  test('lists products in a category', async () => {
    await pact
      .addInteraction()
      .given('products exist in category', { category: 'books' })
      .uponReceiving('a request for products in the books category')
      .withRequest('GET', '/products', (req) => req.headers(authHeader).query({ category: 'books' }))
      .willRespondWith(200, (res) =>
        // eachLike(template, min): "at least one item shaped like this".
        res.headers(jsonHeaders).jsonBody({ items: eachLike(productShape('P-100'), 1) }),
      )
      .executeTest(async (mockServer) => {
        const products = await clientFor(mockServer).listProducts({ category: 'books' });

        assert.ok(products.length >= 1);
        assert.equal(products[0].price.currency, 'USD');
      });
  });

  test('places an order', async () => {
    await pact
      .addInteraction()
      .given('a product with id exists', { id: 'P-100' })
      .uponReceiving('a request to order two of P-100')
      .withRequest('POST', '/orders', (req) =>
        req
          .headers({ ...authHeader, 'Content-Type': 'application/json' })
          .jsonBody({ items: [{ productId: 'P-100', quantity: 2 }] }),
      )
      .willRespondWith(201, (res) =>
        res.headers(jsonHeaders).jsonBody({
          id: regex('^ORD-[0-9A-F]{8}$', 'ORD-0000002A'),
          status: 'PENDING',
          totalCents: integer(9198),
          currency,
          createdAt: regex('^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$', '2026-11-18T15:30:00Z'),
        }),
      )
      .executeTest(async (mockServer) => {
        const order = await clientFor(mockServer).placeOrder([{ productId: 'P-100', quantity: 2 }]);

        assert.match(order.id, /^ORD-/);
        assert.equal(order.status, 'PENDING');
        assert.equal(order.total.format(), '$91.98');
        assert.equal(order.createdAt.toISOString(), '2026-11-18T15:30:00.000Z');
      });
  });

  test('maps a 409 to OutOfStockError', async () => {
    await pact
      .addInteraction()
      .given('a product has limited stock', { id: 'P-100', stock: 1 })
      .uponReceiving('a request to order more of P-100 than is in stock')
      .withRequest('POST', '/orders', (req) =>
        req
          .headers({ ...authHeader, 'Content-Type': 'application/json' })
          .jsonBody({ items: [{ productId: 'P-100', quantity: 3 }] }),
      )
      .willRespondWith(409, (res) => res.headers(jsonHeaders).jsonBody(errorShape('INSUFFICIENT_STOCK')))
      .executeTest(async (mockServer) => {
        await assert.rejects(
          clientFor(mockServer).placeOrder([{ productId: 'P-100', quantity: 3 }]),
          OutOfStockError,
        );
      });
  });
});
