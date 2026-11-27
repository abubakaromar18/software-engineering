"""Command-line interface: run experiments and print tables, charts or CSV.

    sketches bloom    [--rates 0.1,0.01,0.001] [--capacity N] [--probes N]
    sketches overload [--rate P] [--capacity N] [--probes N]
    sketches cms      [--epsilons 0.01,0.002] [--delta D] [--length N] [--distinct N] [--skew S]
    sketches topk     [--k K] [--length N] [--distinct N] [--skew S]

All commands accept ``--seed`` (results are deterministic) and ``--csv``.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import asdict, fields
from typing import Any

from sketches.charts import bar_chart, table
from sketches.count_min import CountMinSketch, TopK
from sketches.experiments import (
    CmsTrial,
    run_bloom_accuracy,
    run_bloom_overload,
    run_cms_accuracy,
    zipf_stream,
)
from sketches.hashing import Hashable


def _float_list(text: str) -> list[float]:
    try:
        values = [float(part) for part in text.split(",") if part.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected comma-separated numbers, got {text!r}") from exc
    if not values or any(not 0 < v < 1 for v in values):
        raise argparse.ArgumentTypeError("values must be strictly between 0 and 1")
    return values


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got {text!r}") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return value


def _to_csv(records: Sequence[Any]) -> str:
    if not records:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[f.name for f in fields(records[0])], lineterminator="\n")
    writer.writeheader()
    writer.writerows(asdict(record) for record in records)
    return buffer.getvalue().rstrip("\n")


def _pct(value: float) -> str:
    return f"{value:.3%}"


def cmd_bloom(args: argparse.Namespace) -> str:
    trials = run_bloom_accuracy(args.rates, capacity=args.capacity, probes=args.probes, seed=args.seed)
    if args.csv:
        return _to_csv(trials)
    rows = [
        (_pct(t.target_rate), t.num_bits, t.num_hashes, f"{t.bits_per_item:.2f}",
         _pct(t.theoretical_rate), _pct(t.empirical_rate))
        for t in trials
    ]
    report = table(["target", "bits (m)", "hashes (k)", "bits/item", "theory", "measured"], rows)
    chart = bar_chart(
        f"False-positive rate at capacity ({args.capacity:,} items, {args.probes:,} probes)",
        [_pct(t.target_rate) for t in trials],
        {
            "target": [t.target_rate for t in trials],
            "measured": [t.empirical_rate for t in trials],
        },
        log_scale=True,
        value_format="{:.3%}",
    )
    return f"{report}\n\n{chart}"


def cmd_overload(args: argparse.Namespace) -> str:
    trials = run_bloom_overload(
        error_rate=args.rate, capacity=args.capacity, probes=args.probes, seed=args.seed
    )
    if args.csv:
        return _to_csv(trials)
    rows = [
        (f"{t.load_factor:.2f}x", t.items, _pct(t.theoretical_rate), _pct(t.estimated_rate),
         _pct(t.empirical_rate))
        for t in trials
    ]
    report = table(["load", "items", "theory", "from fill", "measured"], rows)
    chart = bar_chart(
        f"FPR as a {_pct(args.rate)} filter is overfilled (capacity {args.capacity:,})",
        [f"{t.load_factor:.2f}x" for t in trials],
        {"measured": [t.empirical_rate for t in trials]},
        value_format="{:.3%}",
    )
    return f"{report}\n\n{chart}"


def _mode(trial: CmsTrial) -> str:
    return "conservative" if trial.conservative else "standard"


def cmd_cms(args: argparse.Namespace) -> str:
    trials = run_cms_accuracy(
        args.epsilons,
        delta=args.delta,
        stream_length=args.length,
        distinct=args.distinct,
        skew=args.skew,
        seed=args.seed,
    )
    if args.csv:
        return _to_csv(trials)
    rows = [
        (t.epsilon, f"{t.width}x{t.depth}", _mode(t), f"{t.mean_error:.2f}", t.max_error,
         f"{t.error_bound:.0f}", _pct(t.within_bound), _pct(t.exact_fraction))
        for t in trials
    ]
    report = table(
        ["epsilon", "w x d", "update", "mean err", "max err", "eps*N", "within bound", "exact"],
        rows,
    )
    standard = [t for t in trials if not t.conservative]
    conservative = [t for t in trials if t.conservative]
    chart = bar_chart(
        f"Mean over-count per distinct item (N={args.length:,}, Zipf s={args.skew})",
        [f"eps={t.epsilon}" for t in standard],
        {
            "standard": [t.mean_error for t in standard],
            "conservative": [t.mean_error for t in conservative],
        },
        value_format="{:.2f}",
    )
    return f"{report}\n\n{chart}"


def cmd_topk(args: argparse.Namespace) -> str:
    stream = zipf_stream(args.length, args.distinct, args.skew, random.Random(args.seed))
    tracker = TopK(args.k, CountMinSketch.from_error(0.001, 0.01, seed=args.seed, conservative=True))
    tracker.update(stream)
    truth: Counter[Hashable] = Counter(stream)
    reported = tracker.items()
    actual_top = {item for item, _ in truth.most_common(args.k)}
    if args.csv:
        lines = ["rank,item,estimate,true_count"]
        lines += [f"{rank},{item!s},{est},{truth[item]}" for rank, (item, est) in enumerate(reported, 1)]
        return "\n".join(lines)
    rows = [(rank, item, est, truth[item]) for rank, (item, est) in enumerate(reported, 1)]
    recall = len(actual_top & {item for item, _ in reported}) / args.k
    sketch = tracker.sketch
    return (
        table(["rank", "item", "estimate", "true count"], rows)
        + f"\n\nrecall vs exact top-{args.k}: {recall:.0%}"
        + f"  |  sketch memory: {sketch.memory_bytes:,} bytes for {len(truth):,} distinct items"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sketches",
        description="Measure Bloom filters and Count-Min sketches against their theoretical error.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seed", type=int, default=0, help="hash and RNG seed (default 0)")
    common.add_argument("--csv", action="store_true", help="emit CSV instead of tables and charts")
    sub = parser.add_subparsers(dest="command", required=True)

    bloom = sub.add_parser("bloom", parents=[common], help="target vs measured FPR at capacity")
    bloom.add_argument("--rates", type=_float_list, default=[0.1, 0.05, 0.01, 0.001, 0.0001])
    bloom.add_argument("--capacity", type=_positive_int, default=10_000)
    bloom.add_argument("--probes", type=_positive_int, default=50_000)
    bloom.set_defaults(handler=cmd_bloom)

    overload = sub.add_parser("overload", parents=[common], help="FPR when filled past capacity")
    overload.add_argument("--rate", type=lambda t: _float_list(t)[0], default=0.01)
    overload.add_argument("--capacity", type=_positive_int, default=5_000)
    overload.add_argument("--probes", type=_positive_int, default=20_000)
    overload.set_defaults(handler=cmd_overload)

    cms = sub.add_parser("cms", parents=[common], help="Count-Min error, standard vs conservative")
    cms.add_argument("--epsilons", type=_float_list, default=[0.01, 0.005, 0.002, 0.001])
    cms.add_argument("--delta", type=lambda t: _float_list(t)[0], default=0.01)
    cms.add_argument("--length", type=_positive_int, default=100_000)
    cms.add_argument("--distinct", type=_positive_int, default=20_000)
    cms.add_argument("--skew", type=float, default=1.1)
    cms.set_defaults(handler=cmd_cms)

    topk = sub.add_parser("topk", parents=[common], help="heavy hitters from a Zipf stream")
    topk.add_argument("--k", type=_positive_int, default=10)
    topk.add_argument("--length", type=_positive_int, default=100_000)
    topk.add_argument("--distinct", type=_positive_int, default=20_000)
    topk.add_argument("--skew", type=float, default=1.1)
    topk.set_defaults(handler=cmd_topk)
    return parser


def main(argv: Sequence[str] | None = None, out: Callable[[str], None] = print) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        out(args.handler(args))
    except ValueError as exc:
        print(f"sketches: error: {exc}", file=sys.stderr)
        return 2
    return 0
