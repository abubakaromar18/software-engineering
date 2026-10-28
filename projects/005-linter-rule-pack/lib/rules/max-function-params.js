"use strict";

/**
 * Limits how many positional parameters a function may declare.
 *
 * Long parameter lists are a code smell: call sites become order-dependent
 * (`createUser("a", "b", true, false, 3)`) and every new argument is a
 * breaking change. The report highlights only the *excess* parameters and
 * suggests the usual refactoring, an options object.
 */

const { docsUrl } = require("../utils/docs");
const { getFunctionName, isIIFE } = require("../utils/ast");

const DEFAULT_MAX_PARAMS = 3;

/** @type {import("eslint").Rule.RuleModule} */
module.exports = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Enforce a maximum number of parameters in function definitions",
      recommended: true,
      url: docsUrl("max-function-params"),
    },
    schema: [
      {
        type: "object",
        properties: {
          max: { type: "integer", minimum: 0 },
          ignoreIIFE: { type: "boolean" },
          countDestructured: { enum: ["as-one", "per-property"] },
        },
        additionalProperties: false,
      },
    ],
    defaultOptions: [{ max: DEFAULT_MAX_PARAMS, ignoreIIFE: false, countDestructured: "as-one" }],
    messages: {
      tooMany:
        "{{name}} has {{count}} parameters (maximum allowed is {{max}}). Group related parameters into an options object.",
    },
  },

  create(context) {
    const [{ max, ignoreIIFE, countDestructured }] = context.options;

    /**
     * Number of parameters a param node contributes.
     * With "per-property", `({ a, b, c })` counts as 3: destructuring hides the
     * call-site problem but not the "this function knows too much" problem.
     */
    function weightOf(param) {
      const pattern = param.type === "AssignmentPattern" ? param.left : param;
      if (countDestructured === "per-property" && pattern.type === "ObjectPattern") {
        return Math.max(1, pattern.properties.length);
      }
      return 1;
    }

    function check(node) {
      if (ignoreIIFE && isIIFE(node)) {
        return;
      }
      // Setters take exactly one argument by definition; nothing to refactor.
      if (node.parent.type === "MethodDefinition" && node.parent.kind === "set") {
        return;
      }

      let count = 0;
      let firstExcess = null;
      for (const param of node.params) {
        count += weightOf(param);
        if (count > max && firstExcess === null) {
          firstExcess = param;
        }
      }
      if (count <= max) {
        return;
      }

      const lastParam = node.params[node.params.length - 1];
      context.report({
        node,
        loc: { start: firstExcess.loc.start, end: lastParam.loc.end },
        messageId: "tooMany",
        data: { name: getFunctionName(node), count, max },
      });
    }

    return {
      FunctionDeclaration: check,
      FunctionExpression: check,
      ArrowFunctionExpression: check,
    };
  },
};
