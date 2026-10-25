/**
 * ISP — AFTER.
 *
 * Three role interfaces, each with a single capability. Devices implement only
 * what they can do, and each client asks for exactly the role it uses:
 *
 *   printAll   needs a Printer
 *   scanAndFax needs a Scanner & FaxMachine (an intersection, not a fat type)
 *
 * A BasicPrinter can no longer be handed to scanAndFax: it is a compile error
 * instead of a runtime DeviceError.
 */
import { assertFaxNumber, assertPrintable, type Document } from "./types.js";

export interface Printer {
  print(doc: Document): string;
}

export interface Scanner {
  scan(sheet: string): Document;
}

export interface FaxMachine {
  fax(doc: Document, number: string): string;
}

function printLabel(deviceName: string, doc: Document): string {
  assertPrintable(doc);
  return `[${deviceName}] printed '${doc.title}' (${doc.pages.length} page${doc.pages.length === 1 ? "" : "s"})`;
}

export class OfficeMachine implements Printer, Scanner, FaxMachine {
  private scans = 0;

  constructor(readonly name: string) {}

  print(doc: Document): string {
    return printLabel(this.name, doc);
  }

  scan(sheet: string): Document {
    this.scans++;
    return { title: `${this.name} scan ${this.scans}`, pages: [sheet] };
  }

  fax(doc: Document, number: string): string {
    assertPrintable(doc);
    assertFaxNumber(number);
    return `[${this.name}] faxed '${doc.title}' to ${number}`;
  }
}

export class BasicPrinter implements Printer {
  constructor(readonly name: string) {}

  print(doc: Document): string {
    return printLabel(this.name, doc);
  }
}

export function printAll(printer: Printer, docs: readonly Document[]): string[] {
  return docs.map((doc) => printer.print(doc));
}

export function scanAndFax(device: Scanner & FaxMachine, sheets: readonly string[], number: string): string[] {
  return sheets.map((sheet) => device.fax(device.scan(sheet), number));
}
