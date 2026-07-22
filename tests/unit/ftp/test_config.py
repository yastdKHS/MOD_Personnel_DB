"""`FTPConnectionConfig`の既定値・不変性の検証（Phase7 Task16-1）。"""

import dataclasses

import pytest

from mod_personnel_db.ftp import FTPConnectionConfig


def test_default_values() -> None:
    config = FTPConnectionConfig(host="ftp.example.jp")

    assert config.host == "ftp.example.jp"
    assert config.port == 21
    assert config.username == ""
    assert config.password == ""
    assert config.timeout == 30.0
    assert config.passive is True


def test_all_fields_can_be_overridden() -> None:
    config = FTPConnectionConfig(
        host="ftp.example.jp",
        port=2121,
        username="user",
        password="secret",
        timeout=5.0,
        passive=False,
    )

    assert config.port == 2121
    assert config.username == "user"
    assert config.password == "secret"
    assert config.timeout == 5.0
    assert config.passive is False


def test_config_is_frozen() -> None:
    config = FTPConnectionConfig(host="ftp.example.jp")

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.host = "other.example.jp"  # type: ignore[misc]
