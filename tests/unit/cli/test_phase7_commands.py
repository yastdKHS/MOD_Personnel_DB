"""Phase7統合Step2（Task17-2）: `fetch-stage`/`run-workflow`コマンドの単体テスト。

Task17-1で`cli/bootstrap.py`に追加された`build_fetch_client()`/`build_ftp_client()`/
`build_job_orchestrator()`を、`cli/commands.py`が`JobOrchestrator`Protocol経由での
み呼び出すこと、`cli/app.py`が新規サブコマンド（`fetch-stage`/`run-workflow`）を
正しく登録・ディスパッチすることを検証する。`HTTPFetchClient`・`StandardFTPClient`は
本テストファイルでも一切直接インスタンス化しない（`commands._build_job_orchestrator`
をFakeで差し替えることで代替する）。`DefaultJobOrchestrator`は
`bootstrap.build_job_orchestrator()`経由の生成結果を型検証する目的でのみ`isinstance`
チェックに使用する（テストコード自身が新規生成することはない）。
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mod_personnel_db.cli import app, commands
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.fetch import FetchRequest
from mod_personnel_db.models import ExportArtifact, ExportFormat, LearningRecord, PdfId, PdfRecord
from mod_personnel_db.pipeline import PipelineResult
from mod_personnel_db.services import WorkflowResult
from mod_personnel_db.services.orchestrator import DefaultJobOrchestrator


@dataclass
class _RecordingJobOrchestrator:
    """`JobOrchestrator`Protocolを満たすFake実装。呼び出し引数を記録するのみで、
    実際のFetch/FTP/Pipeline/Review/Export処理は一切行わない。
    """

    fetch_and_stage_calls: list[tuple[FetchRequest, str, date]] = field(default_factory=list)
    run_workflow_calls: list[tuple[list[object], ExportFormat, object, str | None]] = field(
        default_factory=list
    )
    fetch_and_stage_result: PdfId | None = PdfId(1)
    workflow_result: WorkflowResult | None = None

    def fetch_and_stage(
        self, request: FetchRequest, *, destination_path: str, published_date: date
    ) -> PdfId | None:
        self.fetch_and_stage_calls.append((request, destination_path, published_date))
        return self.fetch_and_stage_result

    def run_job(self, pdf: PdfRecord) -> PipelineResult:
        raise NotImplementedError

    def run_pending_pipeline(self) -> tuple[PipelineResult, ...]:
        raise NotImplementedError

    def list_pending_reviews(self) -> tuple[LearningRecord, ...]:
        raise NotImplementedError

    def export_and_publish(
        self, export_format: ExportFormat, destination: object, *, remote_path: str | None = None
    ) -> ExportArtifact:
        raise NotImplementedError

    def run_workflow(
        self,
        fetch_items: list[object],
        export_format: ExportFormat,
        export_destination: object,
        *,
        remote_path: str | None = None,
    ) -> WorkflowResult:
        self.run_workflow_calls.append(
            (fetch_items, export_format, export_destination, remote_path)
        )
        assert self.workflow_result is not None
        return self.workflow_result


def _default_workflow_result() -> WorkflowResult:
    return WorkflowResult(
        fetched_pdf_ids=(),
        fetch_errors=(),
        pipeline_results=(),
        pending_review_count=0,
        export_artifact=ExportArtifact(
            export_id="export-1",
            exported_at=datetime(2026, 1, 1, tzinfo=UTC),
            format="json",
            record_count=0,
            sha256="e" * 64,
        ),
    )


# --- 「JobOrchestrator呼び出し」: Protocol経由のみで正しい引数が渡ることを確認 ---


def test_fetch_stage_command_calls_job_orchestrator_via_protocol(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator()
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)

    result = commands.fetch_stage_command(
        settings, "https://example.mod.go.jp/x.pdf", "/tmp/x.pdf", date(2026, 1, 1)
    )

    assert result == PdfId(1)
    assert len(fake_orchestrator.fetch_and_stage_calls) == 1
    request, destination_path, published_date = fake_orchestrator.fetch_and_stage_calls[0]
    assert request.url == "https://example.mod.go.jp/x.pdf"
    assert destination_path == "/tmp/x.pdf"
    assert published_date == date(2026, 1, 1)


def test_run_workflow_command_calls_job_orchestrator_via_protocol(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator(workflow_result=_default_workflow_result())
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)

    result = commands.run_workflow_command(
        settings, "json", "/tmp/export.json", remote_path="remote/export.json"
    )

    assert result is fake_orchestrator.workflow_result
    assert len(fake_orchestrator.run_workflow_calls) == 1
    fetch_items, export_format, export_destination, remote_path = (
        fake_orchestrator.run_workflow_calls[0]
    )
    assert fetch_items == []
    assert export_format == "json"
    assert export_destination == "/tmp/export.json"
    assert remote_path == "remote/export.json"


def test_run_workflow_command_defaults_to_empty_fetch_items_and_no_remote_path(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator(workflow_result=_default_workflow_result())
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)

    commands.run_workflow_command(settings, "csv", "/tmp/export.csv")

    _, _, _, remote_path = fake_orchestrator.run_workflow_calls[0]
    assert remote_path is None


# --- 「CLI→bootstrap呼び出し」: _build_job_orchestrator()がbootstrap.pyのBuilderのみ
# を、期待した引数で1回ずつ呼び出すことを確認 ---


def _tracer(order: list[str], label: str, real: object) -> object:
    """`tests/unit/cli/test_bootstrap.py`の`_tracer`と同じ流儀: 呼び出しを`order`へ
    記録してから`real`（元の関数）へ委譲するラッパーを返す。`getattr`経由で元の関数を
    取得することで、`commands`モジュールの`__all__`に含まれない名前への静的な属性
    アクセス（mypy --strictのno-implicit-reexport制約）を回避する。
    """

    def wrapper(*args: object, **kwargs: object) -> object:
        order.append(label)
        return real(*args, **kwargs)  # type: ignore[operator]

    return wrapper


_ORCHESTRATOR_GENERATION_ORDER_TARGETS = (
    "build_application",
    "build_sqlite_repositories",
    "build_fetch_client",
    "build_ftp_client",
    "build_job_orchestrator",
)


def test_build_job_orchestrator_helper_calls_each_bootstrap_builder_once(
    settings: CompositionSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    for attr_name in _ORCHESTRATOR_GENERATION_ORDER_TARGETS:
        real = getattr(commands, attr_name)
        monkeypatch.setattr(commands, attr_name, _tracer(calls, attr_name, real))

    orchestrator = commands._build_job_orchestrator(settings)

    assert isinstance(orchestrator, DefaultJobOrchestrator)
    assert calls == list(_ORCHESTRATOR_GENERATION_ORDER_TARGETS)


# --- 「CLIコマンド登録」: app.COMMANDS・argparseサブパーサへの登録を確認 ---


def test_commands_tuple_includes_new_phase7_subcommands() -> None:
    assert "fetch-stage" in app.COMMANDS
    assert "run-workflow" in app.COMMANDS
    # 既存7コマンド + help を含め、後方互換のため既存コマンドが失われていないことを確認する。
    for existing in (
        "init-db",
        "run-pending",
        "run-job",
        "version",
        "review",
        "export",
        "help",
    ):
        assert existing in app.COMMANDS


def test_parser_accepts_fetch_stage_arguments() -> None:
    parser = app.build_parser()
    args = parser.parse_args(
        [
            "--db-path",
            "x.sqlite3",
            "--knowledge-root",
            "knowledge",
            "--layouts-root",
            "layouts",
            "fetch-stage",
            "https://example.mod.go.jp/x.pdf",
            "/tmp/x.pdf",
            "2026-01-01",
        ]
    )
    assert args.command == "fetch-stage"
    assert args.url == "https://example.mod.go.jp/x.pdf"
    assert args.destination_path == "/tmp/x.pdf"
    assert args.published_date == "2026-01-01"


def test_parser_accepts_run_workflow_arguments_with_remote_path() -> None:
    parser = app.build_parser()
    args = parser.parse_args(
        [
            "--db-path",
            "x.sqlite3",
            "--knowledge-root",
            "knowledge",
            "--layouts-root",
            "layouts",
            "run-workflow",
            "json",
            "/tmp/export.json",
            "--remote-path",
            "remote/export.json",
        ]
    )
    assert args.command == "run-workflow"
    assert args.export_format == "json"
    assert args.export_destination == "/tmp/export.json"
    assert args.remote_path == "remote/export.json"


def test_parser_rejects_invalid_export_format() -> None:
    parser = app.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--db-path",
                "x.sqlite3",
                "--knowledge-root",
                "knowledge",
                "--layouts-root",
                "layouts",
                "run-workflow",
                "xml",
                "/tmp/export.xml",
            ]
        )


# --- app.main()経由のディスパッチ（Fakeへ差し替え、実HTTP/FTP通信なし） ---


def test_main_fetch_stage_dispatches_and_formats_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator(fetch_and_stage_result=PdfId(42))
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "fetch-stage",
            "https://example.mod.go.jp/x.pdf",
            "/tmp/x.pdf",
            "2026-01-01",
        ]
    )

    assert exit_code == 0
    assert "staged pdf: id=42" in capsys.readouterr().out
    assert len(fake_orchestrator.fetch_and_stage_calls) == 1


def test_main_fetch_stage_reports_duplicate_as_not_staged(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator(fetch_and_stage_result=None)
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "fetch-stage",
            "https://example.mod.go.jp/x.pdf",
            "/tmp/x.pdf",
            "2026-01-01",
        ]
    )

    assert exit_code == 0
    assert "not staged" in capsys.readouterr().out


def test_main_fetch_stage_invalid_date_returns_error(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator()
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "fetch-stage",
            "https://example.mod.go.jp/x.pdf",
            "/tmp/x.pdf",
            "not-a-date",
        ]
    )

    assert exit_code == 1
    assert "error" in capsys.readouterr().out
    assert fake_orchestrator.fetch_and_stage_calls == []


def test_main_run_workflow_dispatches_and_formats_result(
    settings: CompositionSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    fake_orchestrator = _RecordingJobOrchestrator(workflow_result=_default_workflow_result())
    monkeypatch.setattr(commands, "_build_job_orchestrator", lambda _settings: fake_orchestrator)
    destination = str(tmp_path / "export.json")

    exit_code = app.main(
        [
            "--db-path",
            settings.db_path,
            "--knowledge-root",
            str(settings.knowledge_root),
            "--layouts-root",
            str(settings.layouts_root),
            "run-workflow",
            "json",
            destination,
        ]
    )

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "fetched 0 pdf(s)" in out
    assert "export: format=json" in out
    assert len(fake_orchestrator.run_workflow_calls) == 1
    assert fake_orchestrator.run_workflow_calls[0][3] is None


# --- 既存CLI回帰: fetch-stage/run-workflow追加後も既存コマンドが変わらず動作する ---


def test_existing_version_command_unaffected_by_phase7_additions(
    settings: CompositionSettings,
) -> None:
    info = commands.version_command(settings)
    assert info.knowledge_item_count == 0


def test_existing_run_pending_command_unaffected_by_phase7_additions(
    settings: CompositionSettings,
) -> None:
    results = commands.run_pending_command(settings)
    assert results == ()
