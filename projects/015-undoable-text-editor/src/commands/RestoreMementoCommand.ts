import { captureMemento, restoreMemento, type DocumentMemento } from "../document/Memento.js";
import type { TextDocument } from "../document/TextDocument.js";
import type { Command } from "./Command.js";

/** Rolls the document back to a checkpoint, as an undoable step. */
export class RestoreMementoCommand implements Command {
  #before: DocumentMemento | undefined;

  constructor(private readonly target: DocumentMemento) {}

  get label(): string {
    return `Restore "${this.target.label}"`;
  }

  execute(document: TextDocument): void {
    const before = captureMemento(document, "before restore");
    restoreMemento(document, this.target); // throws on a foreign memento before we record anything
    this.#before = before;
  }

  undo(document: TextDocument): void {
    if (this.#before === undefined) throw new Error("Cannot undo a restore that was never executed.");
    restoreMemento(document, this.#before);
  }
}
