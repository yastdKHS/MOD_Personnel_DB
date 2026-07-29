import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from mod_personnel_db.cli import bootstrap as bootstrap_module
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

    @contextmanager
    def fake_application_session(settings_arg: CompositionSettings) -> Iterator[Application]:
        del settings_arg
        yield SimpleNamespace(job_runner=stub)  # type: ignore[misc]

    monkeypatch.setattr(commands, "application_session", fake_application_session)

    result = commands.run_pending_command(settings)

    assert stub.run_pending_called is True
    assert result == ()


def test_run_pending_command_end_to_end_with_no_pending_pdfs(
    settings: CompositionSettings,
) -> None:
    result = commands.run_pending_command(settings)

    assert result == ()


def test_job_orchestrator_session_calls_connect_exactly_once(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`bootstrap.job_orchestrator_session()`は`connect()`を1回のみ呼び出し、
    Application生成（`build_application_with_repositories()`）とJobOrchestrator
    生成（`build_sqlite_repositories()`が返す`repositories.pdfs`）とで同一
    Connectionを共有する（Task21-2、Task22-8でSession Builder化）。以前は
    `build_application()`内部でも独自に`connect()`が呼ばれ、同一`db_path`への
    接続が1回のコマンド実行あたり2本生成されていた（Task20-2で判明）。
    """
    connect_calls: list[str] = []

    def counting_connect(db_path: str) -> sqlite3.Connection:
        connect_calls.append(db_path)
        return connect(db_path)

    monkeypatch.setattr(bootstrap_module, "connect", counting_connect)

    with bootstrap_module.job_orchestrator_session(settings) as orchestrator:
        assert orchestrator is not None

    assert connect_calls == [settings.db_path]


def test_job_orchestrator_session_calls_build_sqlite_repositories_exactly_once(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`bootstrap.job_orchestrator_session()`は`build_application_with_repositories()`を
    経由して`build_sqlite_repositories()`を1回のみ呼び出す（Task22-6、Task22-8で
    Session Builder化）。以前は`build_application()`用とJobOrchestrator用とで
    それぞれ1回ずつ、計2回`build_sqlite_repositories()`が呼ばれ、`jobs`/`gold`/
    `knowledge`/`review`/`export`/`learning`の各Repositoryが未使用のまま二重生成
    されていた（Task20-2で判明、Task21-6/21-7で改善候補化）。
    """
    build_sqlite_repositories_calls: list[sqlite3.Connection] = []
    original_build_sqlite_repositories = bootstrap_module.build_sqlite_repositories

    def counting_build_sqlite_repositories(
        connection: sqlite3.Connection,
    ) -> bootstrap_module.SqliteRepositories:
        build_sqlite_repositories_calls.append(connection)
        return original_build_sqlite_repositories(connection)

    monkeypatch.setattr(
        bootstrap_module, "build_sqlite_repositories", counting_build_sqlite_repositories
    )

    with bootstrap_module.job_orchestrator_session(settings) as orchestrator:
        assert orchestrator is not None

    assert len(build_sqlite_repositories_calls) == 1


def test_version_command_closes_connection(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`version_command()`は他コマンドと同様、`bootstrap.version_dependencies_session()`
    が生成したConnectionを必ず`close()`する（Task22-1、Task22-8でSession
    Builder化した後もclose責務自体は維持されていることを確認する）。
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

    monkeypatch.setattr(bootstrap_module, "connect", fake_connect)

    info = commands.version_command(settings)

    assert close_calls == [True]
    assert info.knowledge_item_count == 0
