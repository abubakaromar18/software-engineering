import { captureMemento, restoreMemento, type DocumentMemento } from "../document/Memento.js";
import type { TextDocument } from "../document/TextDocument.js";
import type { Command } from "./Command.js";

/** A whole-document transformation that is hard or impossible to invert. */
export type TextTransform = (text: string) => string;

/**
 * Memento-backed command for edits without a cheap inverse (sorting lines,
 * regex replace-all, reformatting). Before executing it snapshots the
 * document; undo simply restores the snapshot.
 *
 * Trade-off: memory proportional to document size per history entry, versus
 * the tiny footprint of inverse-operation commands such as InsertTextCommand.
 */
export class SnapshotCommand implements Command {
  #before: DocumentMemento | undefined;

  constructor(
    readonly label: string,
    private readonly transform: TextTransform,
  ) {}

  execute(document: TextDocument): void {
    const next = this.transform(document.text);
    this.#before = captureMemento(document, this.label);
    document.reset(next, Math.min(document.cursor, next.length));
  }

  undo(document: TextDocument): void {
    if (this.#before === undefined) {
      throw new Error(`Cannot undo "${this.label}": it was never executed.`);
    }
    restoreMemento(document, this.#before);
  }
}

/** Common transforms, kept here so the editor and demo can share them. */
export const transforms = {
  upperCase: (text: string): string => text.toUpperCase(),
  sortLines: (text: string): string => text.split("\n").sort((a, b) => a.localeCompare(b)).join("\n"),
  replaceAll:
    (search: string, replacement: string): TextTransform =>
    (text) => {
      if (search.length === 0) throw new TypeError("Search text must not be empty.");
      return text.split(search).join(replacement);
    },
} as const;
