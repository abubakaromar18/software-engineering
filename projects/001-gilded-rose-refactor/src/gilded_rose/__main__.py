"""Command-line entry point: ``python -m gilded_rose [--days N] [--legacy]``."""

import argparse
import sys
from typing import List, Optional

from gilded_rose.inventory import GildedRose
from gilded_rose.legacy import LegacyGildedRose
from gilded_rose.simulation import simulate


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gilded-rose", description="Simulate the Gilded Rose inventory day by day."
    )
    parser.add_argument("--days", type=int, default=2, help="days to simulate (default: 2)")
    parser.add_argument(
        "--legacy", action="store_true", help="run the original legacy implementation"
    )
    args = parser.parse_args(argv)
    if args.days < 0:
        parser.error("--days must be non-negative")
    return args


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    factory = LegacyGildedRose if args.legacy else GildedRose
    for line in simulate(factory, args.days):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
