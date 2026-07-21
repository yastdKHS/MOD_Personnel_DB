import argparse
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mod_personnel_db.cli import app, commands
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings
from mod_personnel_db.cli.bootstrap import build_job_runner as _real_build_job_runner
from mod_personnel_db.cli.commands import VersionInfo
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.models import PdfId, PdfRecord
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.repositories.sqlite import SqlitePdfRepository, connect


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


def _insert_pdf(settings: CompositionSettings) -> PdfId:
    connection = connect(settings.db_path)
    try:
        repo = SqlitePdfRepository(connection)
        return repo.add(
            PdfRecord(
                id=None,
                content_hash="a" * 64,
                source_url="https://example.mod.go.jp/appointment.pdf",
                published_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                file_path="aa/aa/" + "a" * 64 + ".pdf",
                file_size_bytes=1024,
                status="fetched",
            )
        )
    finally:
        connection.close()


class _StubJobRunner:
    """`run_for_pdf`が実パイプラインを起動せずに固定結果を返すStub。"""

    def __init__(self) -> None:
        self.received_pdf: PdfRecord | None = None

    def run_for_pdf(self, pdf: PdfRecord) -> Any:
        self.received_pdf = pdf
        return SimpleNamespace(job=SimpleNamespace(status="succeeded"))

    def run_pending(self) -> tuple[PipelineResult, ...]:
        return ()


class _StubApplication:
    """`Application`と同じ形状（`job_runner`・`read_pdf`）を持つテスト専用Stub。"""

    def __init__(self, pdf: PdfRecord, job_runner: _StubJobRunner) -> None:
        self._pdf = pdf
        self.job_runner = job_runner

    def read_pdf(self, pdf_id: PdfId) -> PdfRecord | None:
        return self._pdf if self._pdf.id == pdf_id else None


def test_help_command_lists_available_commands(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = app.main(["help"])

    output = capsys.readouterr().out
    assert exit_code == 0
    for command in app.COMMANDS:
        assert command in output


def test_help_command_does_not_require_settings(capsys: pytest.CaptureFixture[str]) -> None:
    # --db-path等を一切渡さなくてもhelpは成功する。
    exit_code = app.main(["help"])
    assert exit_code == 0


def test_init_db_command_creates_schema(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db_path = tmp_path / "fresh.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    layouts_root = tmp_path / "layouts"
    knowledge_root.mkdir()
    layouts_root.mkdir()
    argv = [
        "--db-path",
        str(db_path),
        "--knowledge-root",
        str(knowledge_root),
        "--layouts-root",
        str(layouts_root),
        "init-db",
    ]

    exit_code = app.main(argv)

    assert exit_code == 0
    assert "initialized" in capsys.readouterr().out
    connection = sqlite3.connect(str(db_path))
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()
    assert "learning_dataset" in tables


def test_run_pending_command_with_no_pending_pdfs(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*_base_argv(settings), "run-pending"])

    assert exit_code == 0
    assert "processed 0 pdf(s)" in capsys.readouterr().out


def test_run_job_command_missing_pdf_returns_error(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*_base_argv(settings), "run-job", "999"])

    assert exit_code == 1
    assert "error:" in capsys.readouterr().out


def test_run_job_command_processes_existing_pdf(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pdf_id = _insert_pdf(settings)
    stub_job_runner = _StubJobRunner()

    def fake_build_application(settings_arg: CompositionSettings) -> Application:
        connection = connect(settings_arg.db_path)
        pdf = SqlitePdfRepository(connection).get(pdf_id)
        assert pdf is not None
        return _StubApplication(pdf, stub_job_runner)  # type: ignore[return-value]

    monkeypatch.setattr(commands, "build_application", fake_build_application)

    exit_code = app.main([*_base_argv(settings), "run-job", str(int(pdf_id))])

    assert exit_code == 0
    assert "job status: succeeded" in capsys.readouterr().out
    assert stub_job_runner.received_pdf is not None
    assert stub_job_runner.received_pdf.id == pdf_id


def test_version_command_outputs_knowledge_snapshot(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*_base_argv(settings), "version"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "knowledge_snapshot" in output
    assert "parser_version" in output


def test_version_command_reuses_existing_parser_version(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    app.main([*_base_argv(settings), "version"])
    first_output = capsys.readouterr().out

    app.main([*_base_argv(settings), "version"])
    second_output = capsys.readouterr().out

    assert first_output == second_output


def test_format_version_with_no_parser_version_recorded() -> None:
    info = VersionInfo(
        parser_version=None,
        knowledge_snapshot_checksum="deadbeef",
        knowledge_item_count=0,
        knowledge_as_of=date(2026, 1, 1),
    )

    formatted = app._format_version(info)

    assert "parser_version: (none recorded)" in formatted


def test_dispatch_unknown_command_raises_cli_command_error(
    settings: CompositionSettings,
) -> None:
    args = argparse.Namespace(
        db_path=settings.db_path,
        knowledge_root=settings.knowledge_root,
        layouts_root=settings.layouts_root,
        parser_code_version=settings.parser_code_version,
    )
    parser = app.build_parser()

    with pytest.raises(CliCommandError):
        app._dispatch("bogus", args, parser)


def test_invalid_command_raises_systemexit() -> None:
    with pytest.raises(SystemExit):
        app.main(["not-a-real-command"])


def test_missing_required_options_returns_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = app.main(["run-pending"])

    assert exit_code == 1
    assert "error:" in capsys.readouterr().out


def test_composition_root_built_once_for_run_pending(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_count = 0

    def counting_build_job_runner(settings_arg: CompositionSettings) -> object:
        nonlocal call_count
        call_count += 1
        return _real_build_job_runner(settings_arg)

    monkeypatch.setattr(commands, "build_job_runner", counting_build_job_runner)

    app.main([*_base_argv(settings), "run-pending"])

    assert call_count == 1


def test_composition_root_built_once_for_run_job(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_id = _insert_pdf(settings)
    stub_job_runner = _StubJobRunner()
    call_count = 0

    def counting_build_application(settings_arg: CompositionSettings) -> Application:
        nonlocal call_count
        call_count += 1
        connection = connect(settings_arg.db_path)
        pdf = SqlitePdfRepository(connection).get(pdf_id)
        assert pdf is not None
        return _StubApplication(pdf, stub_job_runner)  # type: ignore[return-value]

    monkeypatch.setattr(commands, "build_application", counting_build_application)

    app.main([*_base_argv(settings), "run-job", str(int(pdf_id))])

    assert call_count == 1


def test_run_pending_command_invokes_job_runner(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub_job_runner = _StubJobRunner()
    calls: list[str] = []
    original_run_pending = stub_job_runner.run_pending

    def tracked_run_pending() -> tuple[PipelineResult, ...]:
        calls.append("run_pending")
        return original_run_pending()

    stub_job_runner.run_pending = tracked_run_pending  # type: ignore[method-assign]

    def fake_build_job_runner(settings_arg: CompositionSettings) -> object:
        del settings_arg
        return stub_job_runner

    monkeypatch.setattr(commands, "build_job_runner", fake_build_job_runner)

    exit_code = app.main([*_base_argv(settings), "run-pending"])

    assert exit_code == 0
    assert calls == ["run_pending"]
