"""Golden-master (approval) test over the classic 30-day text fixture.

The approved file is the reviewed, accepted output. When behaviour changes on
purpose, regenerate it with ``APPROVE=1 pytest tests/test_golden_master.py``
and review the diff like any other code change.
"""

import os
from pathlib import Path

from gilded_rose.inventory import GildedRose
from gilded_rose.legacy import LegacyGildedRose
from gilded_rose.simulation import simulate

DAYS = 30
APPROVED = Path(__file__).parent / "approved" / "texttest_30_days.txt"


def render(factory):
    return "\n".join(simulate(factory, DAYS)) + "\n"


def test_output_matches_approved_golden_master():
    received = render(GildedRose)
    if os.environ.get("APPROVE") == "1":
        APPROVED.write_text(received, encoding="utf-8")
    assert received == APPROVED.read_text(encoding="utf-8")


def test_only_conjured_lines_differ_from_legacy():
    legacy_lines = render(LegacyGildedRose).splitlines()
    new_lines = render(GildedRose).splitlines()
    assert len(legacy_lines) == len(new_lines)
    differing = [new for old, new in zip(legacy_lines, new_lines) if old != new]
    assert differing, "the Conjured feature should change some lines"
    assert all(line.startswith("Conjured") for line in differing)
