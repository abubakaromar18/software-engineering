// Package all enables every bundled payment adapter. Import it for its side
// effects:
//
//	import _ ".../plugins/all"
//
// A binary that needs only one provider can blank-import that adapter alone,
// keeping the other vendors' code out of the build entirely.
package all

import (
	_ "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/adapters/ledgerly"
	_ "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/adapters/quickcoin"
	_ "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/adapters/swiftpay"
)
