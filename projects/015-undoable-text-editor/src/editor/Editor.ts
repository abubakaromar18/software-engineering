import type { Command } from "../commands/Command.js";
import { DeleteRangeCommand } from "../commands/DeleteRangeCommand.js";
import { InsertTextCommand } from "../commands/InsertTextCommand.js";
import { MacroCommand } from "../commands/MacroCommand.js";
import { MoveCursorCommand } from "../commands/MoveCursorCommand.js";
import { RestoreMementoCommand } from "../commands/RestoreMementoCommand.js";
import { SnapshotCommand, type TextTransform } from "../commands/SnapshotCommand.js";
import { captureMemento, type DocumentMemento } from "../document/Memento.js";
import { TextDocument } from "../document/TextDocument.js";
import { History, type HistoryOptions } from "../history/History.js";
import { MacroRecorder, type CommandFactory, type Macro } from "./MacroRecorder.js";

export interface EditorState {
  readonly text: string;
  readonly cursor: number;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
  readonly dirty: boolean;
}

export type EditorListener = (state: EditorState) => void;

/**
 * Facade (the Client in Command-pattern terms). Translates user intents such
 * as "type", "backspace" or "play macro" into commands, and routes them
 * through the history and the macro recorder. UI code only ever talks to this.
 */
export class Editor {
  readonly #document: TextDocument;
  readonly #history: History;
  readonly #recorder = new MacroRecorder();
  readonly #listeners = new Set<EditorListener>();

  constructor(initialText = "", options: HistoryOptions = {}) {
    this.#document = new TextDocument(initialText);
    this.#history = new History(this.#document, options);
  }

  // ---- queries -------------------------------------------------------------

  get state(): EditorState {
    return {
      text: this.#document.text,
      cursor: this.#document.cursor,
      canUndo: this.#history.canUndo,
      canRedo: this.#history.canRedo,
      dirty: this.#history.isDirty,
    };
  }

  get text(): string {
    return this.#document.text;
  }

  get cursor(): number {
    return this.#document.cursor;
  }

  get undoLabels(): readonly string[] {
    return this.#history.undoLabels;
  }

  get redoLabels(): readonly string[] {
    return this.#history.redoLabels;
  }

  get isRecording(): boolean {
    return this.#recorder.isRecording;
  }

  /** Observer hook for UIs. Returns an unsubscribe function. */
  onChange(listener: EditorListener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  // ---- editing intents -----------------------------------------------------

  type(value: string): void {
    if (value.length === 0) return;
    this.#perform((doc) => new InsertTextCommand(doc.cursor, value));
  }

  backspace(): void {
    this.#perform((doc) => (doc.cursor === 0 ? undefined : new DeleteRangeCommand({ start: doc.cursor - 1, end: doc.cursor })));
  }

  deleteRange(start: number, end: number): void {
    this.#perform(() => new DeleteRangeCommand({ start, end }), { merge: false });
  }

  /** Applies a whole-document transform (memento-backed, always its own undo step). */
  transform(label: string, fn: TextTransform): void {
    this.#perform(() => new SnapshotCommand(label, fn), { merge: false });
  }

  // ---- cursor --------------------------------------------------------------

  moveTo(position: number): void {
    this.#move(() => position);
  }

  moveBy(delta: number): void {
    this.#move((doc) => doc.cursor + delta);
  }

  moveToLineStart(): void {
    this.#move((doc) => doc.text.lastIndexOf("\n", doc.cursor - 1) + 1);
  }

  moveToLineEnd(): void {
    this.#move((doc) => {
      const newline = doc.text.indexOf("\n", doc.cursor);
      return newline === -1 ? doc.length : newline;
    });
  }

  /** Moves to the start of the following line (or the end of the document). */
  moveToNextLine(): void {
    this.#move((doc) => {
      const newline = doc.text.indexOf("\n", doc.cursor);
      return newline === -1 ? doc.length : newline + 1;
    });
  }

  // ---- history -------------------------------------------------------------

  undo(): boolean {
    return this.#notifyIf(this.#history.undo());
  }

  redo(): boolean {
    return this.#notifyIf(this.#history.redo());
  }

  markSaved(): void {
    this.#history.markSaved();
    this.#notify();
  }

  // ---- mementos ------------------------------------------------------------

  /** Takes a named checkpoint the caller can later roll back to. */
  checkpoint(label: string): DocumentMemento {
    this.#history.seal();
    return captureMemento(this.#document, label);
  }

  /** Rolls back to a checkpoint. The rollback itself is undoable. */
  restore(memento: DocumentMemento): void {
    this.#perform(() => new RestoreMementoCommand(memento), { merge: false });
  }

  // ---- macros --------------------------------------------------------------

  startRecording(name: string): void {
    this.#recorder.start(name);
    this.#history.seal();
  }

  stopRecording(): Macro {
    const macro = this.#recorder.stop();
    this.#history.seal();
    return macro;
  }

  /**
   * Replays a macro `times` times as ONE undoable history entry.
   *
   * Steps are resolved against the live document one at a time (each step sees
   * the effects of the previous one). They are applied, then rolled back and
   * re-applied through History as a MacroCommand: this keeps History's single
   * "execute = record" path and reuses MacroCommand's transactional guarantee.
   */
  playMacro(macro: Macro, times = 1): void {
    if (this.#recorder.isRecording) throw new Error("Cannot play a macro while recording.");
    if (!Number.isInteger(times) || times < 1) throw new TypeError(`times must be a positive integer, got ${times}.`);

    const applied: Command[] = [];
    try {
      for (let run = 0; run < times; run++) {
        for (const step of macro.steps) {
          const command = step(this.#document);
          if (command === undefined) continue;
          command.execute(this.#document);
          applied.push(command);
        }
      }
    } finally {
      for (const command of [...applied].reverse()) command.undo(this.#document);
    }
    if (applied.length === 0) return;

    const label = times === 1 ? `Macro "${macro.name}"` : `Macro "${macro.name}" ×${times}`;
    this.#history.execute(new MacroCommand(label, applied), { merge: false });
    this.#notify();
  }

  // ---- internals -----------------------------------------------------------

  #perform(factory: CommandFactory, options: { merge?: boolean } = {}): void {
    const command = factory(this.#document);
    if (command === undefined) return;
    this.#history.execute(command, options);
    this.#recorder.record(factory);
    this.#notify();
  }

  #move(target: (doc: TextDocument) => number): void {
    this.#document.moveCursor(target(this.#document));
    this.#history.seal(); // typing after a jump starts a new undo group
    this.#recorder.record((doc) => new MoveCursorCommand(target(doc)));
    this.#notify();
  }

  #notifyIf(changed: boolean): boolean {
    if (changed) this.#notify();
    return changed;
  }

  #notify(): void {
    const state = this.state;
    for (const listener of this.#listeners) listener(state);
  }
}
