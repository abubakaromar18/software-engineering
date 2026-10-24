"""Specification tests: one readable test per business rule.

Where the characterization tests say "same as before", these say *why*, and
they cover the new Conjured behaviour that legacy never had.
"""

import pytest

from gilded_rose.inventory import AGED_BRIE, BACKSTAGE_PASS, SULFURAS, GildedRose, RuleBook, named
from gilded_rose.item import Item
from gilded_rose.rules import LegendaryRule, lower_quality, raise_quality


def after_one_day(name, sell_in, quality):
    item = Item(name, sell_in, quality)
    GildedRose([item]).update_quality()
    return item.sell_in, item.quality


class TestStandardItems:
    def test_sell_in_and_quality_drop_by_one(self):
        assert after_one_day("Vest", 10, 20) == (9, 19)

    def test_quality_degrades_twice_as_fast_after_sell_by(self):
        assert after_one_day("Vest", 0, 20) == (-1, 18)

    def test_quality_never_goes_negative(self):
        assert after_one_day("Vest", 0, 1) == (-1, 0)
        assert after_one_day("Vest", 5, 0) == (4, 0)


class TestAgedBrie:
    def test_increases_in_quality(self):
        assert after_one_day(AGED_BRIE, 2, 0) == (1, 1)

    def test_increases_twice_as_fast_after_sell_by(self):
        assert after_one_day(AGED_BRIE, 0, 10) == (-1, 12)

    def test_quality_caps_at_fifty(self):
        assert after_one_day(AGED_BRIE, 0, 49) == (-1, 50)
        assert after_one_day(AGED_BRIE, 5, 50) == (4, 50)


class TestSulfuras:
    @pytest.mark.parametrize("sell_in", [5, 0, -1])
    def test_never_changes(self, sell_in):
        assert after_one_day(SULFURAS, sell_in, 80) == (sell_in, 80)


class TestBackstagePasses:
    @pytest.mark.parametrize(
        "sell_in, expected_quality",
        [(11, 21), (10, 22), (6, 22), (5, 23), (1, 23)],
    )
    def test_quality_rises_faster_as_concert_approaches(self, sell_in, expected_quality):
        assert after_one_day(BACKSTAGE_PASS, sell_in, 20) == (sell_in - 1, expected_quality)

    def test_worthless_after_the_concert(self):
        assert after_one_day(BACKSTAGE_PASS, 0, 40) == (-1, 0)

    def test_quality_caps_at_fifty(self):
        assert after_one_day(BACKSTAGE_PASS, 5, 49) == (4, 50)


class TestConjuredItems:
    def test_degrade_twice_as_fast_as_standard(self):
        assert after_one_day("Conjured Mana Cake", 3, 6) == (2, 4)

    def test_degrade_four_per_day_after_sell_by(self):
        assert after_one_day("Conjured Mana Cake", 0, 10) == (-1, 6)

    def test_quality_never_goes_negative(self):
        assert after_one_day("Conjured Mana Cake", 0, 3) == (-1, 0)


class TestQualityBounds:
    def test_over_cap_item_is_not_pulled_down_by_a_raise(self):
        item = Item("x", 0, 60)
        raise_quality(item, 3)
        assert item.quality == 60

    def test_negative_item_is_not_pushed_up_by_a_lowering(self):
        item = Item("x", 0, -4)
        lower_quality(item, 2)
        assert item.quality == -4


class TestRuleBook:
    def test_custom_catalog_extends_behaviour_without_editing_rules(self):
        frozen = RuleBook(catalog=[(named("Ice Statue"), LegendaryRule())])
        item = Item("Ice Statue", 3, 30)
        GildedRose([item], rule_book=frozen).update_quality()
        assert (item.sell_in, item.quality) == (3, 30)

    def test_unknown_items_fall_back_to_standard_rule(self):
        assert after_one_day("Mystery Box", 1, 1) == (0, 0)
