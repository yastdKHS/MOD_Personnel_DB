"""`config.AppSettings`の結合テスト（ADR-0028、Phase6 Task14-5）。

`tests/unit/config/test_settings.py`が`_env_file`引数で直接ファイルを
指定するのに対し、本テストは実際のプロセス作業ディレクトリ（カレント
ディレクトリ）に配置した`.env`ファイルを、`model_config`の既定
（`env_file=".env"`）どおりに自動発見・読み込みできることを確認する
（python-dotenvとの実結合）。あわせて、`cli.bootstrap.build_settings()`
（合成ルートの唯一のSettings生成経路）を通じた環境変数オーバーライドの
実結合も検証する。
"""

from pathlib import Path

import pytest

from mod_personnel_db.cli.bootstrap import build_settings
from mod_personnel_db.config import AppSettings


def test_app_settings_discovers_dotenv_in_current_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MOD_PERSONNEL_DB_DB_PATH=cwd-dotenv.sqlite3\n"
        "MOD_PERSONNEL_DB_KNOWLEDGE_ROOT=cwd-knowledge\n"
        "MOD_PERSONNEL_DB_LAYOUTS_ROOT=cwd-layouts\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MOD_PERSONNEL_DB_DB_PATH", raising=False)

    settings = AppSettings()  # type: ignore[call-arg]

    assert settings.db_path == "cwd-dotenv.sqlite3"
    assert settings.knowledge_root == Path("cwd-knowledge")


def test_app_settings_env_var_overrides_cwd_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MOD_PERSONNEL_DB_DB_PATH=cwd-dotenv.sqlite3\n"
        "MOD_PERSONNEL_DB_KNOWLEDGE_ROOT=cwd-knowledge\n"
        "MOD_PERSONNEL_DB_LAYOUTS_ROOT=cwd-layouts\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MOD_PERSONNEL_DB_DB_PATH", "envvar.sqlite3")

    settings = AppSettings()  # type: ignore[call-arg]

    assert settings.db_path == "envvar.sqlite3"


def test_build_settings_constructor_args_override_env_var_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`cli.bootstrap.build_settings()`（CLI引数由来）が環境変数より優先される。"""
    monkeypatch.setenv("MOD_PERSONNEL_DB_PARSER_CODE_VERSION", "envvar-version")

    settings = build_settings(
        db_path="cli.sqlite3",
        knowledge_root=Path("cli-knowledge"),
        layouts_root=Path("cli-layouts"),
        parser_code_version="cli-version",
    )

    assert settings.parser_code_version == "cli-version"
    assert settings.db_path == "cli.sqlite3"


def test_build_settings_returns_app_settings_instance() -> None:
    settings = build_settings(
        db_path="cli.sqlite3",
        knowledge_root=Path("cli-knowledge"),
        layouts_root=Path("cli-layouts"),
        parser_code_version="cli-version",
    )

    assert isinstance(settings, AppSettings)
