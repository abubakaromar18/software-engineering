import type { CorpusEntry } from "./corpus.js";
import { normalize } from "./normalize.js";
import { Trie, type Completion } from "./trie.js";

export interface AutocompleteOptions {
  /** Results returned when the caller does not ask for a specific count. */
  readonly defaultLimit: number;
  /** Hard ceiling on results per request, protecting the server from huge scans. */
  readonly maxLimit: number;
  /** Longest accepted query or word, in code points. */
  readonly maxQueryLength: number;
}

/** A caller-supplied value was rejected; maps to HTTP 400. */
export class ValidationError extends Error {
  override readonly name = "ValidationError";
}

/**
 * Application layer between transport (HTTP) and the data structure (Trie).
 *
 * It owns the policy the trie should not know about: input normalisation,
 * limits, and learning from user selections. Keeping this separate means the
 * trie stays a reusable, pure data structure and the HTTP layer stays a thin
 * adapter that only translates requests and status codes.
 */
export class AutocompleteService {
  private readonly trie = new Trie();

  constructor(private readonly options: AutocompleteOptions) {
    if (options.defaultLimit < 1 || options.defaultLimit > options.maxLimit) {
      throw new RangeError("defaultLimit must be between 1 and maxLimit");
    }
  }

  get size(): number {
    return this.trie.size;
  }

  /** Seeds the index. Duplicate words (after normalisation) have their frequencies summed. */
  load(entries: Iterable<CorpusEntry>): void {
    for (const { word, frequency } of entries) {
      const key = normalize(word);
      if (key !== "") this.trie.increment(key, frequency);
    }
  }

  /** Ranked suggestions for a (raw, unnormalised) prefix. */
  suggest(prefix: string, limit?: number): Completion[] {
    const query = this.validateText(prefix, "q", { allowEmpty: true });
    if (query === "") return [];
    return this.trie.complete(query, this.resolveLimit(limit));
  }

  /**
   * Records that the user picked `word`, boosting it in future rankings.
   * Unknown words are learned, which is how the index adapts to new vocabulary.
   */
  recordSelection(word: string): Completion {
    const key = this.validateText(word, "word", { allowEmpty: false });
    return { word: key, frequency: this.trie.increment(key) };
  }

  /** Removes a word entirely (e.g. moderation). Returns false if it was absent. */
  remove(word: string): boolean {
    return this.trie.delete(normalize(word));
  }

  private resolveLimit(limit: number | undefined): number {
    if (limit === undefined) return this.options.defaultLimit;
    if (!Number.isInteger(limit) || limit < 1) {
      throw new ValidationError("limit must be a positive integer");
    }
    return Math.min(limit, this.options.maxLimit);
  }

  private validateText(raw: string, field: string, { allowEmpty }: { allowEmpty: boolean }): string {
    const value = normalize(raw);
    if (!allowEmpty && value === "") throw new ValidationError(`${field} must not be empty`);
    if ([...value].length > this.options.maxQueryLength) {
      throw new ValidationError(`${field} exceeds ${this.options.maxQueryLength} characters`);
    }
    return value;
  }
}
