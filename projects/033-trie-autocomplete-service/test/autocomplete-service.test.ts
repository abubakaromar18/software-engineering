import { beforeEach, describe, expect, it } from "vitest";
import { AutocompleteService, ValidationError } from "../src/autocomplete-service.js";

const options = { defaultLimit: 3, maxLimit: 5, maxQueryLength: 10 };

describe("AutocompleteService", () => {
  let service: AutocompleteService;

  beforeEach(() => {
    service = new AutocompleteService(options);
    service.load([
      { word: "Type", frequency: 10 },
      { word: "typescript", frequency: 30 },
      { word: "typed", frequency: 5 },
      { word: "typeof", frequency: 8 },
      { word: "tree", frequency: 50 },
    ]);
  });

  it("normalises queries and applies the default limit", () => {
    expect(service.suggest("  TY ").map((s) => s.word)).toEqual(["typescript", "type", "typeof"]);
  });

  it("caps limit at maxLimit and validates it", () => {
    expect(service.suggest("t", 100)).toHaveLength(5);
    expect(() => service.suggest("t", 0)).toThrow(ValidationError);
  });

  it("returns nothing for an empty query instead of dumping the index", () => {
    expect(service.suggest("   ")).toEqual([]);
  });

  it("rejects over-long input", () => {
    expect(() => service.suggest("x".repeat(11))).toThrow(/exceeds 10/);
  });

  it("merges duplicates that normalise to the same key", () => {
    service.load([{ word: "TREE", frequency: 5 }]);
    expect(service.suggest("tree")).toEqual([{ word: "tree", frequency: 55 }]);
  });

  it("learns from selections so picks rise in the ranking", () => {
    for (let i = 0; i < 25; i++) service.recordSelection("typed");
    expect(service.suggest("type")[0]).toEqual({ word: "typed", frequency: 30 });
    expect(service.suggest("typ").map((s) => s.word)).toEqual(["typed", "typescript", "type"]);
  });

  it("learns brand-new words and rejects empty selections", () => {
    expect(service.recordSelection("Tuple")).toEqual({ word: "tuple", frequency: 1 });
    expect(() => service.recordSelection("  ")).toThrow(ValidationError);
  });

  it("removes words", () => {
    expect(service.remove("TREE")).toBe(true);
    expect(service.remove("tree")).toBe(false);
    expect(service.size).toBe(4);
  });

  it("rejects inconsistent options", () => {
    expect(() => new AutocompleteService({ ...options, defaultLimit: 6 })).toThrow(RangeError);
  });
});
