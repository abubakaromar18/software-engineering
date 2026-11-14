/**
 * Raised for any roll sequence that cannot occur in a legal game of ten-pin
 * bowling. Callers (the CLI, a UI) can catch this one type and show the
 * message, while programming errors still surface as ordinary exceptions.
 */
export class BowlingError extends Error {
  constructor(message) {
    super(message);
    this.name = 'BowlingError';
  }
}
