"use strict";

const rule = require("../../../lib/rules/max-function-params");
const { createRuleTester } = require("../../rule-tester");

const tooMany = (name, count, max = 3) => ({ messageId: "tooMany", data: { name, count, max } });

createRuleTester().run("max-function-params", rule, {
  valid: [
    "function createUser(name, email, role) {}",
    "const add = (a, b) => a + b;",
    "function create({ name, email, role, active, age }) {}",
    "function log(message, ...rest) {}",
    "class Box { set size(value) {} }",
    { code: "function f(a, b, c, d) {}", options: [{ max: 4 }] },
    { code: "function noop() {}", options: [{ max: 0 }] },
    { code: "(function (a, b, c, d) {})(1, 2, 3, 4);", options: [{ ignoreIIFE: true }] },
    { code: "((a, b, c, d) => a)(1, 2, 3, 4);", options: [{ ignoreIIFE: true }] },
    { code: "function f({ a, b }, c) {}", options: [{ countDestructured: "per-property" }] },
  ],

  invalid: [
    {
      code: "function createUser(name, email, role, active) {}",
      errors: [
        {
          ...tooMany("Function 'createUser'", 4),
          // Only the excess parameter is highlighted.
          line: 1,
          column: 40,
          endColumn: 46,
        },
      ],
    },
    {
      code: "const handler = (a, b, c, d, e) => {};",
      errors: [{ ...tooMany("Function 'handler'", 5), column: 27, endColumn: 31 }],
    },
    {
      code: "const api = { send(to, cc, bcc, body) {} };",
      errors: [tooMany("Function 'send'", 4)],
    },
    {
      code: "class Mailer { send(to, cc, bcc, body) {} }",
      errors: [tooMany("Method 'send'", 4)],
    },
    {
      code: "class Mailer { #send(to, cc, bcc, body) {} }",
      errors: [tooMany("Method '#send'", 4)],
    },
    {
      code: "exports.build = function (a, b, c, d) {};",
      errors: [tooMany("Anonymous function", 4)],
    },
    {
      code: "callback = function (a, b, c, d) {};",
      errors: [tooMany("Function 'callback'", 4)],
    },
    {
      code: "items.map((a, b, c, d) => a);",
      errors: [tooMany("Arrow function", 4)],
    },
    {
      code: "function f(a, b, c, ...rest) {}",
      errors: [tooMany("Function 'f'", 4)],
    },
    {
      code: "(function (a, b, c, d) {})(1, 2, 3, 4);",
      errors: [tooMany("Anonymous function", 4)],
    },
    {
      code: "function f(a) {}",
      options: [{ max: 0 }],
      errors: [tooMany("Function 'f'", 1, 0)],
    },
    {
      // Destructuring hides the long list at the call site but not in the function.
      code: "function f({ a, b, c } = {}, d) {}",
      options: [{ countDestructured: "per-property" }],
      errors: [{ ...tooMany("Function 'f'", 4), column: 30, endColumn: 31 }],
    },
  ],
});
