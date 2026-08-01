import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from mod_personnel_db.cli import bootstrap as bootstrap_module
from mod_personnel_db.cli import commands
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings
from mod_personnel_db.pipeline.result import PipelineResult


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
