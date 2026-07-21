"""必要最小限のCLIコマンド。`bootstrap.py`（合成ルート）が構築した`Application`
（`JobRunner`・`ReviewService`・`ExportService`＋読み取り専用アクセス）を
呼び出す。

コマンド関数はいずれも`bootstrap.build_application()`/`build_job_runner()`・
`cli.init.initialize_database()`のみに依存し、`repositories/sqlite/`・
`knowledge/`・`learning/`・`review/`・`export/`のいずれも直接importしない
（`review_*_command`/`export_*_command`は`Application.review_service`/
`Application.export_service`という、すでに生成済みのオブジェクトのメソッド
を呼ぶのみで、`RepositoryReviewService`/`RepositoryExportService`を自ら
生成・importしない）。引数解析（argparse）は`app.py`が担当し、本モジュール
はコマンドロジックのみを提供する。
"""

from dataclasses import dataclass
from datetime import date, datetime

from mod_personnel_db.cli.bootstrap import (
    CompositionSettings,
    build_application,
    build_job_runner,
)
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.cli.init import initialize_database
from mod_personnel_db.models import (
    GoldRecord,
    LearningRecord,
    LearningRecordId,
    ParserVersion,
    PdfId,
)
from mod_personnel_db.pipeline.result import PipelineResult


def init_db_command(settings: CompositionSettings) -> None:
    """`init-db`コマンド。DBスキーマを`apply_schema()`で一度だけ適用する。"""
    initialize_database(settings.db_path)


def run_pending_command(settings: CompositionSettings) -> tuple[PipelineResult, ...]:
    """`run-pending`コマンド。`JobRunner.run_pending()`を呼び出す。"""
    job_runner = build_job_runner(settings)
    return job_runner.run_pending()


def run_job_command(settings: CompositionSettings, pdf_id: PdfId) -> PipelineResult:
    """`run-job`コマンド。`pdf_id`を解決し`JobRunner.run_for_pdf()`を呼び出す。"""
    application = build_application(settings)
    pdf = application.read_pdf(pdf_id)
    if pdf is None:
        raise CliCommandError(f"pdf not found: pdf_id={int(pdf_id)}")
    return application.job_runner.run_for_pdf(pdf)


def review_list_command(settings: CompositionSettings) -> tuple[LearningRecord, ...]:
    """`review list`コマンド。`ReviewService.list_pending()`を呼び出す。"""
    application = build_application(settings)
    return application.review_service.list_pending()


def review_start_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review start`コマンド。`ReviewService.start_review()`を呼び出す。"""
    application = build_application(settings)
    return application.review_service.start_review(record_id)


def review_approve_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review approve`コマンド。`ReviewService.approve()`を呼び出す
    （GoldPromotion指定は対象外）。
    """
    application = build_application(settings)
    return application.review_service.approve(record_id)


def review_reject_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review reject`コマンド。`ReviewService.reject()`を呼び出す。"""
    application = build_application(settings)
    return application.review_service.reject(record_id)


def export_all_command(settings: CompositionSettings) -> tuple[GoldRecord, ...]:
    """`export all`コマンド。`ExportService.export_all()`を呼び出す。"""
    application = build_application(settings)
    return application.export_service.export_all()


def export_person_command(settings: CompositionSettings, person_key: str) -> tuple[GoldRecord, ...]:
    """`export person`コマンド。`ExportService.export_person()`を呼び出す。"""
    application = build_application(settings)
    return application.export_service.export_person(person_key)


def export_since_command(settings: CompositionSettings, since: datetime) -> tuple[GoldRecord, ...]:
    """`export since`コマンド。`ExportService.export_since()`を呼び出す。"""
    application = build_application(settings)
    return application.export_service.export_since(since)


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """`version`コマンドの表示内容。"""

    parser_version: ParserVersion | None
    knowledge_snapshot_checksum: str
    knowledge_item_count: int
    knowledge_as_of: date


def version_command(settings: CompositionSettings) -> VersionInfo:
    """`version`コマンド。最新`ParserVersion`と`KnowledgeSnapshot`の要約を返す。"""
    application = build_application(settings)
    snapshot = application.read_knowledge_snapshot()
    return VersionInfo(
        parser_version=application.read_latest_parser_version(),
        knowledge_snapshot_checksum=snapshot.snapshot_checksum,
        knowledge_item_count=len(snapshot.items),
        knowledge_as_of=snapshot.as_of,
    )


__all__ = [
    "VersionInfo",
    "export_all_command",
    "export_person_command",
    "export_since_command",
    "init_db_command",
    "review_approve_command",
    "review_list_command",
    "review_reject_command",
    "review_start_command",
    "run_job_command",
    "run_pending_command",
    "version_command",
]
