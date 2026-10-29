"""Turn "measured X against limit Y" into a comparable 0-100 score.

Every rule measures something different (lines, depth, method count, clone
size), so raw numbers can't be ranked against each other. Instead each finding
is scored by its *relative excess* over the threshold::

    excess = (metric - threshold) / threshold
    score  = 100 * excess / (1 + excess)

The curve is 0 at the threshold, 50 at double the threshold and approaches 100
asymptotically, so one pathological 2,000-line function can't dwarf everything
else on a linear scale. Severity bands are cut from the same score.
"""

from smell_detector.models import Severity

MEDIUM_FROM = 25  # 1.33x the threshold
HIGH_FROM = 50  # 2x the threshold


def score(metric: int, threshold: int) -> int:
    """Score how far ``metric`` exceeds ``threshold``. Returns 0 if it doesn't."""
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    if metric <= threshold:
        return 0
    excess = (metric - threshold) / threshold
    return min(100, round(100 * excess / (1 + excess)))


def severity_for(points: int) -> Severity:
    if points >= HIGH_FROM:
        return Severity.HIGH
    if points >= MEDIUM_FROM:
        return Severity.MEDIUM
    return Severity.LOW
