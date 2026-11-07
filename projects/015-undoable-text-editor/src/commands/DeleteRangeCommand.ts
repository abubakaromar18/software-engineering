import type { TextDocument, TextRange } from "../document/TextDocument.js";
import type { Command } from "./Command.js";

/**
 * Deletes a range. The removed text is only known at execution time, so it is
 * captured then; that captured text is the "undo information".
 */
export class DeleteRangeCommand implements Command {
  #removed: string | undefined;
  #cursorBefore = 0;

  constructor(readonly range: TextRange) {
    if (range.end <= range.start) {
      throw new TypeError("DeleteRangeCommand requires a non-empty range.");
    }
  }

  get label(): string {
    return this.#removed === undefined ? "Delete" : `Delete ${JSON.stringify(this.#removed)}`;
  }

  execute(document: TextDocument): void {
    this.#cursorBefore = document.cursor;
    this.#removed = document.delete(this.range);
  }

  undo(document: TextDocument): void {
    if (this.#removed === undefined) {
      throw new Error("Cannot undo a DeleteRangeCommand that was never executed.");
    }
    document.insert(this.range.start, this.#removed);
    document.moveCursor(this.#cursorBefore);
  }

  /** Coalesces repeated backspaces: deleting [4,5) then [3,4) becomes [3,5). */
  mergeWith(next: Command): Command | undefined {
    if (!(next instanceof DeleteRangeCommand) || this.#removed === undefined || next.#removed === undefined) {
      return undefined;
    }
    if (next.range.end !== this.range.start) return undefined;
    const merged = new DeleteRangeCommand({ start: next.range.start, end: this.range.end });
    merged.#removed = next.#removed + this.#removed;
    merged.#cursorBefore = this.#cursorBefore;
    return merged;
  }
}
