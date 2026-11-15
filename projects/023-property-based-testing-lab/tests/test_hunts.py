"""Meta-tests: every law must catch its specimen and pass on the real code.

This is a tiny version of mutation testing. A property that cannot tell a
known-buggy implementation from a correct one is not testing anything.
"""

import pytest
from hypothesis import given, settings

from pbtlab.hunts import HUNTS, main, run_hunt

ids = [h.name for h in HUNTS]


@pytest.mark.parametrize("hunt", HUNTS, ids=ids)
def test_law_catches_specimen(hunt):
    result = run_hunt(hunt, max_examples=3000)
    assert result.caught, f"{hunt.name}: law '{hunt.law_text}' never failed on the specimen"
    assert not hunt.holds(hunt.buggy, result.counterexample)


@pytest.mark.parametrize("hunt", HUNTS, ids=ids)
def test_law_holds_for_real_implementation(hunt):
    @settings(max_examples=300)
    @given(hunt.strategy)
    def check(example):
        assert hunt.holds(hunt.correct, example)

    check()


def test_shrinking_gives_minimal_counterexamples():
    by_name = {h.name: h for h in HUNTS}
    assert run_hunt(by_name["merge_sort_drops_tail"]).counterexample == [0, 0]
    assert run_hunt(by_name["zigzag_fixed64"]).counterexample == 2**63
    assert run_hunt(by_name["rle_naive"]).counterexample == "0"


def test_cli_lists_and_runs(capsys):
    assert main(["--list"]) == 0
    assert "zigzag_fixed64" in capsys.readouterr().out
    assert main(["merge_sort_unstable"]) == 0
    assert "1/1 specimens caught" in capsys.readouterr().out


def test_cli_rejects_unknown_hunt():
    with pytest.raises(SystemExit):
        main(["no_such_hunt"])
