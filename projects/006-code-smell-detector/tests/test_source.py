from pathlib import Path

import pytest

from smell_detector.source import SourceFile


def parse(code: str) -> SourceFile:
    return SourceFile.parse(Path("t.py"), code)


def test_code_lines_skip_blanks_and_comments_but_include_strings():
    source = parse('x = 1\n\n# comment\ny = """a\nb"""\n')
    assert source.code_lines == {1, 4, 5}


def test_suppression_forms():
    source = parse(
        "a = 1  # smell: ignore\n"
        "b = 2  # smell: ignore[long-method, deep-nesting]\n"
        "c = 3  # unrelated comment\n"
    )
    assert source.is_suppressed(1, "anything")
    assert source.is_suppressed(2, "deep-nesting")
    assert not source.is_suppressed(2, "large-class")
    assert not source.is_suppressed(3, "long-method")


def test_suppression_text_inside_a_string_is_not_a_suppression():
    source = parse('a = "# smell: ignore"\n')
    assert not source.is_suppressed(1, "long-method")


def test_syntax_error_propagates():
    with pytest.raises(SyntaxError):
        parse("def broken(:\n")


def test_read_honours_encoding_declaration(tmp_path):
    path = tmp_path / "latin.py"
    path.write_bytes("# -*- coding: latin-1 -*-\nname = 'caf\xe9'\n".encode("latin-1"))
    assert SourceFile.read(path).code_lines == {2}
