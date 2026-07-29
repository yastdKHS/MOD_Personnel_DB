import sqlite3
from types import SimpleNamespace

import pytest

from mod_personnel_db.cli import commands
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.repositories.sqlite import connect


class _StubJobRunner:
    """`run_pending_command`がJobRunner.run_pending()を呼ぶことを確認するためのStub。"""

    def __init__(self) -> None:
        self.run_pending_called = False

    def run_pending(self) -> tuple[PipelineResult, ...]:
        self.run_pending_called = True
        return ()


def test_run_pending_command_invokes_job_runner_run_pending(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    stub = _StubJobRunner()

    def fake_build_application(
        settings_arg: CompositionSettings, connection: sqlite3.Connection | None = None
    ) -> Application:
        del settings_arg, connection
        return SimpleNamespace(job_runner=stub)  # type: ignore[return-value]

    monkeypatch.setattr(commands, "build_application", fake_build_application)

    result = commands.run_pending_command(settings)

    assert stub.run_pending_called is True
    assert result == ()


def test_run_pending_command_end_to_end_with_no_pending_pdfs(
    settings: CompositionSettings,
) -> None:
    result = commands.run_pending_command(settings)

    assert result == ()


def test_build_job_orchestrator_calls_connect_exactly_once(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`_build_job_orchestrator()`は`connect()`を1回のみ呼び出し、Application生成
    （`build_application()`）とJobOrchestrator生成（`build_sqlite_repositories()`
    が返す`repositories.pdfs`）とで同一Connectionを共有する（Task21-2、Task21-1
    で選定した案B）。以前は`build_application()`内部でも独自に`connect()`が
    呼ばれ、同一`db_path`への接続が1回のコマンド実行あたり2本生成されていた
    （Task20-2で判明）。
    """
    connect_calls: list[str] = []

    def counting_connect(db_path: str) -> sqlite3.Connection:
        connect_calls.append(db_path)
        return connect(db_path)

    monkeypatch.setattr(commands, "connect", counting_connect)

    orchestrator, connection = commands._build_job_orchestrator(settings)
    connection.close()

    assert connect_calls == [settings.db_path]
    assert orchestrator is not None


def test_version_command_closes_connection(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`version_command()`は他コマンドと同様、`connect()`で生成したConnectionを
    `try/finally`で必ず`close()`する（Task22-1、Task21-4の他8コマンドとの統一）。
    """
    close_calls: list[bool] = []

    class _TrackingConnection(sqlite3.Connection):
        def close(self) -> None:
            close_calls.append(True)
            super().close()

    def fake_connect(db_path: str) -> sqlite3.Connection:
        connection = sqlite3.connect(db_path, factory=_TrackingConnection)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    monkeypatch.setattr(commands, "connect", fake_connect)

    info = commands.version_command(settings)

    assert close_calls == [True]
    assert info.knowledge_item_count == 0
