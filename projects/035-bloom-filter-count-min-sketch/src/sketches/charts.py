"""Dependency-free terminal rendering: aligned tables and grouped bar charts.

Charts are plain strings so they can be printed, written to a file, pasted
into a README, or asserted on in tests.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

GLYPHS = ("█", "▓", "░", "▒")


def table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    """Render ``rows`` under ``headers`` with right-aligned columns."""
    cells = [[str(h) for h in headers]] + [[str(c) for c in row] for row in rows]
    if any(len(row) != len(headers) for row in cells):
        raise ValueError("every row must have one cell per header")
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]

    def line(row: Sequence[str]) -> str:
        return "  ".join(cell.rjust(width) for cell, width in zip(row, widths))

    rule = "  ".join("-" * width for width in widths)
    return "\n".join([line(cells[0]), rule, *(line(row) for row in cells[1:])])


def _scaler(values: Sequence[float], width: int, log_scale: bool):
    positive = [v for v in values if v > 0]
    if not positive:
        return lambda value: 0
    high = max(positive)
    if not log_scale:
        return lambda value: round(max(value, 0) / high * width)
    # Log axis anchored one decade below the smallest positive value, so the
    # smallest bar is still visible and every decade gets equal width.
    low = math.floor(math.log10(min(positive))) - 1
    span = max(math.log10(high) - low, 1e-12)
    return lambda value: 0 if value <= 0 else max(1, round((math.log10(value) - low) / span * width))


def bar_chart(
    title: str,
    labels: Sequence[str],
    series: Mapping[str, Sequence[float]],
    *,
    width: int = 40,
    log_scale: bool = False,
    value_format: str = "{:.4g}",
) -> str:
    """Render a horizontal grouped bar chart.

    ``series`` maps a legend name to one value per label. With ``log_scale``
    the bars are proportional to ``log10(value)``, which is the only readable
    way to compare error rates spanning several orders of magnitude.
    """
    if width < 1:
        raise ValueError("width must be at least 1")
    if not series:
        raise ValueError("at least one series is required")
    if len(series) > len(GLYPHS):
        raise ValueError(f"at most {len(GLYPHS)} series are supported")
    for name, values in series.items():
        if len(values) != len(labels):
            raise ValueError(f"series {name!r} has {len(values)} values for {len(labels)} labels")

    all_values = [v for values in series.values() for v in values]
    scale = _scaler(all_values, width, log_scale)
    label_width = max((len(label) for label in labels), default=0)
    name_width = max(len(name) for name in series)

    lines = [title + (" (log scale)" if log_scale else "")]
    for index, label in enumerate(labels):
        for position, (glyph, (name, values)) in enumerate(zip(GLYPHS, series.items())):
            value = values[index]
            prefix = label.rjust(label_width) if position == 0 else " " * label_width
            bar = glyph * scale(value)
            lines.append(f"{prefix}  {name.ljust(name_width)} │{bar} {value_format.format(value)}")
    return "\n".join(lines)
