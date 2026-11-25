import { describe, expect, it } from "vitest";
import { Trie } from "../src/trie.js";

function trieOf(entries: Record<string, number>): Trie {
  const t = new Trie();
  for (const [w, f] of Object.entries(entries)) t.insert(w, f);
  return t;
}

describe("Trie", () => {
  it("stores words and reports membership and size", () => {
    const t = trieOf({ car: 1, cart: 2, care: 3 });
    expect(t.size).toBe(3);
    expect(t.has("cart")).toBe(true);
    expect(t.has("ca")).toBe(false); // prefix, not a word
    expect(t.has("cars")).toBe(false);
    expect(t.hasPrefix("ca")).toBe(true);
    expect(t.hasPrefix("dog")).toBe(false);
  });

  it("insert replaces frequency without changing size", () => {
    const t = trieOf({ car: 1 });
    t.insert("car", 9);
    expect(t.size).toBe(1);
    expect(t.frequencyOf("car")).toBe(9);
  });

  it("increment adds to an existing word or creates a new one", () => {
    const t = trieOf({ car: 4 });
    expect(t.increment("car")).toBe(5);
    expect(t.increment("cat", 3)).toBe(3);
    expect(t.size).toBe(2);
  });

  it("ranks completions by frequency, ties broken alphabetically", () => {
    const t = trieOf({ tea: 5, ten: 9, ted: 5, tent: 1, to: 50 });
    expect(t.complete("te").map((c) => c.word)).toEqual(["ten", "tea", "ted", "tent"]);
  });

  it("includes the prefix itself when it is a word", () => {
    const t = trieOf({ test: 1, testing: 2 });
    expect(t.complete("test")).toEqual([
      { word: "testing", frequency: 2 },
      { word: "test", frequency: 1 },
    ]);
  });

  it("respects the limit and keeps the best k", () => {
    const t = new Trie();
    for (let i = 0; i < 100; i++) t.insert(`w${i}`, i);
    const top = t.complete("w", 3);
    expect(top.map((c) => c.frequency)).toEqual([99, 98, 97]);
    expect(t.complete("w", 0)).toEqual([]);
  });

  it("returns nothing for an unknown prefix and rejects a bad limit", () => {
    const t = trieOf({ a: 1 });
    expect(t.complete("zz")).toEqual([]);
    expect(() => t.complete("a", -1)).toThrow(RangeError);
    expect(() => t.complete("a", 1.5)).toThrow(RangeError);
  });

  it("deletes words and prunes dead branches", () => {
    const t = trieOf({ car: 1, cart: 2 });
    expect(t.delete("cart")).toBe(true);
    expect(t.has("cart")).toBe(false);
    expect(t.has("car")).toBe(true);
    expect(t.hasPrefix("cart")).toBe(false); // the 't' node was pruned
    expect(t.delete("cart")).toBe(false);
    expect(t.delete("ca")).toBe(false); // prefix only
    expect(t.delete("car")).toBe(true);
    expect(t.size).toBe(0);
    expect(t.hasPrefix("")).toBe(false);
  });

  it("deleting a prefix word keeps longer words", () => {
    const t = trieOf({ car: 1, cart: 2 });
    t.delete("car");
    expect(t.complete("c")).toEqual([{ word: "cart", frequency: 2 }]);
  });

  it("treats astral code points as a single character", () => {
    const t = trieOf({ "🍕pizza": 2, "🍕pasta": 1 });
    expect(t.complete("🍕").map((c) => c.word)).toEqual(["🍕pizza", "🍕pasta"]);
    expect(t.delete("🍕pizza")).toBe(true);
    expect(t.has("🍕pasta")).toBe(true);
  });

  it("validates input", () => {
    const t = new Trie();
    expect(() => t.insert("")).toThrow(RangeError);
    expect(() => t.insert("a", -1)).toThrow(RangeError);
    expect(() => t.increment("a", 0.5)).toThrow(RangeError);
  });

  it("enumerates all entries", () => {
    const t = trieOf({ b: 2, a: 1, ab: 3 });
    expect([...t.entries()].sort((x, y) => x.word.localeCompare(y.word))).toEqual([
      { word: "a", frequency: 1 },
      { word: "ab", frequency: 3 },
      { word: "b", frequency: 2 },
    ]);
  });

  it("matches a brute-force reference on random data", () => {
    // Deterministic LCG so the test is reproducible.
    let seed = 42;
    const rand = (n: number): number => (seed = (seed * 1_103_515_245 + 12_345) % 2 ** 31) % n;
    const words = new Map<string, number>();
    const t = new Trie();
    for (let i = 0; i < 2_000; i++) {
      const w = Array.from({ length: 1 + rand(6) }, () => "abc"[rand(3)]).join("");
      const f = rand(100);
      words.set(w, f);
      t.insert(w, f);
    }
    for (const prefix of ["", "a", "ab", "cab", "bbb"]) {
      const expected = [...words]
        .filter(([w]) => w.startsWith(prefix))
        .map(([word, frequency]) => ({ word, frequency }))
        .sort((x, y) => y.frequency - x.frequency || (x.word < y.word ? -1 : 1))
        .slice(0, 7);
      expect(t.complete(prefix, 7)).toEqual(expected);
    }
  });
});
