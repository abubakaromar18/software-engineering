# rule-pack/max-function-params

Enforce a maximum number of parameters in function definitions.

⚠️ In `recommended` (as `warn`, `max: 3`).

## Why

A long positional parameter list makes every call site order-dependent and hard to read:

```js
createUser("Ada", "ada@example.com", "admin", true, false);   // what is `false`?
```

Each new parameter is a breaking change for every caller. The usual fix is an options object:

```js
createUser({ name: "Ada", email: "ada@example.com", role: "admin", active: true });
```

The report highlights only the parameters past the limit, so the fix location is obvious.

## Examples

```js
// ❌ max: 3
function createUser(name, email, role, active) {}
//                                     ^^^^^^ Function 'createUser' has 4 parameters (maximum allowed is 3).

// ✅
function createUser({ name, email, role, active }) {}
function log(message, ...rest) {}       // rest counts as one
class Box { set size(value) {} }        // setters are always ignored
```

## Options

```js
"rule-pack/max-function-params": ["warn", {
  max: 3,                       // integer >= 0
  ignoreIIFE: false,            // skip (function (a, b, c, d) {})(...)
  countDestructured: "as-one",  // or "per-property": ({ a, b, c }) counts as 3
}]
```

`per-property` is for teams that want to catch "options objects" that have grown into
a grab-bag: destructuring fixes the call site but not a function that knows too much.

Differences from core `max-params`: it reports the excess span rather than the whole
function, names methods and private methods in the message, ignores setters, and can
count destructured properties.
