// End-to-end demo against a running provider:
//   (cd ../provider && CATALOG_API_TOKEN=dev-token python -m catalog_api)
//   CATALOG_API_TOKEN=dev-token npm run demo
import { CatalogClient, ProductNotFoundError, checkout, priceCart } from '../src/index.js';

const client = new CatalogClient({
  baseUrl: process.env.CATALOG_API_URL ?? 'http://127.0.0.1:8000',
  token: process.env.CATALOG_API_TOKEN ?? 'dev-token',
});

const books = await client.listProducts({ category: 'books' });
console.log('Books:');
for (const book of books) console.log(`  ${book.id}  ${book.price.format().padStart(8)}  ${book.name}`);

const cart = [
  { productId: 'P-100', quantity: 1 },
  { productId: 'P-101', quantity: 2 },
];
const priced = await priceCart(client, cart);
console.log(`\nCart total: ${priced.total.format()} (can checkout: ${priced.canCheckout})`);

const receipt = await checkout(client, cart);
console.log(`Order ${receipt.orderId} placed for ${receipt.total} at ${receipt.placedAt.toISOString()}`);

try {
  await client.getProduct('P-999');
} catch (err) {
  if (!(err instanceof ProductNotFoundError)) throw err;
  console.log(`\nLookup of P-999 -> ${err.name}: ${err.message}`);
}
