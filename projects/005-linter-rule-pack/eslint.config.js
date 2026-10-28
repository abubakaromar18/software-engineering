"use strict";

// The plugin lints itself: dogfooding catches rules that are too noisy to live with.
const js = require("@eslint/js");
const globals = require("globals");
const rulePack = require("./lib");

module.exports = [
  { ignores: ["examples/**", "node_modules/**"] },
  js.configs.recommended,
  {
    files: ["**/*.js"],
    languageOptions: { sourceType: "commonjs", globals: globals.node },
  },
  {
    files: ["lib/**/*.js"],
    ...rulePack.configs.recommended,
  },
];
