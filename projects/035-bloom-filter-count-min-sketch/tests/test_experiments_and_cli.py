import random

import pytest

from sketches.charts import bar_chart, table
from sketches.cli import main
from sketches.experiments import (
    run_bloom_accuracy,
    run_bloom_overload,
    run_cms_accuracy,
    zipf_stream,
)


def run_cli(args):
    captured = []
    code = main(args, out=captured.append)
    return code, "\n".join(captured)


class TestExperiments:
    def test_bloom_accuracy_tracks_theory(self):
        trials = run_bloom_accuracy([0.1, 0.01], capacity=2000, probes=20_000)
        for trial in trials:
            assert trial.empirical_rate == pytest.approx(trial.target_rate, rel=0.35)
            assert trial.theoretical_rate == pytest.approx(trial.target_rate, rel=0.1)

    def test_overload_fpr_increases_monotonically(self):
        trials = run_bloom_overload(capacity=1000, probes=5000, load_factors=(0.5, 1, 2, 4))
        rates = [t.empirical_rate for t in trials]
        assert rates == sorted(rates)
        assert trials[-1].empirical_rate > 0.3

    def test_overload_validates_load_factors(self):
        with pytest.raises(ValueError):
            run_bloom_overload(load_factors=(2, 1))
        with pytest.raises(ValueError):
            run_bloom_overload(probes=0)

    def test_cms_accuracy_improves_with_smaller_epsilon(self):
        trials = run_cms_accuracy([0.01, 0.001], stream_length=10_000, distinct=2000)
        standard = [t for t in trials if not t.conservative]
        conservative = [t for t in trials if t.conservative]
        assert standard[1].mean_error < standard[0].mean_error
        for std, cons in zip(standard, conservative):
            assert cons.mean_error <= std.mean_error
            assert std.within_bound >= 0.99

    def test_experiments_are_deterministic(self):
        first = run_cms_accuracy([0.01], stream_length=2000, distinct=300, seed=4)
        second = run_cms_accuracy([0.01], stream_length=2000, distinct=300, seed=4)
        assert first == second

    def test_zipf_is_skewed(self):
        stream = zipf_stream(10_000, 100, 1.2, random.Random(0))
        assert stream.count(0) > 10 * stream.count(50)

    @pytest.mark.parametrize("length, distinct, skew", [(0, 1, 1), (1, 0, 1), (1, 1, -1)])
    def test_zipf_validation(self, length, distinct, skew):
        with pytest.raises(ValueError):
            zipf_stream(length, distinct, skew, random.Random(0))


class TestCharts:
    def test_table_alignment(self):
        rendered = table(["a", "long"], [(1, 2), (333, 4)]).splitlines()
        assert rendered[0] == "  a  long"
        assert rendered[1] == "---  ----"
        assert rendered[3] == "333     4"

    def test_table_rejects_ragged_rows(self):
        with pytest.raises(ValueError):
            table(["a"], [(1, 2)])

    def test_linear_bars_are_proportional(self):
        chart = bar_chart("t", ["x", "y"], {"s": [1.0, 0.5]}, width=10)
        lines = chart.splitlines()
        assert lines[1].count("█") == 10
        assert lines[2].count("█") == 5

    def test_log_scale_gives_equal_width_per_decade(self):
        chart = bar_chart("t", ["a", "b", "c"], {"s": [0.001, 0.01, 0.1]}, width=30, log_scale=True)
        lengths = [line.count("█") for line in chart.splitlines()[1:]]
        assert lengths[1] - lengths[0] == lengths[2] - lengths[1] == 10
        assert "(log scale)" in chart

    def test_zero_values_render_empty_bars(self):
        chart = bar_chart("t", ["a"], {"s": [0.0]}, log_scale=True)
        assert "█" not in chart

    def test_multiple_series_use_distinct_glyphs(self):
        chart = bar_chart("t", ["a"], {"one": [1], "two": [1]}, width=4)
        assert "████" in chart and "▓▓▓▓" in chart

    @pytest.mark.parametrize(
        "labels, series, width",
        [(["a"], {}, 10), (["a"], {"s": [1, 2]}, 10), (["a"], {"s": [1]}, 0),
         (["a"], {str(i): [1] for i in range(5)}, 10)],
    )
    def test_chart_validation(self, labels, series, width):
        with pytest.raises(ValueError):
            bar_chart("t", labels, series, width=width)


class TestCli:
    def test_bloom_command(self):
        code, output = run_cli(["bloom", "--rates", "0.1,0.01", "--capacity", "500", "--probes", "2000"])
        assert code == 0
        assert "measured" in output and "(log scale)" in output

    def test_overload_command(self):
        code, output = run_cli(["overload", "--capacity", "200", "--probes", "1000"])
        assert code == 0 and "3.00x" in output

    def test_cms_command(self):
        code, output = run_cli(["cms", "--epsilons", "0.01", "--length", "2000", "--distinct", "500"])
        assert code == 0 and "conservative" in output

    def test_topk_command(self):
        code, output = run_cli(["topk", "--k", "3", "--length", "5000", "--distinct", "500"])
        assert code == 0 and "recall vs exact top-3" in output

    def test_csv_output(self):
        code, output = run_cli(["bloom", "--rates", "0.1", "--capacity", "100", "--probes", "100", "--csv"])
        header, row = output.splitlines()
        assert code == 0
        assert header.startswith("target_rate,num_bits,num_hashes")
        assert row.startswith("0.1,")

    def test_topk_csv_output(self):
        code, output = run_cli(["topk", "--k", "2", "--length", "1000", "--distinct", "50", "--csv"])
        assert code == 0 and output.splitlines()[0] == "rank,item,estimate,true_count"

    @pytest.mark.parametrize(
        "args",
        [["bloom", "--rates", "2"], ["bloom", "--rates", "abc"], ["cms", "--length", "0"], []],
    )
    def test_invalid_arguments_exit_nonzero(self, args):
        with pytest.raises(SystemExit) as excinfo:
            main(args)
        assert excinfo.value.code == 2

    def test_domain_errors_reported_cleanly(self, capsys):
        code, _ = run_cli(["cms", "--skew", "-1", "--length", "10", "--distinct", "5"])
        assert code == 2
        assert "skew must be non-negative" in capsys.readouterr().err
