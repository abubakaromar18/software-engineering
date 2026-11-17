// Prints a worked invoice using the compiled library (run `npm run example`).
import { calculateInvoice } from "../dist/index.js";

const invoice = calculateInvoice(
  [
    { sku: "PEN-BLUE", unitPriceCents: 150, quantity: 20 },
    { sku: "NOTEBOOK", unitPriceCents: 499, quantity: 3, category: "reduced" },
    { sku: "APPLE", unitPriceCents: 80, quantity: 5, category: "food" },
  ],
  {
    issuedOn: "2026-11-17",
    tiers: [
      { minQuantity: 10, basisPoints: 500 },
      { minQuantity: 50, basisPoints: 1000 },
    ],
    coupon: { code: "WELCOME10", kind: { type: "percent", basisPoints: 1000 }, minSpendCents: 1000 },
  },
);

const pad = (s, n) => String(s).padEnd(n);
const amt = (m) => m.format().padStart(11);
console.log(pad("SKU", 10), pad("QTY", 4), pad("CAT", 9), "     GROSS", "     VOLUME", "     COUPON", "        TAX", "      TOTAL");
for (const l of invoice.lines) {
  console.log(pad(l.sku, 10), pad(l.quantity, 4), pad(l.category, 9), amt(l.gross), amt(l.volumeDiscount), amt(l.couponDiscount), amt(l.tax), amt(l.total));
}
console.log();
console.log("Gross     ", amt(invoice.gross));
console.log("Volume    ", amt(invoice.volumeDiscount));
console.log("Subtotal  ", amt(invoice.subtotal));
console.log(`Coupon     ${amt(invoice.couponDiscount)}  (${invoice.appliedCoupon ?? invoice.couponRejection ?? "none"})`);
console.log("Tax       ", amt(invoice.tax));
console.log("TOTAL     ", amt(invoice.total));
