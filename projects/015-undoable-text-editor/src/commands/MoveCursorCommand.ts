import type { TextDocument } from "../document/TextDocument.js";
import type { Command } from "./Command.js";

/**
 * Moves the cursor. Plain cursor movement is not an undoable edit in the
 * editor, but inside a macro it must be replayable and reversible so the macro
 * as a whole restores the cursor on undo.
 */
export class MoveCursorCommand implements Command {
  readonly label = "Move cursor";
  #before = 0;

  constructor(readonly target: number) {}

  execute(document: TextDocument): void {
    this.#before = document.cursor;
    document.moveCursor(this.target);
  }

  undo(document: TextDocument): void {
    document.moveCursor(this.#before);
  }
}
