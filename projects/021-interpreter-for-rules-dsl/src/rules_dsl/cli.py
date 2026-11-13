"""Command-line interface: ``rules-dsl {check,run,fmt,functions}``.

Exit codes: 0 success, 1 problems in the rules or facts, 2 usage or I/O errors.
Results go to stdout as JSON; human-oriented output (traces, diagnostics) goes
to stderr so the JSON can be piped.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from .analysis import Severity, check
from .engine import EngineConfig, ErrorPolicy, Outcome, RuleEngine, RuleStatus
from .errors import DslError
from .formatter import format_ruleset
from .functions import builtin_functions
from .parser import parse
from .source import Source
from .values import display

EXIT_OK, EXIT_PROBLEM, EXIT_USAGE = 0, 1, 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rules-dsl", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    check_cmd = commands.add_parser("check", help="statically check a ruleset")
    check_cmd.add_argument("rules", type=Path)

    run_cmd = commands.add_parser("run", help="evaluate a ruleset against JSON facts")
    run_cmd.add_argument("rules", type=Path)
    run_cmd.add_argument("--facts", type=Path, required=True, help="JSON file ('-' for stdin)")
    run_cmd.add_argument("--trace", action="store_true", help="print per-rule trace to stderr")
    run_cmd.add_argument(
        "--on-error", choices=[p.value for p in ErrorPolicy], default=ErrorPolicy.RAISE.value
    )

    fmt_cmd = commands.add_parser("fmt", help="print the ruleset in canonical form")
    fmt_cmd.add_argument("rules", type=Path)
    fmt_cmd.add_argument("--check", action="store_true", help="exit 1 if not already formatted")

    commands.add_parser("functions", help="list built-in functions")
    return parser


def _read_source(path: Path) -> Source:
    return Source(path.read_text(encoding="utf-8"), name=str(path))


def _cmd_check(args: argparse.Namespace, source: Source, out: TextIO, err: TextIO) -> int:
    diagnostics = check(parse(source), builtin_functions())
    for diagnostic in diagnostics:
        print(diagnostic.render(source), file=err)
    errors = sum(d.severity is Severity.ERROR for d in diagnostics)
    print(f"{errors} error(s), {len(diagnostics) - errors} warning(s)", file=out)
    return EXIT_PROBLEM if errors else EXIT_OK


def _print_trace(outcome: Outcome, err: TextIO) -> None:
    width = max((len(entry.rule) for entry in outcome.trace), default=0)
    for entry in outcome.trace:
        detail = ", ".join(f"{c.name} = {display(c.value)}" for c in entry.changes)
        if entry.status is RuleStatus.FAILED and entry.error is not None:
            detail = entry.error.message + (f" at {entry.error.span}" if entry.error.span else "")
        print(f"  {entry.status:<12} {entry.rule:<{width}}  {detail}".rstrip(), file=err)


def _cmd_run(args: argparse.Namespace, source: Source, out: TextIO, err: TextIO) -> int:
    raw = sys.stdin.read() if str(args.facts) == "-" else args.facts.read_text(encoding="utf-8")
    facts = json.loads(raw)
    engine = RuleEngine.from_source(source, config=EngineConfig(ErrorPolicy(args.on_error)))
    outcome = engine.evaluate(facts)
    if args.trace:
        _print_trace(outcome, err)
    json.dump(outcome.to_json(), out, indent=2)
    out.write("\n")
    return EXIT_PROBLEM if any(e.status is RuleStatus.FAILED for e in outcome.trace) else EXIT_OK


def _cmd_fmt(args: argparse.Namespace, source: Source, out: TextIO, err: TextIO) -> int:
    formatted = format_ruleset(parse(source))
    if args.check:
        if formatted != source.text:
            print(f"{source.name} is not formatted", file=err)
            return EXIT_PROBLEM
        return EXIT_OK
    out.write(formatted)
    return EXIT_OK


def _cmd_functions(
    args: argparse.Namespace, source: Source | None, out: TextIO, err: TextIO
) -> int:
    for spec in builtin_functions():
        print(f"{spec.name:<12} {spec.arity_text():<14} {spec.doc}", file=out)
    return EXIT_OK


COMMANDS = {"check": _cmd_check, "run": _cmd_run, "fmt": _cmd_fmt, "functions": _cmd_functions}


def main(
    argv: Sequence[str] | None = None, out: TextIO | None = None, err: TextIO | None = None
) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_parser().parse_args(argv)
    source: Source | None = None
    try:
        if getattr(args, "rules", None) is not None:
            source = _read_source(args.rules)
        return COMMANDS[args.command](args, source, out, err)
    except DslError as error:
        print(error.render(source), file=err)
        return EXIT_PROBLEM
    except json.JSONDecodeError as error:
        print(f"invalid JSON facts: {error}", file=err)
        return EXIT_USAGE
    except OSError as error:
        print(f"cannot read file: {error}", file=err)
        return EXIT_USAGE
