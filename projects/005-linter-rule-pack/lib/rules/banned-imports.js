"use strict";

/**
 * Bans modules, specific named exports, or whole groups of modules, with an
 * optional per-rule file allow-list.
 *
 * Typical uses:
 *   - architectural boundaries: the domain layer may not import from `ui/**`
 *   - deprecations: `moment` is banned, use `date-fns`
 *   - narrow bans: `lodash` is fine, `lodash.merge` (prototype pollution) is not
 *   - controlled exceptions: `fs` is banned everywhere except `src/infra/**`
 *
 * It recognises every way a module can be pulled in: static `import`,
 * re-exports (`export ... from`), dynamic `import()`, and CommonJS `require()`.
 */

const path = require("node:path");
const { docsUrl } = require("../utils/docs");
const { getStaticKeyName, getStaticString } = require("../utils/ast");
const { createMatcher, toPosix } = require("../utils/glob");

const restrictionBase = {
  message: { type: "string" },
  allowIn: { type: "array", items: { type: "string" }, minItems: 1 },
};

/**
 * @typedef {{ name: string, node: import("estree").Node }} ImportedName
 * `null` instead of a list means "the whole module" (namespace import,
 * `export *`, dynamic import, plain `require`), which includes every name.
 * @typedef {ImportedName[] | null} ImportedNames
 */

/** @type {import("eslint").Rule.RuleModule} */
module.exports = {
  meta: {
    type: "problem",
    docs: {
      description: "Disallow specific modules, named imports, or module groups",
      recommended: false,
      url: docsUrl("banned-imports"),
    },
    schema: [
      {
        type: "object",
        properties: {
          paths: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string", minLength: 1 },
                importNames: { type: "array", items: { type: "string" }, minItems: 1, uniqueItems: true },
                ...restrictionBase,
              },
              required: ["name"],
              additionalProperties: false,
            },
          },
          patterns: {
            type: "array",
            items: {
              type: "object",
              properties: {
                group: { type: "array", items: { type: "string" }, minItems: 1 },
                ...restrictionBase,
              },
              required: ["group"],
              additionalProperties: false,
            },
          },
        },
        additionalProperties: false,
      },
    ],
    defaultOptions: [{ paths: [], patterns: [] }],
    messages: {
      bannedModule: "'{{source}}' is banned.{{reason}}",
      bannedName: "'{{name}}' from '{{source}}' is banned.{{reason}}",
      bannedNameViaWholeModule:
        "'{{source}}' is imported as a whole, which includes banned {{names}}. Import only what you need.{{reason}}",
      bannedPattern: "'{{source}}' matches banned pattern '{{pattern}}'.{{reason}}",
    },
  },

  create(context) {
    const [{ paths, patterns }] = context.options;
    const sourceCode = context.sourceCode;
    const relativeFile = toPosix(path.relative(context.cwd, context.filename));

    /** A restriction applies unless the current file is on its allow-list. */
    const appliesHere = (restriction) => !restriction.allowIn || !createMatcher(restriction.allowIn)(relativeFile);

    const activePaths = paths.filter(appliesHere);
    const activePatterns = patterns.filter(appliesHere).map((restriction) => ({
      ...restriction,
      globs: restriction.group.map((glob) => ({ glob, matches: createMatcher([glob]) })),
    }));

    if (activePaths.length === 0 && activePatterns.length === 0) {
      return {};
    }

    const reasonOf = (restriction) => (restriction.message ? ` ${restriction.message}` : "");

    /**
     * Central check every import form funnels into.
     * @param {import("estree").Node} node node to report on
     * @param {string} source module specifier
     * @param {ImportedNames} importedNames
     */
    function check(node, source, importedNames) {
      for (const restriction of activePaths) {
        if (restriction.name !== source) {
          continue;
        }
        const reason = reasonOf(restriction);

        if (!restriction.importNames) {
          context.report({ node, messageId: "bannedModule", data: { source, reason } });
        } else if (importedNames === null) {
          const names = restriction.importNames.map((name) => `'${name}'`).join(", ");
          context.report({ node, messageId: "bannedNameViaWholeModule", data: { source, names, reason } });
        } else {
          for (const imported of importedNames) {
            if (restriction.importNames.includes(imported.name)) {
              context.report({
                node: imported.node,
                messageId: "bannedName",
                data: { name: imported.name, source, reason },
              });
            }
          }
        }
      }

      for (const restriction of activePatterns) {
        const hit = restriction.globs.find(({ matches }) => matches(source));
        if (hit) {
          context.report({
            node,
            messageId: "bannedPattern",
            data: { source, pattern: hit.glob, reason: reasonOf(restriction) },
          });
        }
      }
    }

    /** @returns {ImportedNames} */
    function namesFromImportDeclaration(node) {
      if (node.specifiers.some((specifier) => specifier.type === "ImportNamespaceSpecifier")) {
        return null;
      }
      return node.specifiers.map((specifier) => ({
        name:
          specifier.type === "ImportDefaultSpecifier"
            ? "default"
            : getStaticKeyName(specifier.imported, false),
        node: specifier,
      }));
    }

    /** `const { merge, pick: p } = require("lodash")` → merge, pick. @returns {ImportedNames} */
    function namesFromRequire(callNode) {
      const parent = callNode.parent;
      if (parent.type !== "VariableDeclarator" || parent.init !== callNode || parent.id.type !== "ObjectPattern") {
        return null;
      }
      const names = [];
      for (const property of parent.id.properties) {
        const name = property.type === "Property" ? getStaticKeyName(property.key, property.computed) : null;
        if (name === null) {
          return null; // `...rest` or a computed key: could be anything
        }
        names.push({ name, node: property });
      }
      return names;
    }

    /** `require` is only CommonJS `require` if no local binding shadows it. */
    function isGlobalRequire(node) {
      for (let scope = sourceCode.getScope(node); scope; scope = scope.upper) {
        const variable = scope.set.get("require");
        if (variable && variable.defs.length > 0) {
          return false;
        }
      }
      return true;
    }

    return {
      ImportDeclaration(node) {
        check(node, node.source.value, namesFromImportDeclaration(node));
      },
      ExportNamedDeclaration(node) {
        if (node.source) {
          const names = node.specifiers.map((specifier) => ({
            name: getStaticKeyName(specifier.local, false),
            node: specifier,
          }));
          check(node, node.source.value, names);
        }
      },
      ExportAllDeclaration(node) {
        check(node, node.source.value, null);
      },
      ImportExpression(node) {
        const source = getStaticString(node.source);
        if (source !== null) {
          check(node, source, null);
        }
      },
      CallExpression(node) {
        if (node.callee.type !== "Identifier" || node.callee.name !== "require") {
          return;
        }
        const source = getStaticString(node.arguments[0]);
        if (source !== null && isGlobalRequire(node)) {
          check(node, source, namesFromRequire(node));
        }
      },
    };
  },
};
