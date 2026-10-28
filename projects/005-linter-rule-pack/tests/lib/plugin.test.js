"use strict";

/**
 * Integration tests: load the plugin through the real ESLint API the way a
 * project would, with a flat config, rather than calling rules in isolation.
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { ESLint } = require("eslint");
const plugin = require("../../lib");

const ROOT = path.join(__dirname, "..", "..");

function lint(code, config, filePath = "src/domain/pricing.js") {
  const eslint = new ESLint({ cwd: ROOT, overrideConfigFile: true, overrideConfig: config });
  return eslint.lintText(code, { filePath: path.join(ROOT, filePath) }).then(([result]) => result);
}

describe("plugin", () => {
  it("exposes meta for config caching and --print-config", () => {
    assert.equal(plugin.meta.name, "eslint-plugin-rule-pack");
    assert.match(plugin.meta.version, /^\d+\.\d+\.\d+$/);
  });

  it("documents every rule with a description and a docs file that exists", () => {
    for (const [name, rule] of Object.entries(plugin.rules)) {
      assert.ok(rule.meta.docs.description, `${name} has a description`);
      assert.ok(rule.meta.docs.url.endsWith(`/docs/rules/${name}.md`), `${name} links to its docs`);
      assert.ok(fs.existsSync(path.join(ROOT, "docs", "rules", `${name}.md`)), `docs/rules/${name}.md exists`);
    }
  });

  it("recommended config enables only rules that work without options", async () => {
    const result = await lint(
      "export function quote(a, b, c, d) { return a * 1.2 + b + c + d; }",
      [plugin.configs.recommended],
    );
    const found = result.messages.map((m) => [m.ruleId, m.severity]);
    assert.deepEqual(found, [
      ["rule-pack/max-function-params", 1],
      ["rule-pack/no-magic-numbers-in-business-logic", 2],
    ]);
  });

  it("can scope rules to a layer with `files`, the intended setup", async () => {
    const config = [
      { files: ["src/domain/**/*.js"], ...plugin.configs.recommended },
    ];
    const domain = await lint("export const total = (x) => x * 1.2;", config, "src/domain/pricing.js");
    const ui = await lint("export const width = (x) => x * 1.2;", config, "src/ui/layout.js");
    assert.equal(domain.errorCount, 1);
    assert.equal(ui.errorCount + ui.warningCount, 0);
  });

  it("rejects invalid options through the rule schema", async () => {
    const config = [
      {
        plugins: { "rule-pack": plugin },
        rules: { "rule-pack/max-function-params": ["error", { max: "three" }] },
      },
    ];
    await assert.rejects(lint("function f() {}", config), /max-function-params/);
  });

  it("merges partial options with defaults", async () => {
    const config = [
      {
        plugins: { "rule-pack": plugin },
        rules: { "rule-pack/no-magic-numbers-in-business-logic": ["error", { ignoreDefaultParams: true }] },
      },
    ];
    // `allow` and `constantPattern` still have their defaults.
    const result = await lint("const MAX = 9; function f(n = 5) { return n + 1; }", config);
    assert.equal(result.errorCount, 0);
  });
});
