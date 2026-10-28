"use strict";

/**
 * Flags unexplained numeric literals in business logic.
 *
 * Unlike ESLint's core `no-magic-numbers`, this rule is designed to be applied
 * to a *layer* (e.g. `src/domain/**`) and is opinionated about where a number
 * is acceptable: only as the value of a named constant, so that the business
 * meaning ("FREE_SHIPPING_THRESHOLD") is written down exactly once.
 */

const { docsUrl } = require("../utils/docs");

const DEFAULT_CONSTANT_PATTERN = "^[A-Z][A-Z0-9_]*$";

/** @type {import("eslint").Rule.RuleModule} */
module.exports = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Disallow magic numbers in business logic; require named constants instead",
      recommended: true,
      url: docsUrl("no-magic-numbers-in-business-logic"),
    },
    schema: [
      {
        type: "object",
        properties: {
          allow: { type: "array", items: { type: "number" }, uniqueItems: true },
          constantPattern: { type: "string" },
          ignoreArrayIndexes: { type: "boolean" },
          ignoreDefaultParams: { type: "boolean" },
        },
        additionalProperties: false,
      },
    ],
    defaultOptions: [
      {
        allow: [-1, 0, 1],
        constantPattern: DEFAULT_CONSTANT_PATTERN,
        ignoreArrayIndexes: true,
        ignoreDefaultParams: false,
      },
    ],
    messages: {
      magicNumber:
        "Magic number {{raw}} in business logic. Extract it into a named constant that says what it means.",
    },
  },

  create(context) {
    const [options] = context.options;
    const allowed = new Set(options.allow);
    const constantName = new RegExp(options.constantPattern);

    /** Is `node` the value of a constant whose name matches the pattern? */
    function isNamedConstantValue(node) {
      let current = node;
      // Walk up through containers that keep the value "part of" the constant:
      // `const RATES = Object.freeze({ gold: [0.2] })`.
      for (;;) {
        const parent = current.parent;
        if (parent.type === "ArrayExpression") {
          current = parent;
        } else if (parent.type === "Property" && parent.value === current) {
          current = parent.parent; // the ObjectExpression
        } else if (isObjectFreezeArgument(parent, current)) {
          current = parent;
        } else {
          return isConstantDeclarator(parent, current);
        }
      }
    }

    function isConstantDeclarator(parent, child) {
      if (parent.type === "VariableDeclarator" && parent.init === child) {
        return (
          parent.parent.kind === "const" &&
          parent.id.type === "Identifier" &&
          constantName.test(parent.id.name)
        );
      }
      // `static readonly`-style class constants: `static TAX_RATE = 0.2;`
      if (parent.type === "PropertyDefinition" && parent.value === child) {
        return parent.static && parent.key.type === "Identifier" && constantName.test(parent.key.name);
      }
      return false;
    }

    function isObjectFreezeArgument(parent, child) {
      return (
        parent.type === "CallExpression" &&
        parent.arguments[0] === child &&
        parent.callee.type === "MemberExpression" &&
        parent.callee.object.type === "Identifier" &&
        parent.callee.object.name === "Object" &&
        parent.callee.property.type === "Identifier" &&
        parent.callee.property.name === "freeze"
      );
    }

    /** `parseInt(value, 10)` / `Number.parseInt(value, 16)`: the radix is not business logic. */
    function isRadixArgument(node) {
      const parent = node.parent;
      if (parent.type !== "CallExpression" || parent.arguments[1] !== node) {
        return false;
      }
      const callee = parent.callee;
      if (callee.type === "Identifier") {
        return callee.name === "parseInt";
      }
      return (
        callee.type === "MemberExpression" &&
        callee.object.type === "Identifier" &&
        callee.object.name === "Number" &&
        callee.property.type === "Identifier" &&
        callee.property.name === "parseInt"
      );
    }

    function isIgnoredByPosition(node) {
      const parent = node.parent;
      if (parent.type === "Property" && parent.key === node) {
        return true; // `{ 404: "Not found" }` is a key, not a quantity
      }
      if (options.ignoreArrayIndexes && parent.type === "MemberExpression" && parent.computed && parent.property === node) {
        return true;
      }
      if (options.ignoreDefaultParams && parent.type === "AssignmentPattern" && parent.right === node) {
        return true;
      }
      return isRadixArgument(node) || isNamedConstantValue(node);
    }

    return {
      Literal(literal) {
        const isNumber = typeof literal.value === "number";
        const isBigInt = typeof literal.bigint === "string";
        if (!isNumber && !isBigInt) {
          return;
        }

        // Treat `-5` as one number, so `allow: [-1]` and the report location work.
        const parent = literal.parent;
        const isSigned = parent.type === "UnaryExpression" && (parent.operator === "-" || parent.operator === "+");
        const node = isSigned ? parent : literal;
        const sign = isSigned && parent.operator === "-" ? -1 : 1;
        const value = sign * Number(isBigInt ? literal.bigint : literal.value);
        const raw = isSigned && parent.operator === "-" ? `-${literal.raw}` : literal.raw;

        if (allowed.has(value) || isIgnoredByPosition(node)) {
          return;
        }

        context.report({
          node,
          messageId: "magicNumber",
          data: { raw },
        });
      },
    };
  },
};
