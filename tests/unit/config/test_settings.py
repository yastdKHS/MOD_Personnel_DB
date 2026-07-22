"""`config.AppSettings`の検証（ADR-0028、Phase6 Task14-5）。

`BaseSettings`利用・環境変数/.env/コンストラクタ引数の優先順位
（コンストラクタ引数 > 環境変数 > `.env`ファイル > デフォルト値）・
既存`CompositionSettings`との等価性（フィールド構成）を検証する。
"""

import ast
import inspect
from pathlib import Path
from typing import TypedDict

import pytest
from pydantic import ValidationError
from pydantic_settings import BaseSettings

from mod_personnel_db import config as config_package
from mod_personnel_db.config import AppSettings
from mod_personnel_db.config.settings import AppSettings as AppSettingsFromSettingsModule


class _BaseKwargs(TypedDict):
    db_path: str
    knowledge_root: Path
    layouts_root: Path


def _base_kwargs() -> _BaseKwargs:
    return {
        "db_path": "mod_personnel.sqlite3",
        "knowledge_root": Path("knowledge"),
        "layouts_root": Path("layouts"),
    }


def test_app_settings_is_exported_from_config_package() -> None:
    assert AppSettingsFromSettingsModule is AppSettings
    assert config_package.AppSettings is AppSettings


def test_app_settings_uses_base_settings() -> None:
    assert issubclass(AppSettings, BaseSettings)


def test_app_settings_field_names_match_composition_settings_equivalent() -> None:
    assert set(AppSettings.model_fields) == {
        "db_path",
        "knowledge_root",
        "layouts_root",
        "parser_code_version",
    }


def test_app_settings_constructed_from_constructor_args_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", raising=False)
    settings = AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]

    assert settings.db_path == "mod_personnel.sqlite3"
    assert settings.knowledge_root == Path("knowledge")
    assert settings.layouts_root == Path("layouts")
    assert settings.parser_code_version == "v1.0.0"


def test_app_settings_coerces_root_fields_to_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """実行時にはpydanticが`str`を`Path`へ強制変換するため、意図的に型を無視する。"""
    monkeypatch.delenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", raising=False)
    settings = AppSettings(  # type: ignore[call-arg]
        db_path="a.db",
        knowledge_root="k",  # type: ignore[arg-type]
        layouts_root="l",  # type: ignore[arg-type]
        _env_file=None,
    )

    assert isinstance(settings.knowledge_root, Path)
    assert isinstance(settings.layouts_root, Path)


def test_app_settings_missing_required_field_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MOD_PERSONNEL_DB_DB_PATH", raising=False)
    with pytest.raises(ValidationError):
        AppSettings(knowledge_root=Path("k"), layouts_root=Path("l"), _env_file=None)  # type: ignore[call-arg]


def test_app_settings_reads_parser_code_version_from_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", "env-v2.0.0")
    settings = AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]

    assert settings.parser_code_version == "env-v2.0.0"


def test_app_settings_reads_db_path_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOD_PERSONNEL_DB_DB_PATH", "env.sqlite3")
    settings = AppSettings(knowledge_root=Path("k"), layouts_root=Path("l"), _env_file=None)  # type: ignore[call-arg]

    assert settings.db_path == "env.sqlite3"


def test_app_settings_reads_from_dotenv_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "MOD_PERSONNEL_DB_DB_PATH=dotenv.sqlite3\n"
        "MOD_PERSONNEL_DB_KNOWLEDGE_ROOT=dotenv-knowledge\n"
        "MOD_PERSONNEL_DB_LAYOUTS_ROOT=dotenv-layouts\n"
        "MOD_PERSONNEL_DB_PARSER_CODE_VERSION=dotenv-v1\n"
    )

    settings = AppSettings(_env_file=str(env_file))  # type: ignore[call-arg]

    assert settings.db_path == "dotenv.sqlite3"
    assert settings.knowledge_root == Path("dotenv-knowledge")
    assert settings.parser_code_version == "dotenv-v1"


def test_app_settings_env_var_takes_priority_over_dotenv_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "MOD_PERSONNEL_DB_DB_PATH=dotenv.sqlite3\n"
        "MOD_PERSONNEL_DB_KNOWLEDGE_ROOT=dotenv-knowledge\n"
        "MOD_PERSONNEL_DB_LAYOUTS_ROOT=dotenv-layouts\n"
        "MOD_PERSONNEL_DB_PARSER_CODE_VERSION=dotenv-v1\n"
    )
    monkeypatch.setenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", "envvar-v2")

    settings = AppSettings(_env_file=str(env_file))  # type: ignore[call-arg]

    assert settings.parser_code_version == "envvar-v2"


def test_app_settings_constructor_arg_takes_priority_over_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", "envvar-v2")

    settings = AppSettings(**_base_kwargs(), parser_code_version="ctor-v3", _env_file=None)  # type: ignore[call-arg]

    assert settings.parser_code_version == "ctor-v3"


def test_app_settings_constructor_arg_takes_priority_over_dotenv_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.test"
    env_file.write_text("MOD_PERSONNEL_DB_PARSER_CODE_VERSION=dotenv-v1\n")

    settings = AppSettings(**_base_kwargs(), parser_code_version="ctor-v3", _env_file=str(env_file))  # type: ignore[call-arg]

    assert settings.parser_code_version == "ctor-v3"


def test_app_settings_is_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", raising=False)
    settings = AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        settings.parser_code_version = "changed"


def test_config_package_depends_only_on_utils_or_external() -> None:
    """`config/`は`utils/`以外の自パッケージに依存しない（docs/api/package-design.md#config）。"""
    for module in (config_package, inspect.getmodule(AppSettings)):
        assert module is not None
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if not node.module.startswith("mod_personnel_db"):
                continue
            assert node.module == "mod_personnel_db.config.settings" or (
                node.module == "mod_personnel_db.utils"
                or node.module.startswith("mod_personnel_db.utils.")
            )
