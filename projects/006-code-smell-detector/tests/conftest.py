"""Shared helpers: analyse dedented source snippets with chosen thresholds."""

import textwrap

import pytest

from smell_detector import Analyzer, Config, Finding


def findings_for(code: str, rule: str | None = None, **config) -> list[Finding]:
    report = Analyzer(Config(**config)).analyze_source(textwrap.dedent(code), "sample.py")
    return [f for f in report.findings if rule is None or f.rule == rule]


@pytest.fixture
def write(tmp_path):
    """Write dedented files under tmp_path and return the root."""

    def _write(files: dict[str, str]):
        for name, code in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(code), encoding="utf-8")
        return tmp_path

    return _write
