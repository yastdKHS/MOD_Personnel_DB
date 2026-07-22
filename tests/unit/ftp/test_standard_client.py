"""`StandardFTPClient`の単体テスト（Phase7 Task16-1）。

`ftplib.FTP`は`unittest.mock`で差し替え、実際のネットワーク接続は行わない
（実ネットワークを用いた検証は`tests/integration/ftp/`が担う）。
"""

import ftplib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mod_personnel_db.ftp import FTPConnectionConfig, FTPConnectionError, FTPTransferError
from mod_personnel_db.ftp.client import StandardFTPClient


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_connect_logs_in_and_sets_passive_mode(ftp_cls: MagicMock) -> None:
    connection = ftp_cls.return_value
    config = FTPConnectionConfig(host="ftp.example.jp", port=2121, username="u", password="p")
    client = StandardFTPClient(config)

    client.connect()

    connection.connect.assert_called_once_with("ftp.example.jp", 2121, timeout=30.0)
    connection.login.assert_called_once_with("u", "p")
    connection.set_pasv.assert_called_once_with(True)


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_connect_is_idempotent(ftp_cls: MagicMock) -> None:
    config = FTPConnectionConfig(host="ftp.example.jp")
    client = StandardFTPClient(config)

    client.connect()
    client.connect()

    assert ftp_cls.call_count == 1


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_connect_wraps_os_error(ftp_cls: MagicMock) -> None:
    ftp_cls.return_value.connect.side_effect = OSError("connection refused")
    config = FTPConnectionConfig(host="ftp.example.jp")
    client = StandardFTPClient(config)

    with pytest.raises(FTPConnectionError):
        client.connect()


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_connect_wraps_ftplib_error(ftp_cls: MagicMock) -> None:
    ftp_cls.return_value.login.side_effect = ftplib.error_perm("530 Login incorrect")
    config = FTPConnectionConfig(host="ftp.example.jp")
    client = StandardFTPClient(config)

    with pytest.raises(FTPConnectionError):
        client.connect()


def test_upload_without_connect_raises() -> None:
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))

    with pytest.raises(FTPConnectionError):
        client.upload("local.pdf", "remote.pdf")


def test_download_without_connect_raises() -> None:
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))

    with pytest.raises(FTPConnectionError):
        client.download("remote.pdf", "local.pdf")


def test_list_remote_without_connect_raises() -> None:
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))

    with pytest.raises(FTPConnectionError):
        client.list_remote("remote")


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_upload_calls_storbinary_with_command_and_stream(
    ftp_cls: MagicMock, tmp_path: Path
) -> None:
    connection = ftp_cls.return_value
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"content")

    client.upload(str(local_file), "remote/2026/source.pdf")

    args, _ = connection.storbinary.call_args
    assert args[0] == "STOR remote/2026/source.pdf"


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_upload_wraps_ftplib_error(ftp_cls: MagicMock, tmp_path: Path) -> None:
    connection = ftp_cls.return_value
    connection.storbinary.side_effect = ftplib.error_perm("553 Could not create file")
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"content")

    with pytest.raises(FTPTransferError):
        client.upload(str(local_file), "remote/source.pdf")


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_upload_missing_local_file_raises_transfer_error(
    ftp_cls: MagicMock, tmp_path: Path
) -> None:
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()

    with pytest.raises(FTPTransferError):
        client.upload(str(tmp_path / "missing.pdf"), "remote/source.pdf")


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_download_calls_retrbinary_and_writes_local_file(
    ftp_cls: MagicMock, tmp_path: Path
) -> None:
    connection = ftp_cls.return_value

    def fake_retrbinary(command: str, callback: object) -> None:
        assert command == "RETR remote/source.pdf"
        callback(b"downloaded-bytes")  # type: ignore[operator]

    connection.retrbinary.side_effect = fake_retrbinary
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()
    dest_file = tmp_path / "dest.pdf"

    client.download("remote/source.pdf", str(dest_file))

    assert dest_file.read_bytes() == b"downloaded-bytes"


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_download_wraps_ftplib_error(ftp_cls: MagicMock, tmp_path: Path) -> None:
    connection = ftp_cls.return_value
    connection.retrbinary.side_effect = ftplib.error_perm("550 No such file")
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()

    with pytest.raises(FTPTransferError):
        client.download("remote/missing.pdf", str(tmp_path / "dest.pdf"))


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_list_remote_returns_tuple_of_names(ftp_cls: MagicMock) -> None:
    connection = ftp_cls.return_value
    connection.nlst.return_value = ["remote/a.pdf", "remote/b.pdf"]
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()

    entries = client.list_remote("remote")

    connection.nlst.assert_called_once_with("remote")
    assert entries == ("remote/a.pdf", "remote/b.pdf")


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_list_remote_wraps_ftplib_error(ftp_cls: MagicMock) -> None:
    connection = ftp_cls.return_value
    connection.nlst.side_effect = ftplib.error_perm("550 No such directory")
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()

    with pytest.raises(FTPTransferError):
        client.list_remote("remote")


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_disconnect_calls_quit_and_clears_connection(ftp_cls: MagicMock) -> None:
    connection = ftp_cls.return_value
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()

    client.disconnect()

    connection.quit.assert_called_once()
    with pytest.raises(FTPConnectionError):
        client.list_remote("remote")


@patch("mod_personnel_db.ftp.client.ftplib.FTP")
def test_disconnect_falls_back_to_close_on_error(ftp_cls: MagicMock) -> None:
    connection = ftp_cls.return_value
    connection.quit.side_effect = ftplib.error_temp("421 Service not available")
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))
    client.connect()

    client.disconnect()

    connection.close.assert_called_once()


def test_disconnect_without_connect_is_noop() -> None:
    client = StandardFTPClient(FTPConnectionConfig(host="ftp.example.jp"))

    client.disconnect()
