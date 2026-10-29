import pytest

from smell_detector.discovery import find_python_files


def test_walks_directories_in_sorted_order_and_skips_tooling_dirs(write):
    root = write(
        {
            "b.py": "",
            "a.py": "",
            "pkg/c.py": "",
            "notes.txt": "",
            ".venv/lib/d.py": "",
            "pkg/__pycache__/e.py": "",
        }
    )
    found = [p.relative_to(root).as_posix() for p in find_python_files([root])]
    assert found == ["a.py", "b.py", "pkg/c.py"]


def test_exclude_globs_are_relative_to_the_scanned_directory(write):
    root = write({"src/m.py": "", "tests/fixtures/deep/f.py": "", "tests/test_m.py": ""})
    found = [
        p.relative_to(root).as_posix() for p in find_python_files([root], ["tests/fixtures/*"])
    ]
    assert found == ["src/m.py", "tests/test_m.py"]


def test_explicit_files_are_always_included_and_deduplicated(write):
    root = write({"gen/x.py": ""})
    target = root / "gen" / "x.py"
    found = list(find_python_files([target, root], ["gen/*"]))
    assert found == [target]


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        list(find_python_files([tmp_path / "nope"]))
