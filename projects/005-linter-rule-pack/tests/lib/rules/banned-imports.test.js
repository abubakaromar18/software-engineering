"use strict";

const path = require("node:path");
const rule = require("../../../lib/rules/banned-imports");
const { createRuleTester } = require("../../rule-tester");

const file = (relative) => path.join(process.cwd(), relative);

const MOMENT = { paths: [{ name: "moment", message: "Use date-fns instead." }] };
const LODASH_MERGE = { paths: [{ name: "lodash", importNames: ["merge", "default"] }] };
const DOMAIN_BOUNDARY = {
  patterns: [{ group: ["**/ui/**", "react"], message: "The domain layer must not depend on the UI." }],
};
const FS_ONLY_IN_INFRA = { paths: [{ name: "node:fs", allowIn: ["src/infra/**"] }] };

createRuleTester().run("banned-imports", rule, {
  valid: [
    // No options: nothing is banned.
    "import moment from 'moment';",
    { code: "import { format } from 'date-fns';", options: [MOMENT] },
    // Exact names only: a subpath is a different specifier (use patterns for those).
    { code: "import locale from 'moment/locale/de';", options: [MOMENT] },
    // Only the listed names are banned.
    { code: "import { pick, omit } from 'lodash';", options: [LODASH_MERGE] },
    { code: "const { pick } = require('lodash');", options: [LODASH_MERGE] },
    { code: "export { pick } from 'lodash';", options: [LODASH_MERGE] },
    // Side-effect import brings in no names.
    { code: "import 'lodash';", options: [LODASH_MERGE] },
    // Allow-list.
    { code: "import fs from 'node:fs';", options: [FS_ONLY_IN_INFRA], filename: file("src/infra/storage.js") },
    { code: "import fs from 'node:fs';", options: [FS_ONLY_IN_INFRA], filename: file("src/infra/disk/cache.js") },
    // A shadowed `require` is not CommonJS.
    { code: "function load(require) { return require('moment'); }", options: [MOMENT] },
    // Dynamic specifiers cannot be checked statically.
    { code: "const lib = 'moment'; import(lib); require(lib);", options: [MOMENT] },
    { code: "import { Order } from '../model/order.js';", options: [DOMAIN_BOUNDARY] },
  ],

  invalid: [
    {
      code: "import moment from 'moment';",
      options: [MOMENT],
      errors: [{ messageId: "bannedModule", data: { source: "moment", reason: " Use date-fns instead." }, line: 1 }],
    },
    {
      code: "const moment = require('moment');",
      options: [MOMENT],
      errors: [{ message: "'moment' is banned. Use date-fns instead." }],
    },
    {
      code: "const moment = require(`moment`);",
      options: [MOMENT],
      errors: [{ messageId: "bannedModule" }],
    },
    {
      code: "const lib = await import('moment');",
      options: [MOMENT],
      errors: [{ messageId: "bannedModule" }],
    },
    {
      code: "export * from 'moment';",
      options: [MOMENT],
      errors: [{ messageId: "bannedModule" }],
    },
    {
      code: "export { default } from 'moment';",
      options: [MOMENT],
      errors: [{ messageId: "bannedModule" }],
    },
    {
      // Each banned specifier is reported on its own location.
      code: "import _, { merge, pick } from 'lodash';",
      options: [LODASH_MERGE],
      errors: [
        { messageId: "bannedName", data: { name: "default", source: "lodash", reason: "" }, column: 8, endColumn: 9 },
        { messageId: "bannedName", data: { name: "merge", source: "lodash", reason: "" }, column: 13, endColumn: 18 },
      ],
    },
    {
      code: "import { merge as deepMerge } from 'lodash';",
      options: [LODASH_MERGE],
      errors: [{ message: "'merge' from 'lodash' is banned." }],
    },
    {
      code: "const { merge: m } = require('lodash');",
      options: [LODASH_MERGE],
      errors: [{ messageId: "bannedName", data: { name: "merge", source: "lodash", reason: "" } }],
    },
    {
      code: "export { merge } from 'lodash';",
      options: [LODASH_MERGE],
      errors: [{ messageId: "bannedName" }],
    },
    {
      // A namespace import includes everything, banned names too.
      code: "import * as _ from 'lodash';",
      options: [LODASH_MERGE],
      errors: [{ message: "'lodash' is imported as a whole, which includes banned 'merge', 'default'. Import only what you need." }],
    },
    {
      code: "const _ = require('lodash');",
      options: [LODASH_MERGE],
      errors: [{ messageId: "bannedNameViaWholeModule" }],
    },
    {
      code: "const { merge, ...rest } = require('lodash');",
      options: [LODASH_MERGE],
      errors: [{ messageId: "bannedNameViaWholeModule" }],
    },
    {
      code: "import { Button } from '../../ui/components/button.js';",
      options: [DOMAIN_BOUNDARY],
      errors: [
        {
          message:
            "'../../ui/components/button.js' matches banned pattern '**/ui/**'. The domain layer must not depend on the UI.",
        },
      ],
    },
    {
      code: "import React from 'react';",
      options: [DOMAIN_BOUNDARY],
      errors: [{ messageId: "bannedPattern", data: { source: "react", pattern: "react", reason: " The domain layer must not depend on the UI." } }],
    },
    {
      code: "import fs from 'node:fs';",
      options: [FS_ONLY_IN_INFRA],
      filename: file("src/domain/order.js"),
      errors: [{ messageId: "bannedModule" }],
    },
    {
      // Allow-lists match the whole relative path, not a substring.
      code: "import fs from 'node:fs';",
      options: [FS_ONLY_IN_INFRA],
      filename: file("lib/src/infra/storage.js"),
      errors: [{ messageId: "bannedModule" }],
    },
    {
      // A module banned by both a path and a pattern is reported by both.
      code: "import moment from 'moment';",
      options: [{ ...MOMENT, patterns: [{ group: ["mom*"] }] }],
      errors: [{ messageId: "bannedModule" }, { messageId: "bannedPattern" }],
    },
  ],
});
