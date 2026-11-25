/**
 * Canonicalises user input before it touches the trie, so "TypeScript ",
 * "typescript" and "ＴｙｐｅＳｃｒｉｐｔ" (full-width) all hit the same path.
 *
 * NFKC folds compatibility characters; toLocaleLowerCase("en-US") keeps the
 * result independent of the server's locale (e.g. the Turkish dotless i).
 * Internal runs of whitespace collapse to one space so phrases still work.
 */
export function normalize(input: string): string {
  return input.normalize("NFKC").toLocaleLowerCase("en-US").trim().replace(/\s+/gu, " ");
}
