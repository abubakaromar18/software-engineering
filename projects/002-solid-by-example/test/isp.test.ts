import { describe, expect, it } from "vitest";
import * as before from "../src/isp/before.js";
import * as after from "../src/isp/after.js";
import { DeviceError, type Document } from "../src/isp/types.js";

const memo: Document = { title: "Memo", pages: ["one"] };
const report: Document = { title: "Report", pages: ["a", "b", "c"] };
const empty: Document = { title: "Blank", pages: [] };

function outcome(run: () => unknown): unknown {
  try {
    return run();
  } catch (error) {
    if (!(error instanceof DeviceError)) throw error;
    return `error: ${error.message}`;
  }
}

describe("ISP parity: segregated interfaces keep behaviour identical", () => {
  it("printing works the same on both printers", () => {
    for (const docs of [[memo, report], [empty]]) {
      expect(outcome(() => after.printAll(new after.BasicPrinter("P"), docs))).toEqual(
        outcome(() => before.printAll(new before.BasicPrinter("P"), docs)),
      );
      expect(outcome(() => after.printAll(new after.OfficeMachine("M"), docs))).toEqual(
        outcome(() => before.printAll(new before.OfficeMachine("M"), docs)),
      );
    }
    expect(after.printAll(new after.BasicPrinter("P"), [memo, report])).toEqual([
      "[P] printed 'Memo' (1 page)",
      "[P] printed 'Report' (3 pages)",
    ]);
  });

  it.each(["+1 555 0100", "020-7946-0018", "12", "not a number"])("scan and fax behave the same for %s", (number) => {
    const b = new before.OfficeMachine("M");
    const a = new after.OfficeMachine("M");
    const sheets = ["page-1", "page-2"];
    expect(outcome(() => after.scanAndFax(a, sheets, number))).toEqual(
      outcome(() => before.scanAndFax(b, sheets, number)),
    );
    // The scan counter advanced identically too.
    expect(a.scan("x")).toEqual(b.scan("x"));
  });
});

describe("ISP: the fat interface hides capability mistakes until runtime", () => {
  it("before: a BasicPrinter type-checks as a scanner and fails when used", () => {
    const printer: before.MultiFunctionDevice = new before.BasicPrinter("P");
    expect(() => before.scanAndFax(printer, ["s"], "+1 555 0100")).toThrow("P cannot scan");
  });

  it("before: a print-only test double must still stub scan() and fax()", () => {
    const fake: before.MultiFunctionDevice = {
      name: "fake",
      print: (doc) => doc.title,
      scan: () => { throw new Error("unused"); },
      fax: () => { throw new Error("unused"); },
    };
    expect(before.printAll(fake, [memo])).toEqual(["Memo"]);
  });
});

describe("ISP payoff: clients depend only on what they use", () => {
  it("after: a print-only test double is one method", () => {
    const fake: after.Printer = { print: (doc) => doc.title };
    expect(after.printAll(fake, [memo])).toEqual(["Memo"]);
  });

  it("after: passing a BasicPrinter to scanAndFax is a compile error", () => {
    const printer = new after.BasicPrinter("P");
    // @ts-expect-error BasicPrinter is not a Scanner & FaxMachine; this line must not compile.
    const misuse = (): unknown => after.scanAndFax(printer, ["s"], "+1 555 0100");
    expect(typeof misuse).toBe("function");
    expect("scan" in printer).toBe(false);
  });
});
