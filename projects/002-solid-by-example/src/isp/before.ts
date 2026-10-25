/**
 * ISP — BEFORE.
 *
 * One "fat" interface for every office device. A plain printer is forced to
 * implement scan() and fax() and can only throw from them. Clients that just
 * want to print still depend on all three methods, so a test double for them
 * has to stub methods it never calls, and a type check cannot tell a printer
 * from a scanner: mistakes surface as runtime errors.
 */
import { assertFaxNumber, assertPrintable, DeviceError, type Document } from "./types.js";

export interface MultiFunctionDevice {
  readonly name: string;
  print(doc: Document): string;
  scan(sheet: string): Document;
  fax(doc: Document, number: string): string;
}

export class OfficeMachine implements MultiFunctionDevice {
  private scans = 0;

  constructor(readonly name: string) {}

  print(doc: Document): string {
    assertPrintable(doc);
    return `[${this.name}] printed '${doc.title}' (${doc.pages.length} page${doc.pages.length === 1 ? "" : "s"})`;
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

export class BasicPrinter implements MultiFunctionDevice {
  constructor(readonly name: string) {}

  print(doc: Document): string {
    assertPrintable(doc);
    return `[${this.name}] printed '${doc.title}' (${doc.pages.length} page${doc.pages.length === 1 ? "" : "s"})`;
  }

  // Forced on us by the fat interface.
  scan(_sheet: string): Document {
    throw new DeviceError(`${this.name} cannot scan`);
  }

  fax(_doc: Document, _number: string): string {
    throw new DeviceError(`${this.name} cannot fax`);
  }
}

/** A client that only prints, yet depends on scanning and faxing too. */
export function printAll(device: MultiFunctionDevice, docs: readonly Document[]): string[] {
  return docs.map((doc) => device.print(doc));
}

/** Scans every sheet and forwards the result by fax. */
export function scanAndFax(device: MultiFunctionDevice, sheets: readonly string[], number: string): string[] {
  return sheets.map((sheet) => device.fax(device.scan(sheet), number));
}
