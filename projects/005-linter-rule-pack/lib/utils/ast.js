"use strict";

/**
 * Small AST helpers shared by the rules. ESLint's own `astUtils` are internal,
 * so the plugin carries the few it needs.
 */

/**
 * Best-effort human-readable name for a function node, used in messages.
 * @param {import("estree").Function} node
 * @returns {string}
 */
function getFunctionName(node) {
  if (node.id) {
    return `Function '${node.id.name}'`;
  }

  const parent = node.parent;
  if (parent.type === "VariableDeclarator" && parent.id.type === "Identifier") {
    return `Function '${parent.id.name}'`;
  }
  if (parent.type === "MethodDefinition" || parent.type === "Property" || parent.type === "PropertyDefinition") {
    const key = getStaticKeyName(parent.key, parent.computed);
    const kind = parent.type === "MethodDefinition" ? "Method" : "Function";
    return key ? `${kind} '${key}'` : `Anonymous ${kind.toLowerCase()}`;
  }
  if (parent.type === "AssignmentExpression" && parent.left.type === "Identifier") {
    return `Function '${parent.left.name}'`;
  }
  return node.type === "ArrowFunctionExpression" ? "Arrow function" : "Anonymous function";
}

/**
 * Name of a property key when it can be known without evaluating code.
 * @param {import("estree").Node} key
 * @param {boolean} computed
 * @returns {string | null}
 */
function getStaticKeyName(key, computed) {
  if (!computed && key.type === "Identifier") {
    return key.name;
  }
  if (key.type === "PrivateIdentifier") {
    return `#${key.name}`;
  }
  if (key.type === "Literal") {
    return String(key.value);
  }
  return null;
}

/**
 * Returns the string value of a module specifier node when it is static:
 * a string literal or a template literal without expressions.
 * @param {import("estree").Node | null | undefined} node
 * @returns {string | null}
 */
function getStaticString(node) {
  if (!node) {
    return null;
  }
  if (node.type === "Literal" && typeof node.value === "string") {
    return node.value;
  }
  if (node.type === "TemplateLiteral" && node.expressions.length === 0) {
    return node.quasis[0].value.cooked;
  }
  return null;
}

/**
 * True when `node` is a function that is invoked right where it is defined.
 * @param {import("estree").Function} node
 * @returns {boolean}
 */
function isIIFE(node) {
  const parent = node.parent;
  return parent.type === "CallExpression" && parent.callee === node;
}

module.exports = { getFunctionName, getStaticKeyName, getStaticString, isIIFE };
