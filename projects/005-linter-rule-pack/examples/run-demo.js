"use strict";

/**
 * Lints examples/src with examples/eslint.config.js and prints the report.
 * The violations are intentional, so the demo exits 0 either way.
 */

const path = require("node:path");
const { ESLint } = require("eslint");

async function main() {
  const cwd = __dirname;
  const eslint = new ESLint({ cwd, overrideConfigFile: path.join(cwd, "eslint.config.js") });
  const results = await eslint.lintFiles(["src/**/*.js"]);
  const formatter = await eslint.loadFormatter("stylish");
  process.stdout.write(await formatter.format(results));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
