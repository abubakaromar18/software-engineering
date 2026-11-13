import io
import json

import pytest

from rules_dsl.cli import EXIT_OK, EXIT_PROBLEM, EXIT_USAGE, main


def run_cli(*argv: str, stdin: str | None = None, monkeypatch=None):
    out, err = io.StringIO(), io.StringIO()
    if stdin is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    code = main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def write(tmp_path):
    def _write(name: str, text: str):
        path = tmp_path / name
        path.write_text(text)
        return str(path)

    return _write


def test_run_prints_json_and_trace(examples):
    code, out, err = run_cli(
        "run", str(examples / "checkout.rules"), "--facts", str(examples / "order.json"), "--trace"
    )
    assert code == EXIT_OK
    assert json.loads(out)["results"]["total"] == "119.91"
    assert "fired        gold loyalty discount" in err
    assert "not matched  standard shipping" in err


def test_run_reads_facts_from_stdin(write, monkeypatch):
    rules = write("r.rules", 'rule "a" when x > 1 then set y = x * 2 end')
    code, out, _ = run_cli("run", rules, "--facts", "-", stdin='{"x": 2}', monkeypatch=monkeypatch)
    assert code == EXIT_OK and json.loads(out)["results"] == {"y": "4"}


def test_run_with_skip_policy_exits_1_but_still_prints_results(write):
    rules = write(
        "r.rules",
        'rule "bad" priority 1 when true then set a = 1 / x end\n'
        'rule "ok" when true then set b = 1 end',
    )
    facts = write("f.json", '{"x": 0}')
    code, out, err = run_cli("run", rules, "--facts", facts, "--on-error", "skip", "--trace")
    assert code == EXIT_PROBLEM
    assert json.loads(out)["results"] == {"b": "1"}
    assert "failed" in err and "division by zero at 1:46" in err


def test_run_failure_renders_a_source_excerpt(write):
    rules = write("r.rules", 'rule "bad" when true then set a = 1 / x end')
    facts = write("f.json", '{"x": 0}')
    code, _, err = run_cli("run", rules, "--facts", facts)
    assert code == EXIT_PROBLEM
    assert 'r.rules:1:35: evaluation error: in rule "bad": division by zero' in err
    assert "^^^^^" in err


def test_check_reports_and_sets_exit_code(examples):
    code, out, err = run_cli("check", str(examples / "broken.rules"))
    assert code == EXIT_PROBLEM
    assert out.strip() == "3 error(s), 2 warning(s)"
    assert "unknown function 'rounded'" in err
    assert run_cli("check", str(examples / "checkout.rules"))[0] == EXIT_OK


def test_syntax_errors_are_all_reported(write):
    rules = write("r.rules", 'rule "a" when then stop end\nrule "b" when x then end')
    code, _, err = run_cli("check", rules)
    assert code == EXIT_PROBLEM
    assert err.count("syntax error") == 2


def test_fmt_and_fmt_check(write, examples):
    messy = write("m.rules", 'rule "a" when (x>1) then stop end')
    code, out, _ = run_cli("fmt", messy)
    assert code == EXIT_OK and out.startswith('rule "a"\nwhen\n    x > 1\n')
    assert run_cli("fmt", "--check", messy)[0] == EXIT_PROBLEM
    assert run_cli("fmt", "--check", str(examples / "checkout.rules"))[0] == EXIT_OK


def test_functions_lists_builtins():
    code, out, _ = run_cli("functions")
    assert code == EXIT_OK and "round" in out and "round half up" in out


def test_io_and_json_errors_are_usage_errors(write, tmp_path):
    rules = write("r.rules", 'rule "a" when true then stop end')
    assert run_cli("check", str(tmp_path / "missing.rules"))[0] == EXIT_USAGE
    bad = write("bad.json", "{not json")
    code, _, err = run_cli("run", rules, "--facts", bad)
    assert code == EXIT_USAGE and "invalid JSON" in err


def test_reserved_fact_is_reported(write):
    rules = write("r.rules", 'rule "a" when true then stop end')
    facts = write("f.json", '{"result": 1}')
    code, _, err = run_cli("run", rules, "--facts", facts)
    assert code == EXIT_PROBLEM and "configuration error" in err
