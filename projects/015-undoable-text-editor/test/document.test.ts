import { describe, expect, it } from "vitest";
import { captureMemento, restoreMemento, TextDocument, TextRangeError, type DocumentMemento } from "../src/index.js";

describe("TextDocument", () => {
  it("inserts and deletes while tracking the cursor", () => {
    const doc = new TextDocument("held");
    expect(doc.cursor).toBe(4);
    doc.insert(3, "l");
    expect(doc.text).toBe("helld");
    expect(doc.cursor).toBe(4);
    expect(doc.delete({ start: 0, end: 2 })).toBe("he");
    expect(doc.text).toBe("lld");
    expect(doc.cursor).toBe(0);
  });

  it("clamps cursor movement", () => {
    const doc = new TextDocument("abc");
    doc.moveCursor(-5);
    expect(doc.cursor).toBe(0);
    doc.moveCursor(99);
    expect(doc.cursor).toBe(3);
  });

  it("rejects out-of-range edits without mutating", () => {
    const doc = new TextDocument("abc");
    expect(() => doc.insert(4, "x")).toThrow(TextRangeError);
    expect(() => doc.delete({ start: 2, end: 1 })).toThrow(TextRangeError);
    expect(() => doc.slice({ start: 0, end: 10 })).toThrow(TextRangeError);
    expect(doc.text).toBe("abc");
  });
});

describe("Memento", () => {
  it("restores text and cursor", () => {
    const doc = new TextDocument("one");
    doc.moveCursor(1);
    const memento = captureMemento(doc, "start", () => new Date(0));
    doc.insert(3, " two");
    restoreMemento(doc, memento);
    expect(doc.text).toBe("one");
    expect(doc.cursor).toBe(1);
    expect(memento.label).toBe("start");
    expect(memento.takenAt.getTime()).toBe(0);
  });

  it("is opaque and immutable", () => {
    const memento = captureMemento(new TextDocument("secret"));
    expect(Object.keys(memento).sort()).toEqual(["label", "takenAt"]);
    expect(Object.isFrozen(memento)).toBe(true);
  });

  it("rejects forged mementos", () => {
    const forged: DocumentMemento = { label: "fake", takenAt: new Date() };
    expect(() => restoreMemento(new TextDocument(), forged)).toThrow(/Unknown memento/);
  });
});
