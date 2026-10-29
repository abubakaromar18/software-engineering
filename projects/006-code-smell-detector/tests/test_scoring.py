import pytest

from smell_detector.models import Severity
from smell_detector.scoring import score, severity_for


@pytest.mark.parametrize(
    ("metric", "threshold", "expected"),
    [(5, 10, 0), (10, 10, 0), (15, 10, 33), (20, 10, 50), (40, 10, 75), (10_000, 10, 100)],
)
def test_score_curve(metric, threshold, expected):
    assert score(metric, threshold) == expected


def test_score_is_monotonic():
    scores = [score(m, 10) for m in range(10, 200)]
    assert scores == sorted(scores)


def test_score_rejects_non_positive_threshold():
    with pytest.raises(ValueError):
        score(5, 0)


@pytest.mark.parametrize(
    ("points", "severity"),
    [
        (0, Severity.LOW),
        (24, Severity.LOW),
        (25, Severity.MEDIUM),
        (49, Severity.MEDIUM),
        (50, Severity.HIGH),
    ],
)
def test_severity_bands(points, severity):
    assert severity_for(points) is severity


def test_severity_parse_and_order():
    assert Severity.parse(" High ") is Severity.HIGH
    assert Severity.HIGH > Severity.MEDIUM > Severity.LOW
    with pytest.raises(ValueError, match="unknown severity"):
        Severity.parse("critical")
