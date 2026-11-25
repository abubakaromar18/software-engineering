/**
 * A prefix tree (trie) that stores words with an integer frequency.
 *
 * Each node owns a map of child characters. A node that terminates a word
 * carries that word's frequency; `undefined` means "prefix only". Keeping the
 * frequency on the node (rather than in a side table) means a single walk
 * answers both "is this a word?" and "how popular is it?".
 *
 * Children are stored in a `Map` rather than a fixed 26-slot array so the
 * trie works for any Unicode alphabet without wasting memory on sparse nodes.
 * Keys are iterated per code point (`for..of` on strings), so surrogate pairs
 * such as emoji are a single edge instead of two broken halves.
 */

/** A ranked completion returned by {@link Trie.complete}. */
export interface Completion {
  readonly word: string;
  readonly frequency: number;
}

class TrieNode {
  readonly children = new Map<string, TrieNode>();
  /** Frequency of the word ending here, or undefined if no word ends here. */
  frequency: number | undefined = undefined;

  get isWord(): boolean {
    return this.frequency !== undefined;
  }
}

/** Orders completions by frequency (desc), then alphabetically for stable ties. */
export function compareCompletions(a: Completion, b: Completion): number {
  return b.frequency - a.frequency || (a.word < b.word ? -1 : a.word > b.word ? 1 : 0);
}

export class Trie {
  private readonly root = new TrieNode();
  private wordCount = 0;

  /** Number of distinct words stored. */
  get size(): number {
    return this.wordCount;
  }

  /**
   * Inserts `word` with the given frequency, replacing any previous value.
   * @throws RangeError for an empty word or a negative / non-integer frequency.
   */
  insert(word: string, frequency = 1): void {
    assertWord(word);
    assertFrequency(frequency);
    const node = this.findOrCreate(word);
    if (!node.isWord) this.wordCount++;
    node.frequency = frequency;
  }

  /**
   * Adds `by` to the word's frequency, inserting the word if it is new.
   * Returns the updated frequency.
   */
  increment(word: string, by = 1): number {
    assertWord(word);
    assertFrequency(by);
    const node = this.findOrCreate(word);
    if (!node.isWord) {
      this.wordCount++;
      node.frequency = 0;
    }
    node.frequency = (node.frequency ?? 0) + by;
    return node.frequency;
  }

  /** Returns the stored frequency of an exact word, or undefined. */
  frequencyOf(word: string): number | undefined {
    return this.find(word)?.frequency;
  }

  has(word: string): boolean {
    return this.find(word)?.isWord ?? false;
  }

  /** True when at least one stored word starts with `prefix`. */
  hasPrefix(prefix: string): boolean {
    return this.find(prefix) !== undefined && (prefix !== "" || this.wordCount > 0);
  }

  /**
   * Removes a word. Nodes that no longer lead to any word are pruned so the
   * trie does not leak memory under insert/delete churn.
   * Returns true if the word was present.
   */
  delete(word: string): boolean {
    const chars = [...word];
    // Record the path so we can prune bottom-up without recursion.
    const path: TrieNode[] = [this.root];
    for (const ch of chars) {
      const next = path[path.length - 1]!.children.get(ch);
      if (!next) return false;
      path.push(next);
    }
    const target = path[path.length - 1]!;
    if (!target.isWord) return false;

    target.frequency = undefined;
    this.wordCount--;

    for (let i = chars.length; i > 0; i--) {
      const node = path[i]!;
      if (node.isWord || node.children.size > 0) break;
      path[i - 1]!.children.delete(chars[i - 1]!);
    }
    return true;
  }

  /**
   * Returns up to `limit` words beginning with `prefix`, most frequent first.
   *
   * Cost is O(p + m log k) where p is the prefix length, m the number of words
   * under the prefix and k the limit: we visit every completion once but only
   * keep the best k in a bounded, sorted buffer.
   */
  complete(prefix: string, limit = 10): Completion[] {
    if (!Number.isInteger(limit) || limit < 0) {
      throw new RangeError(`limit must be a non-negative integer, got ${limit}`);
    }
    const start = this.find(prefix);
    if (!start || limit === 0) return [];

    const best = new TopK(limit);
    // Iterative DFS: avoids call-stack limits on very long words.
    const stack: Array<[TrieNode, string]> = [[start, prefix]];
    while (stack.length > 0) {
      const [node, word] = stack.pop()!;
      if (node.frequency !== undefined) best.offer({ word, frequency: node.frequency });
      for (const [ch, child] of node.children) stack.push([child, word + ch]);
    }
    return best.toArray();
  }

  /** Iterates every stored word (unordered). Handy for export and debugging. */
  *entries(): IterableIterator<Completion> {
    const stack: Array<[TrieNode, string]> = [[this.root, ""]];
    while (stack.length > 0) {
      const [node, word] = stack.pop()!;
      if (node.frequency !== undefined) yield { word, frequency: node.frequency };
      for (const [ch, child] of node.children) stack.push([child, word + ch]);
    }
  }

  private find(prefix: string): TrieNode | undefined {
    let node: TrieNode | undefined = this.root;
    for (const ch of prefix) {
      node = node.children.get(ch);
      if (!node) return undefined;
    }
    return node;
  }

  private findOrCreate(word: string): TrieNode {
    let node = this.root;
    for (const ch of word) {
      let next = node.children.get(ch);
      if (!next) {
        next = new TrieNode();
        node.children.set(ch, next);
      }
      node = next;
    }
    return node;
  }
}

/**
 * Keeps the k best completions seen so far in sorted order.
 * Insertion uses binary search; for the small k typical of autocomplete
 * (5–20) this beats a heap in practice and keeps the output already sorted.
 */
class TopK {
  private readonly items: Completion[] = [];

  constructor(private readonly k: number) {}

  offer(c: Completion): void {
    const items = this.items;
    if (items.length === this.k && compareCompletions(c, items[items.length - 1]!) >= 0) return;
    let lo = 0;
    let hi = items.length;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (compareCompletions(items[mid]!, c) <= 0) lo = mid + 1;
      else hi = mid;
    }
    items.splice(lo, 0, c);
    if (items.length > this.k) items.pop();
  }

  toArray(): Completion[] {
    return [...this.items];
  }
}

function assertWord(word: string): void {
  if (word.length === 0) throw new RangeError("word must not be empty");
}

function assertFrequency(n: number): void {
  if (!Number.isSafeInteger(n) || n < 0) {
    throw new RangeError(`frequency must be a non-negative safe integer, got ${n}`);
  }
}
