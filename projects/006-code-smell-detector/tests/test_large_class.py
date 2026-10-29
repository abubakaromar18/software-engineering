from conftest import findings_for

RULE = "large-class"


def make_class(methods: int, statements_per_method: int = 1) -> str:
    lines = ["class Big:", '    """Doc."""']
    for m in range(methods):
        lines.append(f"    def m{m}(self):")
        lines.extend(f"        v{s} = {s}" for s in range(statements_per_method))
    return "\n".join(lines) + "\n"


def test_small_class_is_fine():
    assert findings_for(make_class(3), RULE, max_class_methods=3) == []


def test_too_many_methods():
    [finding] = findings_for(make_class(6), RULE, max_class_methods=3)
    assert finding.metric == 6
    assert finding.threshold == 3
    assert "6 methods (limit 3)" in finding.message


def test_too_many_lines():
    # 1 class line + 2 * (1 def + 10 statements) = 23 code lines (docstring excluded)
    [finding] = findings_for(make_class(2, 10), RULE, max_class_lines=20)
    assert finding.metric == 23
    assert "lines of code" in finding.message


def test_both_limits_exceeded_scores_the_worse_signal():
    # methods 4/3 (1.33x), lines 13/6 (2.2x): lines should drive the score.
    [finding] = findings_for(make_class(4, 2), RULE, max_class_methods=3, max_class_lines=6)
    assert (finding.metric, finding.threshold) == (13, 6)
    assert "4 methods" in finding.message and "13 lines" in finding.message


def test_nested_classes_are_checked_with_qualified_name():
    code = "class Outer:\n" + "".join("    " + line + "\n" for line in make_class(5).splitlines())
    [finding] = findings_for(code, RULE, max_class_methods=3)
    assert finding.symbol == "Outer.Big"


def test_suppression():
    code = make_class(6).replace("class Big:", "class Big:  # smell: ignore")
    assert findings_for(code, RULE, max_class_methods=3) == []
