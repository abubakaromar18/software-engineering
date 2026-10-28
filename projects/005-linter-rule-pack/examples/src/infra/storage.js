// node:fs is allowed here and nowhere else.
import { readFileSync } from "node:fs";

export const loadJson = (file) => JSON.parse(readFileSync(file, "utf8"));
