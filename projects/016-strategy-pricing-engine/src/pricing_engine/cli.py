"""Command line entry point: price a JSON cart against JSON rules."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from .errors import PricingError
from .loader import cart_from_dict, engine_from_config
from .models import Quote


def _read_json(path: Path) -> Any:
    # parse_float keeps JSON numbers such as 19.99 exact.
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def render_receipt(quote: Quote) -> str:
    rows = [f"{'SKU':<14}{'QTY':>4}{'GROSS':>10}{'DISC':>9}{'TAX':>8}{'TOTAL':>10}"]
    for line in quote.lines:
        rows.append(
            f"{line.sku:<14}{line.quantity:>4}{line.gross:>10}"
            f"{line.discount:>9}{line.tax:>8}{line.total:>10}"
        )
    rows.append("")
    rows.append(f"{'Subtotal':<30}{quote.subtotal:>10}")
    rows.extend(f"  {d.rule:<28}{-d.amount:>10}" for d in quote.discounts)
    rows.append(f"{'Tax (' + quote.tax_rule + ')':<30}{quote.tax_total:>10}")
    rows.append(f"{'Total':<30}{quote.total:>10}")
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, required=True, help="path to rules JSON")
    parser.add_argument("--cart", type=Path, required=True, help="path to cart JSON")
    parser.add_argument("--json", action="store_true", help="print the quote as JSON")
    args = parser.parse_args(argv)

    try:
        engine = engine_from_config(_read_json(args.rules))
        quote = engine.quote(cart_from_dict(_read_json(args.cart)))
    except (PricingError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(quote.to_dict(), indent=2) if args.json else render_receipt(quote))
    return 0


if __name__ == "__main__":
    sys.exit(main())
