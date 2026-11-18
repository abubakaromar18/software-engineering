import assert from 'node:assert/strict';
import { describe, test } from 'node:test';

import { checkout, priceCart } from '../src/cart.js';
import { ProductNotFoundError } from '../src/errors.js';
import { Money } from '../src/money.js';

/** In-memory fake of CatalogClient's domain interface. */
class FakeCatalog {
  constructor(products) {
    this.products = new Map(products.map((p) => [p.id, p]));
    this.orders = [];
  }

  async getProduct(id) {
    const product = this.products.get(id);
    if (!product) throw new ProductNotFoundError(`no ${id}`, { status: 404, code: 'NOT_FOUND' });
    return product;
  }

  async placeOrder(items) {
    this.orders.push(items);
    const total = items.reduce(
      (sum, item) => sum.add(this.products.get(item.productId).price.times(item.quantity)),
      Money.zero('USD'),
    );
    return { id: 'ORD-00000001', status: 'PENDING', total, createdAt: new Date('2026-11-18T15:30:00Z') };
  }
}

const book = { id: 'P-1', name: 'Book', price: new Money(1500, 'USD'), inStock: true };
const pen = { id: 'P-2', name: 'Pen', price: new Money(250, 'USD'), inStock: true };
const soldOut = { id: 'P-3', name: 'Lamp', price: new Money(4000, 'USD'), inStock: false };

describe('priceCart', () => {
  test('totals line items', async () => {
    const cart = await priceCart(new FakeCatalog([book, pen]), [
      { productId: 'P-1', quantity: 2 },
      { productId: 'P-2', quantity: 3 },
    ]);
    assert.equal(cart.total.cents, 3750);
    assert.equal(cart.lines[1].lineTotal.format(), '$7.50');
    assert.equal(cart.canCheckout, true);
  });

  test('flags unavailable items', async () => {
    const cart = await priceCart(new FakeCatalog([book, soldOut]), [
      { productId: 'P-1', quantity: 1 },
      { productId: 'P-3', quantity: 1 },
    ]);
    assert.equal(cart.canCheckout, false);
  });

  test('rejects an empty cart', async () => {
    await assert.rejects(priceCart(new FakeCatalog([]), []), RangeError);
  });
});

describe('checkout', () => {
  test('places the order and returns a receipt', async () => {
    const catalog = new FakeCatalog([book]);
    const receipt = await checkout(catalog, [{ productId: 'P-1', quantity: 2 }]);

    assert.deepEqual(catalog.orders, [[{ productId: 'P-1', quantity: 2 }]]);
    assert.equal(receipt.total, '$30.00');
    assert.equal(receipt.orderId, 'ORD-00000001');
  });

  test('refuses to order unavailable items', async () => {
    const catalog = new FakeCatalog([soldOut]);
    await assert.rejects(checkout(catalog, [{ productId: 'P-3', quantity: 1 }]), /unavailable: Lamp/);
    assert.equal(catalog.orders.length, 0);
  });

  test('propagates typed client errors', async () => {
    await assert.rejects(checkout(new FakeCatalog([]), [{ productId: 'P-9', quantity: 1 }]), ProductNotFoundError);
  });
});
