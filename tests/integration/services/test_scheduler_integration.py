"""`DefaultScheduler`と実装済み`DefaultJobOrchestrator`との結合テスト（Phase7 Task17-3）。

`tests/unit/services/test_scheduler.py`がStub`JobOrchestrator`で呼び出し規約を
検証するのに対し、本テストは実際のSQLiteデータベース・実際の`JobRunner`
（`pipeline/`は一切変更していない）・実際の`DefaultJobOrchestrator`
（`services/orchestrator.py`、Task16-4実装済み）を組み合わせ、`DefaultScheduler`
が`JobOrchestrator`経由で正しく`trigger_now()`/`list_upcoming()`を実行できる
ことを確認する。

`cli.bootstrap.build_application()`/`cli.app.main()`は、
`tests/integration/services/test_orchestrator_integration.py`と同じく、
既に実装済みのComposition Rootをテストのフィクスチャ構築（Arrange）のためだけに
再利用する（`services/scheduler.py`自身の実行時コードが`cli/`に依存するわけでは
ない。`tests/unit/services/test_scheduler.py`のAST検証がこれを保証する）。

中核パイプラインの実行結果自体の正しさはGolden Test（ADR-0007）が別途担保する
ため、本テストはPDF本文の実際の解析結果を検証しない。`trigger_now()`が実際の
`JobRunner`実行を経由して`JobId`を取得できること、および未処理PDFが存在しない
場合に`NoPendingJobError`を送出することのみを確認する。
"""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from mod_personnel_db.cli import app
from mod_personnel_db.cli.bootstrap import CompositionSettings, build_application
from mod_personnel_db.fetch import HTTPFetchClient
from mod_personnel_db.ftp import InMemoryFTPClient
from mod_personnel_db.models import PdfRecord
from mod_personnel_db.repositories.sqlite import SqlitePdfRepository, connect
from mod_personnel_db.services import (
    RUN_PENDING_JOB_TYPE,
    DefaultScheduler,
    JobSchedule,
    NoPendingJobError,
)
from mod_personnel_db.services.orchestrator import DefaultJobOrchestrator, OrchestratorDependencies

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SAMPLE_PDF_PATH = (
    _REPO_ROOT / "tests" / "golden" / "sample_pdfs" / ("2026_format_sample_20260701_synthetic.pdf")
)


@pytest.fixture
def settings(tmp_path: Path) -> CompositionSettings:
    db_path = tmp_path / "mod_personnel.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    layouts_root = tmp_path / "layouts"
    knowledge_root.mkdir()
    layouts_root.mkdir()
    resolved = CompositionSettings(
        db_path=str(db_path),
        knowledge_root=knowledge_root,
        layouts_root=layouts_root,
        parser_code_version="v1.0.0",
    )
    exit_code = app.main(
        [
            "--db-path",
            resolved.db_path,
            "--knowledge-root",
            str(resolved.knowledge_root),
            "--layouts-root",
            str(resolved.layouts_root),
            "--parser-code-version",
            resolved.parser_code_version,
            "init-db",
        ]
    )
    assert exit_code == 0
    return resolved


@pytest.fixture
def pdf_repository(settings: CompositionSettings) -> Iterator[SqlitePdfRepository]:
    connection = connect(settings.db_path)
    try:
        yield SqlitePdfRepository(connection)
    finally:
        connection.close()


@pytest.fixture
def job_orchestrator(
    settings: CompositionSettings, pdf_repository: SqlitePdfRepository
) -> DefaultJobOrchestrator:
    application = build_application(settings)
    return DefaultJobOrchestrator(
        OrchestratorDependencies(
            fetch_client=HTTPFetchClient(),
            ftp_client=InMemoryFTPClient(),
            pdf_repository=pdf_repository,
            job_runner=application.job_runner,
            review_service=application.review_service,
            export_service=application.export_service,
        )
    )


def test_trigger_now_raises_no_pending_job_error_with_real_empty_database(
    job_orchestrator: DefaultJobOrchestrator,
) -> None:
    scheduler = DefaultScheduler(job_orchestrator, (), lambda: datetime(2026, 1, 1, tzinfo=UTC))

    with pytest.raises(NoPendingJobError):
        scheduler.trigger_now(RUN_PENDING_JOB_TYPE)


def test_trigger_now_processes_real_pending_pdf_via_real_job_runner(
    job_orchestrator: DefaultJobOrchestrator,
    pdf_repository: SqlitePdfRepository,
) -> None:
    # Layout Detector（`layout/detector.py`）はpypdfで実際にPDFバイト列を解析
    # するため、構文的に有効なPDFが必要である（Golden Testの合成PDFフィクスチャ
    # を読み取り専用で再利用する。中核パイプラインの解析結果自体の正しさは
    # `tests/integration/golden/test_golden.py`が別途担保する）。
    pdf_repository.add(
        PdfRecord(
            id=None,
            content_hash="b" * 64,
            source_url="https://example.mod.go.jp/order.pdf",
            published_date=date(2026, 1, 1),
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            file_path=str(_SAMPLE_PDF_PATH),
            file_size_bytes=_SAMPLE_PDF_PATH.stat().st_size,
            status="fetched",
        )
    )
    scheduler = DefaultScheduler(job_orchestrator, (), lambda: datetime(2026, 1, 1, tzinfo=UTC))

    job_id = scheduler.trigger_now(RUN_PENDING_JOB_TYPE)

    assert int(job_id) > 0


def test_list_upcoming_reflects_registered_schedules_via_injected_clock(
    job_orchestrator: DefaultJobOrchestrator,
) -> None:
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(
        job_type=RUN_PENDING_JOB_TYPE, interval=timedelta(hours=6), anchor=anchor
    )
    fixed_now = anchor + timedelta(hours=7)
    scheduler = DefaultScheduler(job_orchestrator, (schedule,), lambda: fixed_now)

    upcoming = scheduler.list_upcoming()

    assert upcoming == (f"{RUN_PENDING_JOB_TYPE} at 2026-01-01T12:00:00+00:00",)
