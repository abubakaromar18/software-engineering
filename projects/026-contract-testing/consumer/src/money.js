/**
 * Integer minor units avoid floating-point drift (0.1 + 0.2 !== 0.3).
 * The contract pins `priceCents` as an integer precisely so this holds.
 */
export class Money {
  constructor(cents, currency) {
    if (!Number.isInteger(cents)) throw new TypeError(`cents must be an integer, got ${cents}`);
    if (!/^[A-Z]{3}$/.test(currency)) throw new TypeError(`invalid ISO-4217 currency: ${currency}`);
    this.cents = cents;
    this.currency = currency;
    Object.freeze(this);
  }

  static zero(currency) {
    return new Money(0, currency);
  }

  add(other) {
    if (other.currency !== this.currency) {
      throw new TypeError(`cannot add ${other.currency} to ${this.currency}`);
    }
    return new Money(this.cents + other.cents, this.currency);
  }

  times(quantity) {
    return new Money(this.cents * quantity, this.currency);
  }

  format(locale = 'en-US') {
    return new Intl.NumberFormat(locale, { style: 'currency', currency: this.currency }).format(
      this.cents / 100,
    );
  }
}
