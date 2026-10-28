"use strict";

/**
 * eslint-plugin-rule-pack: entry point.
 *
 * Exposes the rules and a flat-config preset. The preset references the
 * plugin object itself, so it is assembled after the object exists.
 */

const { name, version } = require("../package.json");

const plugin = {
  meta: { name, version },
  rules: {
    "banned-imports": require("./rules/banned-imports"),
    "max-function-params": require("./rules/max-function-params"),
    "no-magic-numbers-in-business-logic": require("./rules/no-magic-numbers-in-business-logic"),
  },
  configs: {},
};

// `banned-imports` is not in the preset: it does nothing without project-specific options.
plugin.configs.recommended = {
  name: "rule-pack/recommended",
  plugins: { "rule-pack": plugin },
  rules: {
    "rule-pack/max-function-params": "warn",
    "rule-pack/no-magic-numbers-in-business-logic": "error",
  },
};

module.exports = plugin;
