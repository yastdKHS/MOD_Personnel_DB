"""`InMemoryFTPClient`（テスト用モック実装）の単体テスト（Phase7 Task16-1）。"""

from pathlib import Path

import pytest

from mod_personnel_db.ftp import FTPConnectionError, FTPTransferError, InMemoryFTPClient


def test_upload_requires_connect(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"content")

    with pytest.raises(FTPConnectionError):
        client.upload(str(local_file), "remote/source.pdf")


def test_download_requires_connect(tmp_path: Path) -> None:
    client = InMemoryFTPClient()

    with pytest.raises(FTPConnectionError):
        client.download("remote/source.pdf", str(tmp_path / "dest.pdf"))


def test_list_remote_requires_connect() -> None:
    client = InMemoryFTPClient()

    with pytest.raises(FTPConnectionError):
        client.list_remote("remote")


def test_upload_then_download_round_trips_bytes(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"personnel-order-body")
    dest_file = tmp_path / "downloaded.pdf"

    client.connect()
    client.upload(str(local_file), "remote/2026/source.pdf")
    client.download("remote/2026/source.pdf", str(dest_file))

    assert dest_file.read_bytes() == b"personnel-order-body"
    assert client.uploaded == [(str(local_file), "remote/2026/source.pdf")]
    assert client.downloaded == [("remote/2026/source.pdf", str(dest_file))]


def test_download_missing_remote_file_raises_transfer_error(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    client.connect()

    with pytest.raises(FTPTransferError):
        client.download("remote/missing.pdf", str(tmp_path / "dest.pdf"))


def test_upload_missing_local_file_raises_transfer_error() -> None:
    client = InMemoryFTPClient()
    client.connect()

    with pytest.raises(FTPTransferError):
        client.upload("/no/such/local/file.pdf", "remote/file.pdf")


def test_list_remote_filters_by_directory_prefix(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    client.connect()
    for name in ("remote/2026/a.pdf", "remote/2026/b.pdf", "remote/2025/c.pdf"):
        local_file = tmp_path / Path(name).name
        local_file.write_bytes(b"x")
        client.upload(str(local_file), name)

    entries = client.list_remote("remote/2026")

    assert set(entries) == {"remote/2026/a.pdf", "remote/2026/b.pdf"}


def test_rename_moves_entry_to_new_key(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    client.connect()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"content")
    client.upload(str(local_file), "remote/source.pdf")

    client.rename("remote/source.pdf", "remote/source.pdf.bak")

    dest_file = tmp_path / "dest.pdf"
    client.download("remote/source.pdf.bak", str(dest_file))
    assert dest_file.read_bytes() == b"content"
    with pytest.raises(FTPTransferError):
        client.download("remote/source.pdf", str(tmp_path / "missing.pdf"))


def test_rename_missing_source_raises_transfer_error() -> None:
    client = InMemoryFTPClient()
    client.connect()

    with pytest.raises(FTPTransferError):
        client.rename("remote/missing.pdf", "remote/missing.pdf.bak")


def test_rename_requires_connect() -> None:
    client = InMemoryFTPClient()

    with pytest.raises(FTPConnectionError):
        client.rename("remote/a.pdf", "remote/b.pdf")


def test_delete_removes_entry(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    client.connect()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"content")
    client.upload(str(local_file), "remote/source.pdf.bak")

    client.delete("remote/source.pdf.bak")

    with pytest.raises(FTPTransferError):
        client.download("remote/source.pdf.bak", str(tmp_path / "missing.pdf"))


def test_delete_missing_target_raises_transfer_error() -> None:
    client = InMemoryFTPClient()
    client.connect()

    with pytest.raises(FTPTransferError):
        client.delete("remote/missing.pdf")


def test_delete_requires_connect() -> None:
    client = InMemoryFTPClient()

    with pytest.raises(FTPConnectionError):
        client.delete("remote/a.pdf")


def test_disconnect_then_upload_raises(tmp_path: Path) -> None:
    client = InMemoryFTPClient()
    client.connect()
    client.disconnect()
    local_file = tmp_path / "source.pdf"
    local_file.write_bytes(b"content")

    with pytest.raises(FTPConnectionError):
        client.upload(str(local_file), "remote/source.pdf")
