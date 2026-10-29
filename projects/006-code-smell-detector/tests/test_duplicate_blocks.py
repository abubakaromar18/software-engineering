import ast

from conftest import findings_for

from smell_detector import Analyzer, Config
from smell_detector.detectors.duplicate_blocks import fingerprint

RULE = "duplicate-block"
SMALL = {"duplicate_min_statements": 3, "duplicate_min_lines": 3}


def fp(code: str) -> str:
    return fingerprint(ast.parse(code).body[0])


def test_fingerprint_ignores_names_and_literal_values():
    assert fp("total = price * qty") == fp("s = p * n")
    assert fp("x = 'a'") == fp("y = 'b'")


def test_fingerprint_respects_structure_operators_and_literal_types():
    assert fp("a = b * c") != fp("a = b + c")
    assert fp("x = 1") != fp("x = '1'")
    assert fp("obj.save()") != fp("obj.delete()")  # attribute names are API, kept


def test_renamed_copy_is_detected():
    code = """
    def a(items):
        total = 0
        for item in items:
            total += item.price
        tax = total * 0.2
        return total + tax

    def b(rows):
        s = 0
        for r in rows:
            s += r.price
        t = s * 0.3
        return s + t
    """
    [finding] = findings_for(code, RULE, **SMALL)
    # Line 1 is the blank line left by the triple-quoted snippet.
    assert (finding.location.line, finding.location.end_line) == (3, 7)
    assert [(r.line, r.end_line) for r in finding.related] == [(10, 14)]
    assert finding.metric == 5  # 5 lines x 1 extra copy


def test_clone_is_extended_to_maximal_length_and_sub_windows_are_pruned():
    # Each statement has a different shape (i additions), so no window repeats
    # inside one function and the only clone is the whole body.
    stmts = "\n".join("    v = w" + " + w" * i for i in range(8))
    code = f"def a():\n{stmts}\n\ndef b():\n{stmts}\n"
    findings = findings_for(code, RULE, **SMALL)
    assert len(findings) == 1
    assert findings[0].location.end_line - findings[0].location.line + 1 == 8


def test_three_copies_reported_once():
    block = "    a = 1\n    b = a + 2\n    c = b * a\n"
    code = "".join(f"def f{i}():\n{block}\n" for i in range(3))
    [finding] = findings_for(code, RULE, **SMALL)
    assert len(finding.related) == 2
    assert "appears 3 times" in finding.message


def test_repeated_statements_do_not_clone_themselves():
    code = "def f(x):\n" + "    x += 1\n" * 3
    assert findings_for(code, RULE, **SMALL) == []


def test_repeated_statements_long_enough_form_one_non_overlapping_pair():
    code = "def f(x):\n" + "    x += 1\n" * 6
    [finding] = findings_for(code, RULE, **SMALL)
    assert (finding.location.line, finding.location.end_line) == (2, 4)
    assert [(r.line, r.end_line) for r in finding.related] == [(5, 7)]


def test_short_clones_below_line_threshold_are_ignored():
    block = "    a = 1\n    b = 2\n    c = 3\n"
    code = f"def f():\n{block}\ndef g():\n{block}"
    assert findings_for(code, RULE, duplicate_min_statements=3, duplicate_min_lines=4) == []


def test_imports_never_form_clones():
    header = "import os\nimport sys\nimport json\nimport re\n"
    assert findings_for(header + "\n" + header, RULE, **SMALL) == []


def test_clones_are_found_across_files(write):
    block = """
    def handler(request):
        user = request.user
        if not user:
            raise PermissionError
        data = request.json()
        return data
    """
    root = write({"a.py": block, "pkg/b.py": block})
    report = Analyzer(Config(**SMALL)).analyze_paths([root])
    [finding] = report.findings
    paths = {finding.location.path.name, finding.related[0].path.name}
    assert paths == {"a.py", "b.py"}


def test_suppressing_one_copy_removes_the_pair():
    block = "    a = 1\n    b = a + 2\n    c = b * a\n"
    code = f"def f():\n{block}\ndef g():\n" + block.replace(
        "a = 1", "a = 1  # smell: ignore[duplicate-block]", 1
    )
    assert findings_for(code, RULE, **SMALL) == []
