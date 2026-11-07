import type { TextDocument } from "../document/TextDocument.js";
import type { Command } from "./Command.js";

/** Inserts text at a fixed position. Reversible by deleting the same span. */
export class InsertTextCommand implements Command {
  #cursorBefore = 0;

  constructor(
    readonly position: number,
    readonly value: string,
  ) {
    if (value.length === 0) {
      throw new TypeError("InsertTextCommand requires non-empty text.");
    }
  }

  get label(): string {
    return `Type ${JSON.stringify(this.value)}`;
  }

  execute(document: TextDocument): void {
    this.#cursorBefore = document.cursor;
    document.insert(this.position, this.value);
  }

  undo(document: TextDocument): void {
    document.delete({ start: this.position, end: this.position + this.value.length });
    document.moveCursor(this.#cursorBefore);
  }

  /**
   * Coalesces continuous typing: "a" at 3 followed by "b" at 4 becomes "ab" at 3.
   * A word boundary (whitespace after non-whitespace) ends a group, so undo
   * removes roughly one word at a time, like most editors.
   */
  mergeWith(next: Command): Command | undefined {
    if (!(next instanceof InsertTextCommand)) return undefined;
    if (next.position !== this.position + this.value.length) return undefined;
    if (/\s$/.test(this.value) && !/^\s/.test(next.value)) return undefined;
    const merged = new InsertTextCommand(this.position, this.value + next.value);
    merged.#cursorBefore = this.#cursorBefore;
    return merged;
  }
}
