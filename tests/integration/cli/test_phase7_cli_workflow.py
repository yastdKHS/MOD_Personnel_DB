"""Phase7統合Step2（Task17-2）の結合テスト。

`app.main([...])`（CLI公開API、実際のargparse解析込み）を起点に、
`cli/commands.py`の`fetch-stage`/`run-workflow`コマンドが`cli/bootstrap.py`
（Composition Root）経由で`JobOrchestrator`まで実際に到達することを確認する。

`commands.build_fetch_client`/`commands.build_ftp_client`（いずれも`cli/bootstrap.py`
からimportされたモジュール属性）を`monkeypatch`でMock実装
（`MockFetchClient`/`InMemoryFTPClient`、いずれも`tests/`ではなく`fetch/`・`ftp/`
パッケージ自身が提供するテスト用実装）に差し替えることで、**実HTTP通信・実FTP通信を
一切行わずに** `CLI → bootstrap → JobOrchestrator → FetchClient/FTPClient` の配線が
機能することを検証する。`build_application`/`build_sqlite_repositories`は実SQLite
データベース（`initialized_settings`フィクスチャ、`app.main([..., "init-db"])`経由で
スキーマ適用済み）に対して実際に動作させる。
"""

from pathlib import Path

import pytest

from mod_personnel_db.cli import app, commands
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.fetch import FetchClient, HTTPFetchClient, MockFetchClient
from mod_personnel_db.ftp import FTPClient, InMemoryFTPClient, StandardFTPClient


def _base_argv(settings: CompositionSettings) -> list[str]:
    return [
        "--db-path",
        settings.db_path,
        "--knowledge-root",
        str(settings.knowledge_root),
        "--layouts-root",
        str(settings.layouts_root),
        "--parser-code-version",
        settings.parser_code_version,
    ]


def test_fetch_stage_reaches_mock_fetch_client_via_bootstrap(
    initialized_settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """実HTTP通信を行わず、`MockFetchClient`まで到達して保存が完了することを確認する。"""
    mock_fetch_client = MockFetchClient()
    monkeypatch.setattr(commands, "build_fetch_client", lambda: mock_fetch_client)
    destination = str(tmp_path / "staged.pdf")

    exit_code = app.main(
        [
            *_base_argv(initialized_settings),
            "fetch-stage",
            "https://example.mod.go.jp/appointment.pdf",
            destination,
            "2026-01-01",
        ]
    )

    assert exit_code == 0
    assert "staged pdf: id=" in capsys.readouterr().out
    assert len(mock_fetch_client.calls) == 1
    assert mock_fetch_client.calls[0].url == "https://example.mod.go.jp/appointment.pdf"
    assert Path(destination).exists()
    assert Path(destination).read_bytes() == b"%PDF-1.4 dummy"


def test_fetch_stage_duplicate_content_hash_is_not_staged_twice(
    initialized_settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`content_hash`重複時に`JobOrchestrator.fetch_and_stage()`が`None`を返す
    既存契約（Task17-1で実装済み）が、CLI経由でも実SQLiteに対して機能することを確認する。
    """
    monkeypatch.setattr(commands, "build_fetch_client", lambda: MockFetchClient())

    first_destination = str(tmp_path / "first.pdf")
    first_exit_code = app.main(
        [
            *_base_argv(initialized_settings),
            "fetch-stage",
            "https://example.mod.go.jp/same.pdf",
            first_destination,
            "2026-01-01",
        ]
    )
    assert first_exit_code == 0

    second_destination = str(tmp_path / "second.pdf")
    second_exit_code = app.main(
        [
            *_base_argv(initialized_settings),
            "fetch-stage",
            "https://example.mod.go.jp/same.pdf",
            second_destination,
            "2026-01-01",
        ]
    )

    assert second_exit_code == 0
    assert "not staged" in capsys.readouterr().out
    assert not Path(second_destination).exists()


def test_run_workflow_reaches_in_memory_ftp_client_via_bootstrap(
    initialized_settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """実FTP通信を行わず、`InMemoryFTPClient`まで到達してアップロードが完了することを
    確認する（未処理PDF・未レビュー項目が存在しない初期状態に対する呼び出し）。
    """
    in_memory_ftp_client = InMemoryFTPClient()
    monkeypatch.setattr(commands, "build_ftp_client", lambda _settings: in_memory_ftp_client)
    destination = str(tmp_path / "export.json")

    exit_code = app.main(
        [
            *_base_argv(initialized_settings),
            "run-workflow",
            "json",
            destination,
            "--remote-path",
            "remote/export.json",
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "fetched 0 pdf(s)" in out
    assert "export: format=json" in out
    assert in_memory_ftp_client.uploaded == [(destination, "remote/export.json")]


def test_run_workflow_without_remote_path_does_not_touch_ftp_client(
    initialized_settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    in_memory_ftp_client = InMemoryFTPClient()
    monkeypatch.setattr(commands, "build_ftp_client", lambda _settings: in_memory_ftp_client)
    destination = str(tmp_path / "export.csv")

    exit_code = app.main([*_base_argv(initialized_settings), "run-workflow", "csv", destination])

    assert exit_code == 0
    assert in_memory_ftp_client.uploaded == []


def test_production_builders_still_construct_real_http_and_standard_ftp_clients(
    initialized_settings: CompositionSettings,
) -> None:
    """本番経路（`build_fetch_client()`/`build_ftp_client()`を差し替えない場合）が
    引き続き実装済みの`HTTPFetchClient`/`StandardFTPClient`を返すことを確認する
    （本テストファイルの他のテストがMock差し替えに依存していることの対照確認）。
    生成のみで`connect()`/`fetch()`は呼び出さないため、実HTTP・実FTP通信は発生しない。
    """
    fetch_client_attr = "build_fetch_client"
    fetch_client: FetchClient = getattr(commands, fetch_client_attr)()
    assert isinstance(fetch_client, HTTPFetchClient)

    ftp_client_attr = "build_ftp_client"
    ftp_client: FTPClient = getattr(commands, ftp_client_attr)(initialized_settings)
    assert isinstance(ftp_client, StandardFTPClient)
