"""End-to-end tests through ``main()``: arguments in, text/JSON and exit code out."""

import json

from smell_detector.cli import EXIT_CLEAN, EXIT_ERROR, EXIT_FINDINGS, main

NESTED = """
def tangled(a, b, c):
    if a:
        for x in b:
            if x:
                while c:
                    if c > x:
                        return x
                    c -= 1
"""


def test_clean_code_exits_zero(write, capsys):
    root = write({"ok.py": "def f():\n    return 1\n"})
    assert main([str(root)]) == EXIT_CLEAN
    assert "0 findings in 1 file" in capsys.readouterr().out


def test_findings_exit_one_and_print_location(write, capsys):
    root = write({"bad.py": NESTED})
    assert main([str(root), "--max-nesting-depth", "3"]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "bad.py:2-9: MEDIUM" in out
    assert "[deep-nesting] function 'tangled' nests blocks 5 deep" in out


def test_json_output(write, capsys):
    root = write({"bad.py": NESTED})
    main([str(root), "--format", "json", "--max-nesting-depth", "2"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["findings"] == 1
    [finding] = payload["findings"]
    assert finding["rule"] == "deep-nesting"
    assert finding["severity"] == "high"
    assert finding["score"] == 60


def test_fail_on_threshold_controls_exit_code(write, capsys):
    root = write({"bad.py": NESTED})
    # depth 5 vs limit 4 scores 20 (low): reported, but doesn't fail a --fail-on medium gate.
    assert main([str(root), "--max-nesting-depth", "4", "--fail-on", "medium"]) == EXIT_CLEAN
    assert "LOW" in capsys.readouterr().out


def test_min_severity_hides_findings(write, capsys):
    root = write({"bad.py": NESTED})
    assert main([str(root), "--max-nesting-depth", "4", "--min-severity", "high"]) == EXIT_CLEAN
    assert "0 findings" in capsys.readouterr().out


def test_config_file_is_discovered_from_scanned_path(write, capsys):
    root = write(
        {"pyproject.toml": "[tool.smell-detector]\nmax_nesting_depth = 2\n", "bad.py": NESTED}
    )
    assert main([str(root)]) == EXIT_FINDINGS
    capsys.readouterr()


def test_explicit_config_flag(write, capsys):
    root = write(
        {"bad.py": NESTED, "conf/strict.toml": "[tool.smell-detector]\nmax_nesting_depth = 1\n"}
    )
    assert main([str(root / "bad.py"), "--config", str(root / "conf/strict.toml")]) == EXIT_FINDINGS
    assert "HIGH" in capsys.readouterr().out


def test_syntax_errors_are_reported_not_fatal(write, capsys):
    root = write({"broken.py": "def f(:\n", "bad.py": NESTED})
    assert main([str(root), "--max-nesting-depth", "3"]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "broken.py: ERROR  syntax error at line 1" in out
    assert "1 file(s) could not be parsed" in out


def test_invalid_config_exits_two(write, capsys):
    root = write({"pyproject.toml": "[tool.smell-detector]\nbogus = 1\n", "a.py": ""})
    assert main([str(root)]) == EXIT_ERROR
    assert "unknown option(s)" in capsys.readouterr().err


def test_missing_path_exits_two(tmp_path, capsys):
    assert main([str(tmp_path / "missing")]) == EXIT_ERROR
    assert "no such file or directory" in capsys.readouterr().err


def test_hotspots_rank_files_by_total_score(write, capsys):
    root = write({"worse.py": NESTED + NESTED.replace("tangled", "knotted"), "bad.py": NESTED})
    main([str(root), "--max-nesting-depth", "2", "--duplicate-min-lines", "100"])
    out = capsys.readouterr().out
    hotspots = out.split("Hotspots (files by total smell score):\n")[1].splitlines()
    assert hotspots[0].endswith("worse.py") and hotspots[1].endswith("bad.py")
