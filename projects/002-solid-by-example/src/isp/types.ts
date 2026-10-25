export interface Document {
  readonly title: string;
  readonly pages: readonly string[];
}

export class DeviceError extends Error {
  override readonly name: string = "DeviceError";
}

const FAX_NUMBER = /^\+?[0-9][0-9 -]{5,}$/;

/** Shared validation so both versions reject the same input. */
export function assertFaxNumber(number: string): void {
  if (!FAX_NUMBER.test(number)) throw new DeviceError(`Invalid fax number: ${number}`);
}

export function assertPrintable(doc: Document): void {
  if (doc.pages.length === 0) throw new DeviceError(`Document '${doc.title}' has no pages`);
}
