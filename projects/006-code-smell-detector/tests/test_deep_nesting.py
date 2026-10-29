import ast
import textwrap

from conftest import findings_for

from smell_detector.detectors.deep_nesting import max_depth

RULE = "deep-nesting"


def depth_of(code: str) -> int:
    return max_depth(ast.parse(textwrap.dedent(code)).body[0])[0]


def test_flat_function_has_depth_zero():
    assert depth_of("def f():\n    return 1\n") == 0


def test_each_block_kind_adds_a_level():
    code = """
    def f(items, path):
        for item in items:
            while item:
                with open(path) as fh:
                    try:
                        match item:
                            case 1:
                                if fh:
                                    pass
                    except OSError:
                        pass
    """
    assert depth_of(code) == 6


def test_elif_chain_is_flat():
    code = """
    def f(x):
        if x == 1:
            return "a"
        elif x == 2:
            return "b"
        elif x == 3:
            return "c"
        else:
            return "d"
    """
    assert depth_of(code) == 1


def test_if_inside_else_block_is_nested():
    code = """
    def f(x, y):
        if x:
            pass
        else:
            y += 1
            if y:
                pass
    """
    assert depth_of(code) == 2


def test_nested_function_is_measured_separately():
    code = """
    def outer(a):
        if a:
            def inner(b):
                if b:
                    if b > 1:
                        if b > 2:
                            return b
            return inner
    """
    findings = findings_for(code, RULE, max_nesting_depth=2)
    assert [(f.symbol, f.metric) for f in findings] == [("outer.<locals>.inner", 3)]


def test_finding_reports_deepest_line():
    code = """
    def f(a):
        if a:
            for i in a:
                if i:
                    return i
    """
    [finding] = findings_for(code, RULE, max_nesting_depth=2)
    assert "3 deep at line 5" in finding.message
