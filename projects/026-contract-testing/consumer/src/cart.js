import { Money } from './money.js';

/**
 * Storefront use cases built on top of CatalogClient. They depend only on the
 * client's *domain* interface (Money, plain objects, typed errors), so they are
 * unit-tested with a hand-written fake - no HTTP, no Pact.
 */

/**
 * Price a cart for display.
 * @param {{getProduct(id: string): Promise<{id, name, price: Money, inStock: boolean}>}} catalog
 * @param {{productId: string, quantity: number}[]} lines
 */
export async function priceCart(catalog, lines) {
  if (lines.length === 0) throw new RangeError('cart is empty');
  const products = await Promise.all(lines.map((line) => catalog.getProduct(line.productId)));

  const priced = lines.map((line, i) => {
    const product = products[i];
    return {
      productId: product.id,
      name: product.name,
      quantity: line.quantity,
      unitPrice: product.price,
      lineTotal: product.price.times(line.quantity),
      available: product.inStock,
    };
  });
  const total = priced.reduce((sum, line) => sum.add(line.lineTotal), Money.zero(priced[0].unitPrice.currency));
  return { lines: priced, total, canCheckout: priced.every((line) => line.available) };
}

/**
 * Price the cart, refuse to submit if anything is unavailable, then place the order.
 * @returns {Promise<{orderId: string, total: string, placedAt: Date}>}
 */
export async function checkout(catalog, lines) {
  const cart = await priceCart(catalog, lines);
  if (!cart.canCheckout) {
    const missing = cart.lines.filter((line) => !line.available).map((line) => line.name);
    throw new RangeError(`unavailable: ${missing.join(', ')}`);
  }
  const order = await catalog.placeOrder(
    lines.map(({ productId, quantity }) => ({ productId, quantity })),
  );
  return { orderId: order.id, total: order.total.format(), placedAt: order.createdAt };
}
