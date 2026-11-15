"""Stateful (model-based) test of RangeSet.

Hypothesis generates whole *programs*: random sequences of add/remove/query
calls. After every step the real RangeSet is compared with a trivially
correct model (a Python ``set`` of days), and its structural invariant is
checked. When a sequence fails, Hypothesis shrinks it to the shortest
program that still fails, which reads like a hand-written bug report.
"""

from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from pbtlab import strategies as pst
from pbtlab.dateranges import RangeSet, merge


class RangeSetMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.real = RangeSet()
        self.model: set = set()

    @rule(span=pst.date_ranges())
    def add(self, span):
        self.real.add(span)
        self.model |= set(span)

    @rule(span=pst.date_ranges())
    def remove(self, span):
        self.real.remove(span)
        self.model -= set(span)

    @precondition(lambda self: self.model)
    @rule(data=st.data())
    def remove_exactly_one_stored_range(self, data):
        """Targets the split-in-the-middle logic by reusing a stored boundary."""
        stored = data.draw(st.sampled_from(self.real.ranges))
        self.real.remove(stored)
        self.model -= set(stored)

    @rule(day=pst.dates)
    def membership_agrees(self, day):
        assert (day in self.real) == (day in self.model)

    @invariant()
    def same_days(self):
        assert {d for r in self.real.ranges for d in r} == self.model

    @invariant()
    def total_days_agrees(self):
        assert self.real.total_days == len(self.model)

    @invariant()
    def ranges_are_canonical(self):
        assert list(self.real.ranges) == merge(self.real.ranges)


TestRangeSet = RangeSetMachine.TestCase
