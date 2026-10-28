// Clean domain code: every business number has a name.
const FREE_SHIPPING_THRESHOLD = 50;
const SHIPPING_FEE = 4.99;

export function shippingFor(subtotal) {
  return subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_FEE;
}
