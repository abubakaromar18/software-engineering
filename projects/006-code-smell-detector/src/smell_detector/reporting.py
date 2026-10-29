"""Render a ``Report`` for humans (text) or machines (JSON).

Reporters are pure functions from ``Report`` to ``str``; the CLI decides where
the output goes. New formats (SARIF, Markdown) slot in by adding a function to
``FORMATTERS``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from smell_detector.models import Finding, Report, Severity

HOTSPOT_COUNT = 5


def format_text(report: Report) -> str:
    lines: list[str] = []
    for finding in report.findings:
        lines.append(
            f"{finding.location}: {finding.severity.name:<6} {finding.score:>3}  "
            f"[{finding.rule}] {finding.message}"
        )
    for error in report.errors:
        lines.append(f"{error.path}: ERROR  {error.message}")
    if lines:
        lines.append("")
    lines.append(_summary(report))
    hotspots = _hotspots(report.findings)
    if len(hotspots) > 1:
        lines.append("Hotspots (files by total smell score):")
        lines.extend(f"  {total:>4}  {path}" for path, total in hotspots)
    return "\n".join(lines) + "\n"


def format_json(report: Report) -> str:
    payload = {
        "summary": {
            "files_analyzed": report.files_analyzed,
            "findings": len(report.findings),
            "by_severity": {str(s): n for s, n in report.count_by_severity().items()},
        },
        "findings": [_finding_dict(f) for f in report.findings],
        "errors": [{"path": str(e.path), "message": e.message} for e in report.errors],
    }
    return json.dumps(payload, indent=2) + "\n"


FORMATTERS: dict[str, Callable[[Report], str]] = {"text": format_text, "json": format_json}


def _summary(report: Report) -> str:
    counts = report.count_by_severity()
    noun = "finding" if len(report.findings) == 1 else "findings"
    files = "file" if report.files_analyzed == 1 else "files"
    breakdown = ", ".join(f"{s}: {counts[s]}" for s in sorted(Severity, reverse=True))
    text = f"{len(report.findings)} {noun} in {report.files_analyzed} {files} ({breakdown})"
    if report.errors:
        text += f"; {len(report.errors)} file(s) could not be parsed"
    return text


def _hotspots(findings: tuple[Finding, ...]) -> list[tuple[Path, int]]:
    totals: dict[Path, int] = defaultdict(int)
    for finding in findings:
        totals[finding.location.path] += finding.score
    ranked = sorted(totals.items(), key=lambda item: (-item[1], str(item[0])))
    return ranked[:HOTSPOT_COUNT]


def _finding_dict(finding: Finding) -> dict:
    loc = finding.location
    return {
        "rule": finding.rule,
        "path": str(loc.path),
        "line": loc.line,
        "end_line": loc.end_line,
        "symbol": finding.symbol,
        "message": finding.message,
        "metric": finding.metric,
        "threshold": finding.threshold,
        "score": finding.score,
        "severity": str(finding.severity),
        "related": [
            {"path": str(r.path), "line": r.line, "end_line": r.end_line} for r in finding.related
        ],
    }
