import { describe, expect, it } from "vitest";
import { CorpusParseError, parseCorpus } from "../src/corpus.js";
import { DEFAULT_CONFIG, loadConfig } from "../src/config.js";
import { normalize } from "../src/normalize.js";

describe("parseCorpus", () => {
  it("parses words, defaults frequency, skips comments and blanks", () => {
    const text = "# header\n\ntrie\t7\r\ntree\n  heap\t0  \n";
    expect(parseCorpus(text)).toEqual([
      { word: "trie", frequency: 7 },
      { word: "tree", frequency: 1 },
      { word: "heap", frequency: 0 },
    ]);
  });

  it.each([
    ["a\tb", /line 1: invalid frequency/],
    ["ok\t1\nbad\t-3", /line 2: invalid frequency/],
    ["a\t1\textra", /at most 2/],
    ["\t5", /word is empty/],
  ])("rejects %j", (text, message) => {
    expect(() => parseCorpus(text)).toThrow(CorpusParseError);
    expect(() => parseCorpus(text)).toThrow(message);
  });
});

describe("normalize", () => {
  it("lowercases, trims, collapses whitespace and folds width", () => {
    expect(normalize("  Type   Script ")).toBe("type script");
    expect(normalize("ＴＹＰＥ")).toBe("type");
    expect(normalize("İSTANBUL")).toBe("i̇stanbul"); // locale-independent lowering
  });
});

describe("loadConfig", () => {
  it("uses defaults for an empty environment", () => {
    expect(loadConfig({})).toEqual(DEFAULT_CONFIG);
  });

  it("reads overrides", () => {
    const cfg = loadConfig({ PORT: "8080", HOST: "0.0.0.0", MAX_LIMIT: "20", CORPUS_PATH: "x.tsv" });
    expect(cfg).toMatchObject({ port: 8080, host: "0.0.0.0", maxLimit: 20, corpusPath: "x.tsv" });
  });

  it.each(["abc", "-1", "70000", "1.5"])("rejects PORT=%s", (port) => {
    expect(() => loadConfig({ PORT: port })).toThrow(/PORT must be an integer/);
  });
});
