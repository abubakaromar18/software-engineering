"use strict";

const REPO_DOCS =
  "https://github.com/abubakaromar18/software-engineering/blob/main/projects/005-linter-rule-pack/docs/rules";

/**
 * Link shown by editors and `eslint --format` next to each report.
 * @param {string} ruleName
 * @returns {string}
 */
function docsUrl(ruleName) {
  return `${REPO_DOCS}/${ruleName}.md`;
}

module.exports = { docsUrl };
