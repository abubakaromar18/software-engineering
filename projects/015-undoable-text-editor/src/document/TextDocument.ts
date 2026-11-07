/**
 * The Receiver in the Command pattern: a plain text buffer plus a cursor.
 *
 * It knows nothing about undo, history or commands. It only offers small,
 * validated primitive edits. Keeping it dumb means every command can be
 * reasoned about as "a primitive edit plus the information to reverse it".
 */

/** Thrown when an edit would address characters outside the buffer. */
export class TextRangeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TextRangeError";
  }
}

/** A half-open character range: `start` inclusive, `end` exclusive. */
export interface TextRange {
  readonly start: number;
  readonly end: number;
}

export class TextDocument {
  #text: string;
  #cursor: number;

  constructor(initialText = "") {
    this.#text = initialText;
    this.#cursor = initialText.length;
  }

  get text(): string {
    return this.#text;
  }

  get length(): number {
    return this.#text.length;
  }

  get cursor(): number {
    return this.#cursor;
  }

  /** Moves the cursor, clamping into `[0, length]` (like an editor does on arrow keys). */
  moveCursor(position: number): void {
    this.#cursor = Math.max(0, Math.min(this.#text.length, Math.trunc(position)));
  }

  /** Returns the substring for a range after validating it. */
  slice(range: TextRange): string {
    this.#assertRange(range);
    return this.#text.slice(range.start, range.end);
  }

  /** Inserts `value` at `position` and leaves the cursor after the inserted text. */
  insert(position: number, value: string): void {
    this.#assertPosition(position);
    this.#text = this.#text.slice(0, position) + value + this.#text.slice(position);
    this.#cursor = position + value.length;
  }

  /** Deletes a range, returns the removed text, and leaves the cursor at `range.start`. */
  delete(range: TextRange): string {
    this.#assertRange(range);
    const removed = this.#text.slice(range.start, range.end);
    this.#text = this.#text.slice(0, range.start) + this.#text.slice(range.end);
    this.#cursor = range.start;
    return removed;
  }

  /**
   * Replaces the whole buffer and cursor. This is deliberately the only "bulk"
   * mutator and exists to support restoring a memento.
   */
  reset(text: string, cursor: number): void {
    this.#text = text;
    this.moveCursor(cursor);
  }

  #assertPosition(position: number): void {
    if (!Number.isInteger(position) || position < 0 || position > this.#text.length) {
      throw new TextRangeError(`Position ${position} is outside the document (length ${this.#text.length}).`);
    }
  }

  #assertRange(range: TextRange): void {
    this.#assertPosition(range.start);
    this.#assertPosition(range.end);
    if (range.start > range.end) {
      throw new TextRangeError(`Range start ${range.start} is after end ${range.end}.`);
    }
  }
}
