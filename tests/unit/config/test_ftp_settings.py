"""`config.FtpSettings`・`AppSettings.ftp`の検証（Phase8 Task18-1）。

`docs/phase8-integration-design.md#2-ftpsettings導入設計`が確定した設計
（環境変数`MOD_PERSONNEL_DB_FTP__*`によるネスト読み込み・デフォルト値・
`SecretStr`によるパスワード秘匿・未設定時は`ftp=None`のまま後方互換を保つ
こと）を検証する。
"""

import ast
import inspect
from pathlib import Path
from typing import TypedDict

import pytest
from pydantic import SecretStr, ValidationError

from mod_personnel_db import config as config_package
from mod_personnel_db.config import AppSettings, FtpSettings
from mod_personnel_db.config.ftp import FtpSettings as FtpSettingsFromFtpModule


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


def _clear_ftp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "MOD_PERSONNEL_DB_FTP__HOST",
        "MOD_PERSONNEL_DB_FTP__PORT",
        "MOD_PERSONNEL_DB_FTP__USERNAME",
        "MOD_PERSONNEL_DB_FTP__PASSWORD",
        "MOD_PERSONNEL_DB_FTP__REMOTE_DIRECTORY",
        "MOD_PERSONNEL_DB_FTP__TIMEOUT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_ftp_settings_is_exported_from_config_package() -> None:
    assert FtpSettingsFromFtpModule is FtpSettings
    assert config_package.FtpSettings is FtpSettings


def test_ftp_settings_field_names() -> None:
    assert set(FtpSettings.model_fields) == {
        "host",
        "port",
        "username",
        "password",
        "remote_directory",
        "timeout",
    }


def test_ftp_settings_defaults_besides_host() -> None:
    settings = FtpSettings(host="ftp.example.com")

    assert settings.port == 21
    assert settings.username == ""
    assert settings.password.get_secret_value() == ""
    assert settings.remote_directory == "/"
    assert settings.timeout == 30.0


def test_ftp_settings_password_is_secret_str() -> None:
    settings = FtpSettings(host="ftp.example.com", password=SecretStr("hunter2"))

    assert isinstance(settings.password, SecretStr)
    assert "hunter2" not in repr(settings)
    assert "hunter2" not in str(settings)
    assert settings.password.get_secret_value() == "hunter2"


def test_ftp_settings_host_is_required() -> None:
    with pytest.raises(ValidationError):
        FtpSettings()  # type: ignore[call-arg]


def test_app_settings_field_names_include_ftp() -> None:
    assert "ftp" in AppSettings.model_fields


def test_app_settings_ftp_defaults_to_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """既存のCompositionSettings等価性（4フィールドのみ）との後方互換を保つ。"""
    _clear_ftp_env(monkeypatch)
    settings = AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]

    assert settings.ftp is None


def test_app_settings_reads_ftp_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__HOST", "ftp.example.com")
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__PORT", "2121")
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__USERNAME", "publisher")
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__PASSWORD", "s3cret")
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__REMOTE_DIRECTORY", "/public")
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__TIMEOUT", "45.0")

    settings = AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]

    assert settings.ftp is not None
    assert settings.ftp.host == "ftp.example.com"
    assert settings.ftp.port == 2121
    assert settings.ftp.username == "publisher"
    assert settings.ftp.password.get_secret_value() == "s3cret"
    assert settings.ftp.remote_directory == "/public"
    assert settings.ftp.timeout == 45.0


def test_app_settings_ftp_partial_env_without_host_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """`host`欠落のまま他フィールドのみ指定した場合はfail-fastとする。"""
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__PORT", "2121")

    with pytest.raises(ValidationError):
        AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]


def test_app_settings_reads_ftp_from_dotenv_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "MOD_PERSONNEL_DB_DB_PATH=dotenv.sqlite3\n"
        "MOD_PERSONNEL_DB_KNOWLEDGE_ROOT=dotenv-knowledge\n"
        "MOD_PERSONNEL_DB_LAYOUTS_ROOT=dotenv-layouts\n"
        "MOD_PERSONNEL_DB_FTP__HOST=dotenv-ftp-host\n"
        "MOD_PERSONNEL_DB_FTP__PASSWORD=dotenv-pass\n"
    )

    settings = AppSettings(_env_file=str(env_file))  # type: ignore[call-arg]

    assert settings.ftp is not None
    assert settings.ftp.host == "dotenv-ftp-host"
    assert settings.ftp.password.get_secret_value() == "dotenv-pass"


def test_app_settings_ftp_env_var_takes_priority_over_dotenv_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.test"
    env_file.write_text(
        "MOD_PERSONNEL_DB_DB_PATH=dotenv.sqlite3\n"
        "MOD_PERSONNEL_DB_KNOWLEDGE_ROOT=dotenv-knowledge\n"
        "MOD_PERSONNEL_DB_LAYOUTS_ROOT=dotenv-layouts\n"
        "MOD_PERSONNEL_DB_FTP__HOST=dotenv-ftp-host\n"
    )
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__HOST", "envvar-ftp-host")

    settings = AppSettings(_env_file=str(env_file))  # type: ignore[call-arg]

    assert settings.ftp is not None
    assert settings.ftp.host == "envvar-ftp-host"


def test_app_settings_ftp_constructor_arg_takes_priority_over_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOD_PERSONNEL_DB_FTP__HOST", "envvar-ftp-host")

    settings = AppSettings(
        **_base_kwargs(),
        ftp=FtpSettings(host="ctor-ftp-host"),
        _env_file=None,
    )  # type: ignore[call-arg]

    assert settings.ftp is not None
    assert settings.ftp.host == "ctor-ftp-host"


def test_app_settings_remains_frozen_with_ftp_field(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_ftp_env(monkeypatch)
    settings = AppSettings(**_base_kwargs(), _env_file=None)  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        settings.ftp = FtpSettings(host="changed")


def test_ftp_module_depends_only_on_external_libraries() -> None:
    """`config/ftp.py`は`config/`内の他モジュール・他パッケージに依存しない。"""
    module = inspect.getmodule(FtpSettings)
    assert module is not None
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        assert not node.module.startswith("mod_personnel_db")
