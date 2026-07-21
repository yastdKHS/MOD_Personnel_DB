import argparse
import sqlite3
import uuid
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
from mod_personnel_db.models import (
    CandidateId,
    ErrorCategory,
    GoldRecord,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    NormalizedRecord,
    NormalizedValue,
    PdfId,
    PdfRecord,
    PipelineStageName,
    RawRecord,
    RegressionStatus,
)
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.repositories.sqlite import (
    SqliteGoldRepository,
    SqliteLearningRepository,
    SqlitePdfRepository,
    connect,
)
from mod_personnel_db.utils.exceptions import RepositoryError


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


def _make_learning_record(status: LearningStatus = LearningStatus.OPEN) -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.VALIDATOR,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="大将?",
        # `review start`はcorrect_valueを追加引数として受け取らないため、
        # status='open'の時点で既に確定している想定でテストデータを用意する
        # （モデルの不変条件はstatus!='open'でのcorrect_value必須のみを課しており、
        # status='open'でcorrect_valueが設定済みであること自体は禁止されない）。
        correct_value="大将",
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=None,
        layout_id=None,
        confidence=None,
        status=status,
        reflected_in_knowledge_item_id=None,
        reflected_in_layout_id=None,
        git_commit_hash=None,
        pull_request_url=None,
        regression_status=RegressionStatus.NOT_RUN,
        regression_run_at=None,
        regression_details=None,
        improvement_candidate=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        resolved_at=None,
    )


def _insert_learning_record(
    settings: CompositionSettings, status: LearningStatus = LearningStatus.OPEN
) -> LearningRecordId:
    connection = connect(settings.db_path)
    try:
        return SqliteLearningRepository(connection).add(_make_learning_record(status))
    finally:
        connection.close()


def _insert_candidate_id(connection: sqlite3.Connection) -> CandidateId:
    """gold_records.candidate_record_idのFOREIGN KEY制約を満たすための最小限の
    先行データ（parser_versions/pdfs/layouts/personnel_sections/candidate_records）
    を直接SQLで作成する（テスト専用、tests/unit/repositories/conftest.pyの
    layout_idフィクスチャと同じ方針）。UNIQUE制約回避のため呼び出しごとに
    一意な値を用いる。
    """
    unique = uuid.uuid4().hex
    parser_version_id = connection.execute(
        "INSERT INTO parser_versions (code_version, knowledge_snapshot_checksum) VALUES (?, ?)",
        (f"v1.0.0-test-{unique}", "c" * 64),
    ).lastrowid
    pdf_id = connection.execute(
        "INSERT INTO pdfs (content_hash, source_url, published_date, file_path, file_size_bytes) "
        "VALUES (?, 'https://example.mod.go.jp/x.pdf', '2026-01-01', ?, 1024)",
        (unique, f"bb/bb/{unique}.pdf"),
    ).lastrowid
    layout_id = connection.execute(
        "INSERT INTO layouts (era_id, manifest_path, manifest_checksum, valid_from) "
        "VALUES (?, 'layouts/reiwa/manifest.yaml', ?, '2019-05-01')",
        (f"reiwa-{unique}", "d" * 64),
    ).lastrowid
    section_id = connection.execute(
        "INSERT INTO personnel_sections "
        "(pdf_id, layout_id, parser_version_id, section_index, section_text) "
        "VALUES (?, ?, ?, 0, 'text')",
        (pdf_id, layout_id, parser_version_id),
    ).lastrowid
    candidate_id = connection.execute(
        "INSERT INTO candidate_records "
        "(personnel_section_id, parser_version_id, record_index, raw_fields) "
        'VALUES (?, ?, 0, \'{"rank": "大将?"}\')',
        (section_id, parser_version_id),
    ).lastrowid
    connection.commit()
    assert candidate_id is not None
    return CandidateId(candidate_id)


