/**
 * OCP — BEFORE.
 *
 * Every shipping method lives in one switch. Adding a method means editing
 * (and re-testing) this function, and every new branch makes the next edit
 * riskier. The set of methods is closed to extension and open to modification:
 * the exact opposite of what the principle asks for.
 */
import { assertValidParcel, billableKg, ShippingError, type Parcel, type Quote } from "./types.js";

export function shippingCost(method: string, parcel: Parcel): Quote {
  assertValidParcel(parcel);
  const kg = billableKg(parcel);
  switch (method) {
    case "standard":
      return 500 + 100 * kg;
    case "express":
      return 1200 + 150 * kg + 100 * Math.ceil(parcel.distanceKm / 100);
    case "overnight":
      if (parcel.distanceKm > 1000) {
        throw new ShippingError("Overnight shipping is limited to 1000 km");
      }
      return 3000 + 300 * kg;
    default:
      throw new ShippingError(`Unknown shipping method: ${method}`);
  }
}

export function availableMethods(): string[] {
  return ["standard", "express", "overnight"];
}
