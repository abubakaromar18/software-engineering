"use strict";

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { createMatcher, globToRegExp, toPosix } = require("../../../lib/utils/glob");

describe("globToRegExp", () => {
  const cases = [
    // [glob, input, expected]
    ["src/*.js", "src/order.js", true],
    ["src/*.js", "src/domain/order.js", false],
    ["src/**/*.js", "src/order.js", true],
    ["src/**/*.js", "src/a/b/c/order.js", true],
    ["src/**", "src/a/b", true],
    ["**/ui/**", "../../ui/button.js", true],
    ["**/ui/**", "./build/guide.js", false],
    ["file?.js", "file1.js", true],
    ["file?.js", "file10.js", false],
    // Regex metacharacters are literal.
    ["lodash.merge", "lodash.merge", true],
    ["lodash.merge", "lodashXmerge", false],
    ["(a)+[b]", "(a)+[b]", true],
  ];

  for (const [glob, input, expected] of cases) {
    it(`${JSON.stringify(glob)} ${expected ? "matches" : "does not match"} ${JSON.stringify(input)}`, () => {
      assert.equal(globToRegExp(glob).test(input), expected);
    });
  }
});

describe("createMatcher", () => {
  it("matches when any glob matches", () => {
    const matches = createMatcher(["react", "react-dom/*"]);
    assert.equal(matches("react"), true);
    assert.equal(matches("react-dom/client"), true);
    assert.equal(matches("preact"), false);
  });

  it("matches nothing for an empty list", () => {
    assert.equal(createMatcher([])("anything"), false);
  });
});

describe("toPosix", () => {
  it("converts Windows separators", () => {
    assert.equal(toPosix("src\\infra\\fs.js"), "src/infra/fs.js");
  });
});
