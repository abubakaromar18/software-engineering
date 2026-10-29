"""Command-line entry point.

Exit codes follow linter conventions so the tool can gate CI:

* 0 - no findings at or above ``--fail-on`` (default: low, i.e. any finding)
* 1 - at least one such finding
* 2 - usage or configuration error, or a path that doesn't exist
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from smell_detector import __version__
from smell_detector.analyzer import Analyzer
from smell_detector.config import Config, ConfigError
from smell_detector.models import Severity
from smell_detector.reporting import FORMATTERS

EXIT_CLEAN, EXIT_FINDINGS, EXIT_ERROR = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smell-detector",
        description="Find long methods, deep nesting, large classes and duplicate blocks.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="files or directories to scan")
    parser.add_argument("--format", choices=sorted(FORMATTERS), default="text")
    parser.add_argument(
        "--config",
        type=Path,
        help="pyproject.toml to read [tool.smell-detector] from "
        "(default: nearest one above the first path)",
    )
    parser.add_argument(
        "--min-severity",
        type=Severity.parse,
        default=Severity.LOW,
        metavar="{low,medium,high}",
        help="hide findings below this severity",
    )
    parser.add_argument(
        "--fail-on",
        type=Severity.parse,
        default=Severity.LOW,
        metavar="{low,medium,high}",
        help="exit 1 only if a finding at or above this severity remains",
    )
    thresholds = parser.add_argument_group("threshold overrides")
    thresholds.add_argument("--max-function-lines", type=int)
    thresholds.add_argument("--max-nesting-depth", type=int)
    thresholds.add_argument("--max-class-methods", type=int)
    thresholds.add_argument("--max-class-lines", type=int)
    thresholds.add_argument("--duplicate-min-statements", type=int)
    thresholds.add_argument("--duplicate-min-lines", type=int)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def load_config(args: argparse.Namespace) -> Config:
    base = Config.from_pyproject(args.config) if args.config else Config.discover(args.paths[0])
    return base.with_overrides(
        max_function_lines=args.max_function_lines,
        max_nesting_depth=args.max_nesting_depth,
        max_class_methods=args.max_class_methods,
        max_class_lines=args.max_class_lines,
        duplicate_min_statements=args.duplicate_min_statements,
        duplicate_min_lines=args.duplicate_min_lines,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args)
        report = Analyzer(config).analyze_paths(args.paths)
    except (ConfigError, FileNotFoundError) as exc:
        print(f"smell-detector: error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    visible = report.at_or_above(args.min_severity)
    sys.stdout.write(FORMATTERS[args.format](visible))
    failing = any(f.severity >= args.fail_on for f in visible.findings)
    return EXIT_FINDINGS if failing else EXIT_CLEAN
