"""Phase7統合Step4（Task17-4）の結合テスト。

`app.main([...])`（CLI公開API、実際のargparse解析込み）を起点に、
`cli/commands.py`の`schedule-now`/`list-schedule`コマンドが`cli/bootstrap.py`
（Composition Root）経由で実際の`Scheduler`（`DefaultScheduler`）・
`JobOrchestrator`（`DefaultJobOrchestrator`）・実SQLiteデータベースまで到達する
ことを確認する。`tests/integration/services/test_scheduler_integration.py`と
同じく、パイプライン実解析結果の正しさはGolden Test（ADR-0007）が別途担保する
ため、本テストは`trigger_now()`がCLI経由で`JobId`を取得できること、
未処理PDFが存在しない場合に`NoPendingJobError`が伝播すること、
`list-schedule`が現時点では常に「0件」を表示すること（CLIから周期定義を
まだ設定できないため、`_build_scheduler()`が空タプルを渡す既存契約）のみを
確認する。
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mod_personnel_db.cli import app
from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.models import PdfRecord
from mod_personnel_db.repositories.sqlite import SqlitePdfRepository, connect
from mod_personnel_db.services import RUN_PENDING_JOB_TYPE, NoPendingJobError

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SAMPLE_PDF_PATH = (
    _REPO_ROOT / "tests" / "golden" / "sample_pdfs" / ("2026_format_sample_20260701_synthetic.pdf")
)


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


def test_schedule_now_raises_no_pending_job_error_via_real_empty_database(
    initialized_settings: CompositionSettings,
) -> None:
    with pytest.raises(NoPendingJobError):
        app.main([*_base_argv(initialized_settings), "schedule-now", RUN_PENDING_JOB_TYPE])


def test_schedule_now_processes_real_pending_pdf_via_bootstrap(
    initialized_settings: CompositionSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    connection = connect(initialized_settings.db_path)
    try:
        SqlitePdfRepository(connection).add(
            PdfRecord(
                id=None,
                content_hash="c" * 64,
                source_url="https://example.mod.go.jp/order.pdf",
                published_date=date(2026, 1, 1),
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
                file_path=str(_SAMPLE_PDF_PATH),
                file_size_bytes=_SAMPLE_PDF_PATH.stat().st_size,
                status="fetched",
            )
        )
    finally:
        connection.close()

    exit_code = app.main([*_base_argv(initialized_settings), "schedule-now", RUN_PENDING_JOB_TYPE])

    assert exit_code == 0
    assert "triggered job: id=" in capsys.readouterr().out


def test_list_schedule_reports_zero_upcoming_via_bootstrap(
    initialized_settings: CompositionSettings,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLIからは周期定義をまだ設定できないため（`_build_scheduler()`が空タプルを
    渡す既存契約）、`list-schedule`は常に0件を表示する。
    """
    exit_code = app.main([*_base_argv(initialized_settings), "list-schedule"])

    assert exit_code == 0
    assert "0 upcoming schedule(s)" in capsys.readouterr().out


def test_existing_run_workflow_command_unaffected_by_scheduler_additions(
    initialized_settings: CompositionSettings,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    destination = str(tmp_path / "export.json")

    exit_code = app.main([*_base_argv(initialized_settings), "run-workflow", "json", destination])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "fetched 0 pdf(s)" in out
    assert "export: format=json" in out
