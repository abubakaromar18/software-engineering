import { readFile } from "node:fs/promises";

/** One word with its seed frequency, as parsed from a corpus file. */
export interface CorpusEntry {
  readonly word: string;
  readonly frequency: number;
}

/** Raised for malformed corpus input; carries the 1-based line number. */
export class CorpusParseError extends Error {
  constructor(
    message: string,
    readonly line: number,
  ) {
    super(`line ${line}: ${message}`);
    this.name = "CorpusParseError";
  }
}

/**
 * Parses a TSV corpus: `word<TAB>frequency` per line. The frequency column
 * is optional and defaults to 1. Blank lines and `#` comments are skipped.
 *
 * Parsing is pure (string in, entries out) so it can be tested without disk
 * I/O; {@link loadCorpus} is the thin I/O wrapper.
 */
export function parseCorpus(text: string): CorpusEntry[] {
  const entries: CorpusEntry[] = [];
  const lines = text.split(/\r?\n/u);
  lines.forEach((raw, index) => {
    // Only trim trailing whitespace before splitting: a leading tab marks an
    // empty word column and must not be swallowed.
    const line = raw.trimEnd();
    if (line.trim() === "" || line.trimStart().startsWith("#")) return;
    const [word = "", freqText, ...rest] = line.split("\t");
    const lineNo = index + 1;
    if (rest.length > 0) throw new CorpusParseError("expected at most 2 tab-separated columns", lineNo);
    if (word.trim() === "") throw new CorpusParseError("word is empty", lineNo);
    const frequency = freqText === undefined ? 1 : Number(freqText.trim());
    if (!Number.isSafeInteger(frequency) || frequency < 0) {
      throw new CorpusParseError(`invalid frequency "${freqText}"`, lineNo);
    }
    entries.push({ word: word.trim(), frequency });
  });
  return entries;
}

export async function loadCorpus(path: string): Promise<CorpusEntry[]> {
  return parseCorpus(await readFile(path, "utf8"));
}
