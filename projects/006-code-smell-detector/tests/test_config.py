import pytest

from smell_detector import Config, ConfigError


def test_defaults():
    config = Config()
    assert config.max_function_lines == 50
    assert config.exclude == ()


def test_from_pyproject_reads_tool_table(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text(
        '[project]\nname = "x"\n\n[tool.smell-detector]\n'
        'max_nesting_depth = 2\nexclude = ["gen/*"]\n',
        encoding="utf-8",
    )
    config = Config.from_pyproject(path)
    assert config.max_nesting_depth == 2
    assert config.exclude == ("gen/*",)
    assert config.max_function_lines == 50  # untouched options keep defaults


def test_missing_table_means_defaults(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text('[project]\nname = "x"\n', encoding="utf-8")
    assert Config.from_pyproject(path) == Config()


def test_discover_walks_up_to_nearest_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.smell-detector]\nmax_class_methods = 7\n")
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    assert Config.discover(nested).max_class_methods == 7


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ("max_function_line = 10", "unknown option"),
        ("max_function_lines = 0", "positive integer"),
        ("max_function_lines = true", "positive integer"),
        ('max_function_lines = "10"', "positive integer"),
        ('exclude = "tests/*"', "list of glob strings"),
    ],
)
def test_invalid_options_are_rejected(tmp_path, toml, message):
    path = tmp_path / "pyproject.toml"
    path.write_text(f"[tool.smell-detector]\n{toml}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        Config.from_pyproject(path)


def test_invalid_toml_is_a_config_error(tmp_path):
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool.smell-detector\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid TOML"):
        Config.from_pyproject(path)


def test_overrides_ignore_none():
    config = Config().with_overrides(max_nesting_depth=2, max_class_lines=None)
    assert config.max_nesting_depth == 2
    assert config.max_class_lines == 300
