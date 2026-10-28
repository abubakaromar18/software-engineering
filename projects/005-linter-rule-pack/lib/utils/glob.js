"use strict";

/**
 * A deliberately small glob matcher, so the plugin has no runtime dependencies.
 *
 * Supported syntax (the subset that import specifiers and file paths need):
 *   **   any number of path segments, including none
 *   *    any characters except "/"
 *   ?    exactly one character except "/"
 * Everything else matches literally. Paths are compared in POSIX form.
 */

const REGEXP_SPECIALS = /[.+^${}()|[\]\\]/g;
const GLOBSTAR = "**";
const GLOBSTAR_SEGMENT = "**/";

/**
 * Compile a glob into an anchored regular expression.
 * @param {string} glob
 * @returns {RegExp}
 */
function globToRegExp(glob) {
  let source = "";
  let i = 0;
  while (i < glob.length) {
    if (glob.startsWith(GLOBSTAR_SEGMENT, i)) {
      // "**/" may match zero segments: "src/**/x" matches "src/x".
      source += "(?:.*/)?";
      i += GLOBSTAR_SEGMENT.length;
    } else if (glob.startsWith(GLOBSTAR, i)) {
      source += ".*";
      i += GLOBSTAR.length;
    } else {
      const char = glob[i];
      if (char === "*") {
        source += "[^/]*";
      } else if (char === "?") {
        source += "[^/]";
      } else {
        source += char.replace(REGEXP_SPECIALS, "\\$&");
      }
      i += 1;
    }
  }
  return new RegExp(`^${source}$`);
}

/**
 * Build a predicate that is true when the input matches any of the globs.
 * @param {string[]} globs
 * @returns {(input: string) => boolean}
 */
function createMatcher(globs) {
  const expressions = globs.map(globToRegExp);
  return (input) => expressions.some((expression) => expression.test(input));
}

/**
 * Convert an OS path to POSIX separators so globs behave the same on Windows.
 * @param {string} filePath
 * @returns {string}
 */
function toPosix(filePath) {
  return filePath.split("\\").join("/");
}

module.exports = { globToRegExp, createMatcher, toPosix };
