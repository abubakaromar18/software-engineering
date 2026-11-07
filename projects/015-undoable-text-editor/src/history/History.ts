import type { Command } from "../commands/Command.js";
import type { TextDocument } from "../document/TextDocument.js";

/** Tunables for the history; injectable so tests can control time. */
export interface HistoryOptions {
  /** Maximum undo entries kept. Oldest entries are dropped first. Default 100. */
  readonly limit?: number;
  /** Keystrokes further apart than this (ms) are not coalesced. Default 1000. */
  readonly mergeWindowMs?: number;
  /** Clock used for the merge window. Default `Date.now`. */
  readonly now?: () => number;
}

interface Entry {
  readonly id: number;
  readonly command: Command;
  readonly at: number;
}

/**
 * The Invoker / caretaker: executes commands against a document and keeps the
 * undo and redo stacks.
 *
 * Invariants:
 *  - Executing a new command clears the redo stack (history is linear, not a tree).
 *  - A command that throws during execute is never recorded.
 *  - `isDirty` compares the current top entry to the one marked at save time,
 *    so undoing back to the save point makes the document clean again.
 */
export class History {
  readonly #document: TextDocument;
  readonly #limit: number;
  readonly #mergeWindowMs: number;
  readonly #now: () => number;
  #undo: Entry[] = [];
  #redo: Entry[] = [];
  #nextId = 1;
  #sealed = false;
  #savedEntryId: number | undefined = undefined;

  constructor(document: TextDocument, options: HistoryOptions = {}) {
    const limit = options.limit ?? 100;
    if (!Number.isInteger(limit) || limit < 1) {
      throw new TypeError(`History limit must be a positive integer, got ${limit}.`);
    }
    this.#document = document;
    this.#limit = limit;
    this.#mergeWindowMs = options.mergeWindowMs ?? 1000;
    this.#now = options.now ?? Date.now;
  }

  get canUndo(): boolean {
    return this.#undo.length > 0;
  }

  get canRedo(): boolean {
    return this.#redo.length > 0;
  }

  /** Labels from oldest to newest, for an "Edit > Undo ..." menu. */
  get undoLabels(): readonly string[] {
    return this.#undo.map((e) => e.command.label);
  }

  get redoLabels(): readonly string[] {
    return this.#redo.map((e) => e.command.label).reverse();
  }

  get isDirty(): boolean {
    return this.#topId() !== this.#savedEntryId;
  }

  /** Executes and records a command, coalescing it into the previous one when allowed. */
  execute(command: Command, { merge = true }: { merge?: boolean } = {}): void {
    command.execute(this.#document); // throws => nothing recorded
    this.#redo = [];

    const at = this.#now();
    const previous = this.#undo.at(-1);
    if (merge && !this.#sealed && previous !== undefined && at - previous.at <= this.#mergeWindowMs) {
      const merged = previous.command.mergeWith?.(command);
      if (merged !== undefined) {
        this.#undo[this.#undo.length - 1] = { id: this.#nextId++, command: merged, at };
        return;
      }
    }

    this.#undo.push({ id: this.#nextId++, command, at });
    this.#sealed = false;
    if (this.#undo.length > this.#limit) this.#undo.shift();
  }

  /** Prevents the next command from merging into the current top (e.g. after a cursor jump). */
  seal(): void {
    this.#sealed = true;
  }

  undo(): boolean {
    const entry = this.#undo.pop();
    if (entry === undefined) return false;
    entry.command.undo(this.#document);
    this.#redo.push(entry);
    this.#sealed = true;
    return true;
  }

  redo(): boolean {
    const entry = this.#redo.pop();
    if (entry === undefined) return false;
    entry.command.execute(this.#document);
    this.#undo.push(entry);
    this.#sealed = true;
    return true;
  }

  /** Records the current state as "saved" for dirty tracking. */
  markSaved(): void {
    this.#savedEntryId = this.#topId();
    this.#sealed = true;
  }

  clear(): void {
    this.#undo = [];
    this.#redo = [];
    this.#savedEntryId = undefined;
    this.#sealed = false;
  }

  #topId(): number | undefined {
    return this.#undo.at(-1)?.id;
  }
}
