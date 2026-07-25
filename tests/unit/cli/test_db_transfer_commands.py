"""`download-db`/`upload-db`コマンドの単体テスト（Task18-17）。

既存`FTPClient.download()`/`upload()`（`ftp/`、Phase7 Task16-1）のみを
呼び出すことを、`InMemoryFTPClient`（`ftp/mock.py`、実ネットワーク接続なし）
で差し替えて確認する。`cli/commands.py`の`download_db_command`/
`upload_db_command`は`bootstrap.build_ftp_client()`をProtocol経由でのみ
利用し、`StandardFTPClient`を直接生成しない。
"""

from pathlib import Path

import pytest

from mod_personnel_db.cli import app, commands
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.ftp import InMemoryFTPClient


def test_download_db_command_calls_ftp_client_download_only(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`download_db_command()`は`FTPClient.download()`のみを呼び出し、
    取得したバイト列を`settings.db_path`へそのまま書き込む。
    """
    fake_ftp = InMemoryFTPClient()
    fake_ftp.connect()
    source_file = tmp_path / "remote-source.sqlite3"
    source_file.write_bytes(b"remote-db-bytes")
    fake_ftp.upload(str(source_file), "/incoming/personnel.db")
    fake_ftp.disconnect()
    monkeypatch.setattr(commands, "build_ftp_client", lambda _settings: fake_ftp)

    commands.download_db_command(settings, "/incoming/personnel.db")

    assert Path(settings.db_path).read_bytes() == b"remote-db-bytes"
    assert fake_ftp.downloaded == [("/incoming/personnel.db", settings.db_path)]


def test_upload_db_command_calls_ftp_client_upload_only(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`upload_db_command()`は`FTPClient.upload()`のみを呼び出し、
    `settings.db_path`を指定した`remote_path`へそのまま渡す。
    """
    fake_ftp = InMemoryFTPClient()
    monkeypatch.setattr(commands, "build_ftp_client", lambda _settings: fake_ftp)

    commands.upload_db_command(settings, "/incoming/personnel.db")

    assert fake_ftp.uploaded == [(settings.db_path, "/incoming/personnel.db")]


def test_commands_tuple_includes_db_transfer_subcommands() -> None:
    assert "download-db" in app.COMMANDS
    assert "upload-db" in app.COMMANDS


def test_parser_accepts_download_db_with_remote_path() -> None:
    parser = app.build_parser()
    args = parser.parse_args(
        [
            "--db-path",
            "x.sqlite3",
            "--knowledge-root",
            "knowledge",
            "--layouts-root",
            "layouts",
            "download-db",
            "/incoming/personnel.db",
        ]
    )
    assert args.command == "download-db"
    assert args.remote_path == "/incoming/personnel.db"


def test_parser_accepts_upload_db_with_remote_path() -> None:
    parser = app.build_parser()
    args = parser.parse_args(
        [
            "--db-path",
            "x.sqlite3",
            "--knowledge-root",
            "knowledge",
            "--layouts-root",
            "layouts",
            "upload-db",
            "/incoming/personnel.db",
        ]
    )
    assert args.command == "upload-db"
    assert args.remote_path == "/incoming/personnel.db"


def test_main_download_db_dispatches_and_formats_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_ftp = InMemoryFTPClient()
    fake_ftp.connect()
    source_file = tmp_path / "remote-source.sqlite3"
    source_file.write_bytes(b"remote-db-bytes")
    fake_ftp.upload(str(source_file), "/incoming/personnel.db")
    fake_ftp.disconnect()
    monkeypatch.setattr(commands, "build_ftp_client", lambda _settings: fake_ftp)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "download-db",
            "/incoming/personnel.db",
        ]
    )

    assert exit_code == 0
    assert "database downloaded" in capsys.readouterr().out


def test_main_upload_db_dispatches_and_formats_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_ftp = InMemoryFTPClient()
    monkeypatch.setattr(commands, "build_ftp_client", lambda _settings: fake_ftp)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "upload-db",
            "/incoming/personnel.db",
        ]
    )

    assert exit_code == 0
    assert "database uploaded" in capsys.readouterr().out


def test_existing_schedule_now_command_unaffected_by_db_transfer_additions() -> None:
    assert callable(commands.schedule_now_command)
    assert callable(commands.run_workflow_command)
