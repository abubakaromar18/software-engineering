from conftest import findings_for

RULE = "long-method"


def body(n: int, indent: str = "    ") -> str:
    return "\n".join(f"{indent}x{i} = {i}" for i in range(n))


def test_function_at_limit_is_not_flagged():
    code = "def f():\n" + body(4)  # def line + 4 statements = 5 code lines
    assert findings_for(code, RULE, max_function_lines=5) == []


def test_function_over_limit_is_flagged_with_metric_and_symbol():
    code = "def f():\n" + body(9)
    [finding] = findings_for(code, RULE, max_function_lines=5)
    assert finding.metric == 10
    assert finding.threshold == 5
    assert finding.symbol == "f"
    assert (finding.location.line, finding.location.end_line) == (1, 10)


def test_blank_lines_comments_and_docstring_do_not_count():
    code = '''
    def f():
        """A docstring
        that spans
        several lines."""
        # a comment

        a = 1

        # another comment
        return a
    '''
    assert findings_for(code, RULE, max_function_lines=3) == []


def test_multiline_expressions_count_every_physical_line():
    code = """
    def f():
        return [
            1,
            2,
        ]
    """
    [finding] = findings_for(code, RULE, max_function_lines=4)
    assert finding.metric == 5


def test_methods_and_nested_functions_get_qualified_names():
    code = "class C:\n    def m(self):\n        def inner():\n" + body(6, " " * 12)
    names = {f.symbol for f in findings_for(code, RULE, max_function_lines=5)}
    assert names == {"C.m", "C.m.<locals>.inner"}


def test_async_functions_are_measured():
    code = "async def f():\n" + body(9)
    assert len(findings_for(code, RULE, max_function_lines=5)) == 1


def test_suppression_comment_on_def_line():
    code = "def f():  # smell: ignore[long-method]\n" + body(9)
    assert findings_for(code, RULE, max_function_lines=5) == []