def _insert_gold_record(settings: CompositionSettings, person_key: str) -> GoldRecord:
    connection = connect(settings.db_path)
    try:
        candidate_id = _insert_candidate_id(connection)
        repository = SqliteGoldRepository(connection)
        raw = RawRecord(
            section_ref=None,
            layout_id="reiwa",
            record_index=0,
            raw_fields={"rank": "大将?"},
            extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        record = NormalizedRecord(
            raw_record_ref=raw,
            normalized_fields={"rank": NormalizedValue(value="大将", raw="大将?")},
            normalization_applied=(),
            normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        record_id = repository.add_version(
            candidate_id, record, person_key, date(2026, 1, 1), "promotion"
        )
        current = repository.get_current(person_key, date(2026, 1, 1))
        assert current is not None
        assert current.id == record_id
        return current
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

    with pytest.raises(CliCommandError):
        app._dispatch("bogus", args, settings)


def test_dispatch_review_unknown_action_raises_cli_command_error(
    settings: CompositionSettings,
) -> None:
    args = argparse.Namespace(review_action="bogus", record_id=1)

    with pytest.raises(CliCommandError):
        app._dispatch_review(args, settings)


def test_dispatch_export_unknown_action_raises_cli_command_error(
    settings: CompositionSettings,
) -> None:
    args = argparse.Namespace(export_action="bogus")

    with pytest.raises(CliCommandError):
        app._dispatch_export(args, settings)


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


def test_review_list_command_shows_pending_items(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = _insert_learning_record(settings)

    exit_code = app.main([*_base_argv(settings), "review", "list"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 pending review item(s):" in output
    assert str(int(record_id)) in output


def test_review_list_command_empty(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*_base_argv(settings), "review", "list"])

    assert exit_code == 0
    assert "0 pending review item(s)" in capsys.readouterr().out


def test_review_start_command_transitions_open_to_in_review(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = _insert_learning_record(settings)

    exit_code = app.main([*_base_argv(settings), "review", "start", str(int(record_id))])

    assert exit_code == 0
    assert f"record {int(record_id)}: status={LearningStatus.IN_REVIEW}" in capsys.readouterr().out


def test_review_approve_command_transitions_in_review_to_reflected(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = _insert_learning_record(settings)
    app.main([*_base_argv(settings), "review", "start", str(int(record_id))])
    capsys.readouterr()

    exit_code = app.main([*_base_argv(settings), "review", "approve", str(int(record_id))])

    assert exit_code == 0
    assert f"record {int(record_id)}: status={LearningStatus.REFLECTED}" in capsys.readouterr().out


def test_review_reject_command_transitions_in_review_to_wontfix(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record_id = _insert_learning_record(settings)
    app.main([*_base_argv(settings), "review", "start", str(int(record_id))])
    capsys.readouterr()

    exit_code = app.main([*_base_argv(settings), "review", "reject", str(int(record_id))])

    assert exit_code == 0
    assert f"record {int(record_id)}: status={LearningStatus.WONTFIX}" in capsys.readouterr().out


def test_export_all_command_lists_current_gold_records(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    record = _insert_gold_record(settings, "person-1")

    exit_code = app.main([*_base_argv(settings), "export", "all"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 record(s):" in output
    assert str(int(record.id)) in output
    assert "person-1" in output


def test_export_all_command_empty(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*_base_argv(settings), "export", "all"])

    assert exit_code == 0
    assert "0 record(s)" in capsys.readouterr().out


def test_export_person_command_filters_by_person_key(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    _insert_gold_record(settings, "person-a")
    _insert_gold_record(settings, "person-b")

    exit_code = app.main([*_base_argv(settings), "export", "person", "person-a"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 record(s):" in output
    assert "person-a" in output
    assert "person-b" not in output


def test_export_since_command_parses_iso8601_and_delegates(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    _insert_gold_record(settings, "person-1")

    exit_code = app.main([*_base_argv(settings), "export", "since", "2099-01-01T00:00:00+00:00"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "1 record(s):" in output
    assert "person-1" in output


def test_export_since_command_invalid_datetime_returns_error(
    settings: CompositionSettings, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = app.main([*_base_argv(settings), "export", "since", "not-a-datetime"])

    assert exit_code == 1
    assert "error:" in capsys.readouterr().out


def test_review_start_with_non_integer_record_id_raises_systemexit(
    settings: CompositionSettings,
) -> None:
    with pytest.raises(SystemExit):
        app.main([*_base_argv(settings), "review", "start", "not-an-int"])


def test_review_missing_subcommand_raises_systemexit(settings: CompositionSettings) -> None:
    with pytest.raises(SystemExit):
        app.main([*_base_argv(settings), "review"])


def test_export_missing_subcommand_raises_systemexit(settings: CompositionSettings) -> None:
    with pytest.raises(SystemExit):
        app.main([*_base_argv(settings), "export"])


class _RaisingReviewService:
    """`RepositoryError`をそのまま送出するReviewServiceのStub。"""

    def list_pending(self) -> tuple[LearningRecord, ...]:
        raise RepositoryError("stub failure in list_pending")


def test_review_list_command_propagates_repository_error(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_build_application(settings_arg: CompositionSettings) -> Application:
        del settings_arg
        return SimpleNamespace(review_service=_RaisingReviewService())  # type: ignore[return-value]

    monkeypatch.setattr(commands, "build_application", fake_build_application)

    with pytest.raises(RepositoryError):
        app.main([*_base_argv(settings), "review", "list"])


class _RaisingExportService:
    """`RepositoryError`をそのまま送出するExportServiceのStub。"""

    def export_all(self) -> tuple[GoldRecord, ...]:
        raise RepositoryError("stub failure in export_all")


def test_export_all_command_propagates_repository_error(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_build_application(settings_arg: CompositionSettings) -> Application:
        del settings_arg
        return SimpleNamespace(export_service=_RaisingExportService())  # type: ignore[return-value]

    monkeypatch.setattr(commands, "build_application", fake_build_application)

    with pytest.raises(RepositoryError):
        app.main([*_base_argv(settings), "export", "all"])
