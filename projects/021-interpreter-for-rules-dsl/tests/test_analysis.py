from rules_dsl import Severity, builtin_functions, check, parse


def diagnose(text: str) -> list[tuple[Severity, str]]:
    return [(d.severity, d.message) for d in check(parse(text), builtin_functions())]


def messages(text: str) -> list[str]:
    return [message for _severity, message in diagnose(text)]


def test_clean_ruleset_has_no_diagnostics(examples):
    assert check(parse((examples / "checkout.rules").read_text()), builtin_functions()) == []


def test_duplicate_rule_names():
    assert diagnose('rule "a" when x then stop end\nrule "a" when x then stop end') == [
        (Severity.ERROR, 'duplicate rule name "a"')
    ]


def test_unknown_functions_and_arity():
    found = messages('rule "a" when len(x, y) > 1 then set y = frobnicate(1) end')
    assert found[0] == "len() takes 1 argument(s), got 2"
    assert found[1].startswith("unknown function 'frobnicate' (known: abs, len")


def test_constant_subexpressions_that_must_fail_are_errors():
    found = diagnose('rule "a" when x > 1 / 0 then set label = "n" + 1 end')
    assert found == [
        (Severity.ERROR, "always fails: division by zero"),
        (Severity.ERROR, "always fails: operator '+' needs two numbers or two strings, "
                         "got string and number"),
    ]  # fmt: skip


def test_non_boolean_constant_condition_is_an_error():
    assert diagnose('rule "a" when 1 + 1 then stop end') == [
        (Severity.ERROR, "condition is not a boolean")
    ]


def test_constant_conditions_are_warnings_but_a_bare_true_is_allowed():
    assert messages('rule "a" when 2 > 1 then stop end') == ["condition is always true"]
    assert messages('rule "a" when 1 > 2 then stop end') == [
        "condition is always false; rule never fires"
    ]
    assert messages('rule "default" when true then set x = 1 end') == []


def test_unconditional_stop_makes_later_rules_unreachable():
    found = messages(
        'rule "gate" priority 1 when true then stop end\nrule "after" when x then stop end'
    )
    assert found == ['unreachable: rule "gate" always fires and stops']


def test_result_reads_before_assignment():
    found = messages(
        """
        rule "early" priority 9 when result.score > 1 then set flag = true end
        rule "scores" priority 5 when true then set score = 3 end
        rule "uses" priority 1 when result.score > 1 and result.ghost then stop end
        """
    )
    assert found == [
        "'result.score' is read before any earlier rule assigns it",
        "'result.ghost' is never assigned by any rule",
    ]


def test_has_guards_and_earlier_actions_in_the_same_rule_count_as_assigned():
    assert (
        messages(
            """
        rule "a" when has(result.x) then set y = 1 set z = result.y + 1 end
        rule "b" priority -1 when true then set x = 1 end
        """
        )
        == []
    )


def test_diagnostics_carry_rule_names_and_render_with_source():
    from rules_dsl import Source

    source = Source('rule "a" when x then set y = "s" - 1 end', name="demo.rules")
    (diagnostic,) = check(parse(source), builtin_functions())
    assert diagnostic.rule == "a"
    rendered = diagnostic.render(source)
    assert rendered.startswith("demo.rules:1:30: error: always fails")
    assert rendered.endswith("^" * 7)
