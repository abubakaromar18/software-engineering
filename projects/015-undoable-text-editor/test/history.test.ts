import { describe, expect, it } from "vitest";
import { DeleteRangeCommand, History, InsertTextCommand, TextDocument } from "../src/index.js";

function setup(options: { limit?: number; mergeWindowMs?: number } = {}) {
  let clock = 0;
  const doc = new TextDocument("");
  const history = new History(doc, { ...options, now: () => clock });
  const typeChar = (ch: string) => history.execute(new InsertTextCommand(doc.cursor, ch));
  return { doc, history, typeChar, tick: (ms: number) => (clock += ms) };
}

describe("History", () => {
  it("undoes and redoes in LIFO order", () => {
    const { doc, history } = setup();
    history.execute(new InsertTextCommand(0, "a"), { merge: false });
    history.execute(new InsertTextCommand(1, "b"), { merge: false });
    expect(history.undo()).toBe(true);
    expect(doc.text).toBe("a");
    expect(history.redo()).toBe(true);
    expect(doc.text).toBe("ab");
    expect(history.redo()).toBe(false);
  });

  it("returns false when nothing to undo", () => {
    expect(setup().history.undo()).toBe(false);
  });

  it("clears the redo stack when a new command executes", () => {
    const { doc, history, typeChar } = setup();
    typeChar("a");
    history.undo();
    expect(history.canRedo).toBe(true);
    history.execute(new InsertTextCommand(doc.cursor, "z"));
    expect(history.canRedo).toBe(false);
  });

  it("coalesces typing within the merge window", () => {
    const { doc, history, typeChar, tick } = setup({ mergeWindowMs: 500 });
    for (const ch of "abc") {
      typeChar(ch);
      tick(100);
    }
    expect(history.undoLabels).toEqual(['Type "abc"']);
    tick(1000);
    typeChar("d");
    expect(history.undoLabels).toEqual(['Type "abc"', 'Type "d"']);
    history.undo();
    expect(doc.text).toBe("abc");
  });

  it("does not merge after undo, seal or with merge disabled", () => {
    const { history, typeChar } = setup();
    typeChar("a");
    history.seal();
    typeChar("b");
    expect(history.undoLabels).toHaveLength(2);
    history.undo();
    typeChar("c");
    expect(history.undoLabels).toEqual(['Type "a"', 'Type "c"']);
  });

  it("does not record a command that throws", () => {
    const { doc, history } = setup();
    expect(() => history.execute(new DeleteRangeCommand({ start: 0, end: 3 }))).toThrow();
    expect(history.canUndo).toBe(false);
    expect(doc.text).toBe("");
  });

  it("drops the oldest entries beyond the limit", () => {
    const { doc, history } = setup({ limit: 2 });
    for (const ch of "abc") history.execute(new InsertTextCommand(doc.cursor, ch), { merge: false });
    expect(history.undoLabels).toEqual(['Type "b"', 'Type "c"']);
    while (history.undo());
    expect(doc.text).toBe("a");
  });

  it("validates the limit", () => {
    expect(() => new History(new TextDocument(), { limit: 0 })).toThrow(TypeError);
  });

  it("tracks dirty state relative to the save point", () => {
    const { history, typeChar } = setup();
    expect(history.isDirty).toBe(false);
    typeChar("a");
    expect(history.isDirty).toBe(true);
    history.markSaved();
    expect(history.isDirty).toBe(false);
    typeChar("b"); // cannot merge into the saved entry: markSaved seals
    expect(history.isDirty).toBe(true);
    history.undo();
    expect(history.isDirty).toBe(false);
    history.undo();
    expect(history.isDirty).toBe(true);
    history.redo();
    expect(history.isDirty).toBe(false);
  });

  it("clear() empties both stacks", () => {
    const { history, typeChar } = setup();
    typeChar("a");
    typeChar(" ");
    typeChar("b");
    history.undo();
    history.clear();
    expect(history.canUndo || history.canRedo).toBe(false);
  });
});
