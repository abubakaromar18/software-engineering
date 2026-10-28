"use strict";

/**
 * A realistic setup for a layered app:
 *   src/domain  business rules: no magic numbers, no UI or I/O imports
 *   src/infra   adapters: the only place allowed to touch the file system
 *   src/ui      presentation: layout numbers are fine here
 */

const rulePack = require("../lib");

// Flat config replaces a rule's options wholesale when a later block configures it
// again, so the domain block must repeat the shared bans rather than inherit them.
const SHARED_BANS = [
  { name: "moment", message: "Use date-fns instead." },
  { name: "lodash", importNames: ["merge"], message: "Deep-merging untrusted input enables prototype pollution." },
  { name: "node:fs", allowIn: ["src/infra/**"], message: "File access belongs in src/infra." },
];

module.exports = [
  {
    files: ["src/**/*.js"],
    plugins: { "rule-pack": rulePack },
    rules: {
      "rule-pack/max-function-params": ["warn", { max: 3 }],
      "rule-pack/banned-imports": ["error", { paths: SHARED_BANS }],
    },
  },
  {
    files: ["src/domain/**/*.js"],
    rules: {
      "rule-pack/no-magic-numbers-in-business-logic": "error",
      "rule-pack/banned-imports": [
        "error",
        {
          paths: SHARED_BANS,
          patterns: [{ group: ["**/ui/**", "react"], message: "The domain layer must not depend on the UI." }],
        },
      ],
    },
  },
];
