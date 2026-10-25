import { describe, expect, it } from "vitest";
import * as before from "../src/ocp/before.js";
import * as after from "../src/ocp/after.js";
import { billableKg, ShippingError, type Parcel } from "../src/ocp/types.js";

type Cost = (method: string, parcel: Parcel) => number;
const versions: [string, () => Cost][] = [
  ["before", () => before.shippingCost],
  ["after", () => {
    const calculator = new after.ShippingCalculator();
    return (method, parcel) => calculator.cost(method, parcel);
  }],
];

const parcels: Parcel[] = [
  { weightKg: 0.1, distanceKm: 0 },
  { weightKg: 1, distanceKm: 99 },
  { weightKg: 1.01, distanceKm: 100 },
  { weightKg: 2.5, distanceKm: 101 },
  { weightKg: 20, distanceKm: 1000 },
  { weightKg: 20, distanceKm: 1001 },
  { weightKg: 75, distanceKm: 4200 },
];
const methods = ["standard", "express", "overnight", "teleport", ""];

/** Captures either a value or an error message so outcomes can be compared. */
function outcome(cost: Cost, method: string, parcel: Parcel): number | string {
  try {
    return cost(method, parcel);
  } catch (error) {
    if (!(error instanceof ShippingError)) throw error;
    return `error: ${error.message}`;
  }
}

describe("OCP parity: the strategy version quotes exactly like the switch", () => {
  const [beforeCost, afterCost] = versions.map(([, make]) => make()) as [Cost, Cost];
  const grid = methods.flatMap((m) => parcels.map((p) => [m, p] as const));

  it.each(grid)("%s %o", (method, parcel) => {
    expect(outcome(afterCost, method, parcel)).toEqual(outcome(beforeCost, method, parcel));
  });

  it.each([
    { weightKg: 0, distanceKm: 1 },
    { weightKg: -1, distanceKm: 1 },
    { weightKg: Number.NaN, distanceKm: 1 },
    { weightKg: 1, distanceKm: -5 },
    { weightKg: 1, distanceKm: Number.POSITIVE_INFINITY },
  ])("both reject invalid parcel %o", (parcel) => {
    expect(() => beforeCost("standard", parcel)).toThrow(ShippingError);
    expect(outcome(afterCost, "standard", parcel)).toEqual(outcome(beforeCost, "standard", parcel));
  });

  it("lists the same methods", () => {
    expect(new after.ShippingCalculator().availableMethods()).toEqual(before.availableMethods());
  });

  it("matches known prices", () => {
    expect(afterCost("standard", { weightKg: 2.3, distanceKm: 640 })).toBe(800);
    expect(afterCost("express", { weightKg: 2.3, distanceKm: 640 })).toBe(2350);
    expect(afterCost("overnight", { weightKg: 2.3, distanceKm: 640 })).toBe(3900);
  });
});

describe("OCP payoff: extension without modification", () => {
  // Defined entirely in the test: no source file was edited to support it.
  const drone: after.ShippingRate = {
    method: "drone",
    quote: (parcel) => {
      if (parcel.weightKg > 5 || parcel.distanceKm > 30) throw new ShippingError("Out of drone range");
      return 999 + 50 * billableKg(parcel);
    },
  };

  it("a new method is added by registering a strategy", () => {
    const calculator = new after.ShippingCalculator().register(drone);
    expect(calculator.cost("drone", { weightKg: 1.2, distanceKm: 10 })).toBe(1099);
    expect(calculator.availableMethods()).toContain("drone");
    // Existing methods are untouched.
    expect(calculator.cost("standard", { weightKg: 1, distanceKm: 1 })).toBe(600);
  });

  it("parcel validation still runs before the new strategy", () => {
    const calculator = new after.ShippingCalculator([drone]);
    expect(() => calculator.cost("drone", { weightKg: 0, distanceKm: 1 })).toThrow("Weight must be");
  });

  it("refuses to silently replace an existing method", () => {
    expect(() => new after.ShippingCalculator().register({ ...after.standardRate })).toThrow("already registered");
  });
});
