"""Code Smell Detector: static analysis of Python source using the ``ast`` module.

The public API is intentionally small::

    from smell_detector import Analyzer, Config

    report = Analyzer(Config()).analyze_paths(["src/"])
    for finding in report.findings:
        print(finding.location, finding.message)
"""

from smell_detector.analyzer import Analyzer
from smell_detector.config import Config, ConfigError
from smell_detector.models import Finding, Location, Report, Severity

__all__ = [
    "Analyzer",
    "Config",
    "ConfigError",
    "Finding",
    "Location",
    "Report",
    "Severity",
]
__version__ = "1.0.0"
