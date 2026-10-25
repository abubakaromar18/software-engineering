/**
 * Money is modelled as an integer number of cents throughout the project so
 * that arithmetic is exact. Formatting is the only place cents become dollars.
 */
export type Cents = number;

/** Throws if `value` is not a non-negative safe integer number of cents. */
export function assertCents(value: number, label: string): void {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new RangeError(`${label} must be a non-negative integer number of cents, got ${value}`);
  }
}

/** Formats cents as US dollars, e.g. 123456 -> "$1,234.56". */
export function formatCents(cents: Cents): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const dollars = Math.floor(abs / 100).toLocaleString("en-US");
  const remainder = String(abs % 100).padStart(2, "0");
  return `${sign}$${dollars}.${remainder}`;
}
