"""必要最小限のCLIコマンド。`bootstrap.py`（合成ルート）が構築した`Application`
（`JobRunner`＋読み取り専用アクセス）を呼び出す。

コマンド関数はいずれも`bootstrap.build_application()`/`build_job_runner()`・
`cli.init.initialize_database()`のみに依存し、`repositories/sqlite/`・
`knowledge/`・`learning/`のいずれも直接importしない。引数解析（argparse）
は`app.py`が担当し、本モジュールはコマンドロジックのみを提供する。
"""

from dataclasses import dataclass
from datetime import date

from mod_personnel_db.cli.bootstrap import CompositionSettings, build_application, build_job_runner
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.cli.init import initialize_database
from mod_personnel_db.models import ParserVersion, PdfId
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
    "init_db_command",
    "run_job_command",
    "run_pending_command",
    "version_command",
]
