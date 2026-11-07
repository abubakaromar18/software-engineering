import type { TextDocument } from "./TextDocument.js";

/**
 * Memento pattern: an opaque, immutable snapshot of a document's state.
 *
 * Callers (the caretaker: history, editor, user code) can hold and pass
 * mementos around but cannot read or modify the captured state. Only this
 * module can create one or apply it back onto a document, which preserves the
 * document's encapsulation.
 */
export interface DocumentMemento {
  /** When the snapshot was taken; useful for labelling checkpoints. */
  readonly takenAt: Date;
  /** Optional human-readable label, e.g. "before sort". */
  readonly label: string;
}

interface SnapshotState {
  readonly text: string;
  readonly cursor: number;
}

// The private state lives in a WeakMap keyed by the public memento object, so
// it is unreachable from outside this module and garbage-collected with it.
const states = new WeakMap<DocumentMemento, SnapshotState>();

export function captureMemento(document: TextDocument, label = "snapshot", now: () => Date = () => new Date()): DocumentMemento {
  const memento: DocumentMemento = Object.freeze({ takenAt: now(), label });
  states.set(memento, Object.freeze({ text: document.text, cursor: document.cursor }));
  return memento;
}

export function restoreMemento(document: TextDocument, memento: DocumentMemento): void {
  const state = states.get(memento);
  if (state === undefined) {
    throw new TypeError("Unknown memento: it was not created by captureMemento().");
  }
  document.reset(state.text, state.cursor);
}
