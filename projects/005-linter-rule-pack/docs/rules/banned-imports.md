# rule-pack/banned-imports

Disallow specific modules, specific named imports, or groups of modules, with per-entry
allow-lists. Not in `recommended`, because it needs project-specific options.

## Why

- **Architecture boundaries.** The domain layer must not import UI code or frameworks.
- **Deprecations.** `moment` is banned; the message says to use `date-fns`.
- **Narrow bans.** `lodash` is fine, but `merge` (deep merge of untrusted input) is not.
- **Controlled exceptions.** `node:fs` only inside `src/infra/**`.

## What it detects

Every way a module enters a file:

```js
import x from "m";                 // static import (default, named, namespace)
export { a } from "m";             // re-export
export * from "m";
await import("m");                 // dynamic import with a static string
const x = require("m");            // CommonJS, unless `require` is a local binding
const { a } = require("m");        // destructured names are checked against importNames
```

Specifiers built at runtime (`require(name)`) cannot be checked statically and are skipped.

## Options

```js
"rule-pack/banned-imports": ["error", {
  paths: [
    { name: "moment", message: "Use date-fns instead." },
    { name: "lodash", importNames: ["merge"] },
    { name: "node:fs", allowIn: ["src/infra/**"] },
  ],
  patterns: [
    { group: ["**/ui/**", "react", "react-dom/*"], message: "The domain must not depend on the UI." },
  ],
}]
```

- `paths[].name` matches the specifier **exactly**. Use `patterns` for subpaths.
- `paths[].importNames` bans only those exports. `default` means the default import.
  A namespace import (`import * as _`), `export *`, dynamic `import()` or a plain
  `require()` brings in the whole module, so it is reported too.
- `patterns[].group` is a list of globs matched against the specifier: `*` (one segment),
  `**` (any depth), `?` (one character).
- `allowIn` is a list of globs matched against the linted file's path relative to the
  ESLint working directory. The entry does not apply inside those files.
- `message` is appended to the report.

## Compared with core `no-restricted-imports`

Core covers ES imports only; this rule also covers `require()` (with destructured names)
and dynamic `import()`, and it supports per-entry `allowIn`, which otherwise needs a
separate config block per exception.
