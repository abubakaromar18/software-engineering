import type { Cents } from "../shared/money.js";

export interface Parcel {
  readonly weightKg: number;
  readonly distanceKm: number;
}

export class ShippingError extends Error {
  override readonly name: string = "ShippingError";
}

/** Throws if the parcel is physically impossible. Shared so both versions validate identically. */
export function assertValidParcel(parcel: Parcel): void {
  if (!(parcel.weightKg > 0) || !Number.isFinite(parcel.weightKg)) {
    throw new ShippingError(`Weight must be a positive number of kg, got ${parcel.weightKg}`);
  }
  if (!(parcel.distanceKm >= 0) || !Number.isFinite(parcel.distanceKm)) {
    throw new ShippingError(`Distance must be a non-negative number of km, got ${parcel.distanceKm}`);
  }
}

/** Carriers bill per started kilogram. */
export const billableKg = (parcel: Parcel): number => Math.ceil(parcel.weightKg);

export type Quote = Cents;
