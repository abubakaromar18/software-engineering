"use strict";

/**
 * RuleTester wired to Node's built-in test runner, so the suite needs no
 * Mocha/Jest. RuleTester calls these hooks to create one test per case.
 */

const { describe, it } = require("node:test");
const { RuleTester } = require("eslint");

RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

/** @returns {RuleTester} a tester for modern ESM source */
function createRuleTester() {
  return new RuleTester({
    languageOptions: { ecmaVersion: "latest", sourceType: "module" },
  });
}

module.exports = { createRuleTester };
