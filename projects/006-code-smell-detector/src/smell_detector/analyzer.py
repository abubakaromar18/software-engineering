"""Orchestrates one analysis run: discover, parse, detect, collect.

The analyzer knows nothing about individual smells. It parses each file once,
hands the parsed ``SourceFile`` to every file-level detector, then gives the
whole set to project-level detectors. A file that fails to parse is recorded
as an error and the run continues, so one broken file can't hide the smells
in the other hundred.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from smell_detector.config import Config
from smell_detector.detectors import FileDetector, ProjectDetector, default_detectors
from smell_detector.discovery import find_python_files
from smell_detector.models import Finding, ParseError, Report
from smell_detector.source import SourceFile


class Analyzer:
    def __init__(
        self,
        config: Config | None = None,
        detectors: Sequence[FileDetector | ProjectDetector] | None = None,
    ) -> None:
        self.config = config or Config()
        self.detectors = (
            list(detectors) if detectors is not None else default_detectors(self.config)
        )

    def analyze_paths(self, paths: Iterable[Path | str]) -> Report:
        files = find_python_files((Path(p) for p in paths), self.config.exclude)
        sources: list[SourceFile] = []
        errors: list[ParseError] = []
        for path in files:
            try:
                sources.append(SourceFile.read(path))
            except SyntaxError as exc:
                errors.append(ParseError(path, f"syntax error at line {exc.lineno}: {exc.msg}"))
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(ParseError(path, f"cannot read file: {exc}"))
        return self.analyze_sources(sources, errors)

    def analyze_source(self, text: str, path: str = "<string>") -> Report:
        """Convenience for tests and editors: analyse code held in memory."""
        return self.analyze_sources([SourceFile.parse(Path(path), text)])

    def analyze_sources(
        self, sources: Sequence[SourceFile], errors: Sequence[ParseError] = ()
    ) -> Report:
        findings: list[Finding] = []
        for detector in self.detectors:
            if isinstance(detector, ProjectDetector):
                findings.extend(detector.check_project(sources))
            else:
                for source in sources:
                    findings.extend(detector.check(source))
        findings.sort(key=Finding.sort_key)
        return Report(tuple(findings), len(sources), tuple(errors))
