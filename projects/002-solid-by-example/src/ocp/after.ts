/**
 * OCP — AFTER.
 *
 * Each method is a ShippingRate strategy. ShippingCalculator looks rates up by
 * name and never needs to change when a carrier adds a service: new behaviour
 * arrives as a new object passed to register() (see the "drone" test).
 *
 * Trade-off: the full price list is no longer visible in one place. That is
 * acceptable here because rates are independent of each other; if they started
 * sharing rules (e.g. a global surcharge), a decorator would keep them closed.
 */
import { assertValidParcel, billableKg, ShippingError, type Parcel, type Quote } from "./types.js";

export interface ShippingRate {
  readonly method: string;
  /** Called only with a parcel that has already been validated. */
  quote(parcel: Parcel): Quote;
}

export const standardRate: ShippingRate = {
  method: "standard",
  quote: (parcel) => 500 + 100 * billableKg(parcel),
};

export const expressRate: ShippingRate = {
  method: "express",
  quote: (parcel) => 1200 + 150 * billableKg(parcel) + 100 * Math.ceil(parcel.distanceKm / 100),
};

export const overnightRate: ShippingRate = {
  method: "overnight",
  quote: (parcel) => {
    if (parcel.distanceKm > 1000) {
      throw new ShippingError("Overnight shipping is limited to 1000 km");
    }
    return 3000 + 300 * billableKg(parcel);
  },
};

export const defaultRates: readonly ShippingRate[] = [standardRate, expressRate, overnightRate];

export class ShippingCalculator {
  private readonly rates = new Map<string, ShippingRate>();

  constructor(rates: readonly ShippingRate[] = defaultRates) {
    rates.forEach((rate) => this.register(rate));
  }

  /** The extension point: add behaviour without modifying this class. */
  register(rate: ShippingRate): this {
    if (this.rates.has(rate.method)) {
      throw new ShippingError(`Shipping method already registered: ${rate.method}`);
    }
    this.rates.set(rate.method, rate);
    return this;
  }

  cost(method: string, parcel: Parcel): Quote {
    assertValidParcel(parcel);
    const rate = this.rates.get(method);
    if (!rate) throw new ShippingError(`Unknown shipping method: ${method}`);
    return rate.quote(parcel);
  }

  availableMethods(): string[] {
    return [...this.rates.keys()];
  }
}
