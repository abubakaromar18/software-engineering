import { describe, expect, it } from "vitest";
import {
  DeleteRangeCommand,
  InsertTextCommand,
  MacroCommand,
  SnapshotCommand,
  TextDocument,
  transforms,
  type Command,
} from "../src/index.js";

/** Asserts the core Command contract: execute+undo is the identity, redo reproduces execute. */
function assertReversible(initial: string, cursor: number, command: Command): void {
  const doc = new TextDocument(initial);
  doc.moveCursor(cursor);
  command.execute(doc);
  const after = { text: doc.text, cursor: doc.cursor };
  command.undo(doc);
  expect({ text: doc.text, cursor: doc.cursor }).toEqual({ text: initial, cursor });
  command.execute(doc);
  expect({ text: doc.text, cursor: doc.cursor }).toEqual(after);
}

describe("command reversibility", () => {
  it.each<[string, Command]>([
    ["insert", new InsertTextCommand(2, "XY")],
    ["delete", new DeleteRangeCommand({ start: 1, end: 4 })],
    ["snapshot", new SnapshotCommand("upper", transforms.upperCase)],
    ["macro", new MacroCommand("m", [new InsertTextCommand(0, ">"), new DeleteRangeCommand({ start: 3, end: 5 })])],
  ])("%s: undo restores text and cursor, redo reapplies", (_name, command) => {
    assertReversible("abcdef", 3, command);
  });
});

describe("InsertTextCommand merging", () => {
  const run = (doc: TextDocument, cmd: InsertTextCommand) => (cmd.execute(doc), cmd);

  it("merges adjacent keystrokes and keeps the original cursor for undo", () => {
    const doc = new TextDocument("");
    const a = run(doc, new InsertTextCommand(0, "a"));
    const b = run(doc, new InsertTextCommand(1, "b"));
    const merged = a.mergeWith(b) as InsertTextCommand;
    expect(merged.value).toBe("ab");
    merged.undo(doc);
    expect(doc.text).toBe("");
    expect(doc.cursor).toBe(0);
  });

  it("does not merge non-adjacent inserts or across a word boundary", () => {
    const doc = new TextDocument("");
    const a = run(doc, new InsertTextCommand(0, "a "));
    expect(a.mergeWith(run(doc, new InsertTextCommand(2, "b")))).toBeUndefined();
    expect(a.mergeWith(run(doc, new InsertTextCommand(0, "z")))).toBeUndefined();
    expect(a.mergeWith(new DeleteRangeCommand({ start: 0, end: 1 }))).toBeUndefined();
  });

  it("rejects empty text", () => {
    expect(() => new InsertTextCommand(0, "")).toThrow(TypeError);
  });
});

describe("DeleteRangeCommand merging", () => {
  it("merges consecutive backspaces into one range", () => {
    const doc = new TextDocument("hello");
    const first = new DeleteRangeCommand({ start: 4, end: 5 });
    first.execute(doc);
    const second = new DeleteRangeCommand({ start: 3, end: 4 });
    second.execute(doc);
    const merged = first.mergeWith(second) as DeleteRangeCommand;
    expect(merged.range).toEqual({ start: 3, end: 5 });
    expect(merged.label).toBe('Delete "lo"');
    merged.undo(doc);
    expect(doc.text).toBe("hello");
    expect(doc.cursor).toBe(5);
  });

  it("refuses to undo before executing", () => {
    expect(() => new DeleteRangeCommand({ start: 0, end: 1 }).undo(new TextDocument("a"))).toThrow(/never executed/);
  });
});

describe("MacroCommand", () => {
  it("rolls back already-applied children when a later child fails", () => {
    const doc = new TextDocument("abc");
    const macro = new MacroCommand("bad", [new InsertTextCommand(0, "X"), new DeleteRangeCommand({ start: 10, end: 11 })]);
    expect(() => macro.execute(doc)).toThrow();
    expect(doc.text).toBe("abc");
  });

  it("requires children", () => {
    expect(() => new MacroCommand("empty", [])).toThrow(TypeError);
  });
});

describe("transforms", () => {
  it("sorts lines and replaces all occurrences", () => {
    expect(transforms.sortLines("c\na\nb")).toBe("a\nb\nc");
    expect(transforms.replaceAll("o", "0")("foo boo")).toBe("f00 b00");
    expect(() => transforms.replaceAll("", "x")("abc")).toThrow(TypeError);
  });
});
