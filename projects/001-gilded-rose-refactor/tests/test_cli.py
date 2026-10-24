import pytest

from gilded_rose.__main__ import main
from gilded_rose.simulation import simulate
from gilded_rose.inventory import GildedRose


def test_cli_prints_requested_number_of_days(capsys):
    assert main(["--days", "1"]) == 0
    out = capsys.readouterr().out
    assert "-------- day 0 --------" in out
    assert "-------- day 1 --------" in out
    assert "day 2" not in out


def test_cli_legacy_flag_runs_legacy_engine(capsys):
    main(["--days", "1", "--legacy"])
    # Legacy treats Conjured goods as ordinary: 6 -> 5 rather than 6 -> 4.
    assert "Conjured Mana Cake, 2, 5" in capsys.readouterr().out


def test_cli_rejects_negative_days():
    with pytest.raises(SystemExit):
        main(["--days", "-1"])


def test_simulate_rejects_negative_days():
    with pytest.raises(ValueError):
        list(simulate(GildedRose, -1))
