"""必要最小限のCLIコマンド。`bootstrap.py`（合成ルート）が構築した`Application`
（`JobRunner`・`ReviewService`・`ExportService`＋読み取り専用アクセス）を
呼び出す。

コマンド関数はいずれも`bootstrap.build_application()`/`build_job_runner()`・
`cli.init.initialize_database()`のみに依存し、`knowledge/`・`learning/`・
`review/`・`export/`のいずれも直接importしない（`review_*_command`/
`export_*_command`は`Application.review_service`/`Application.export_service`
という、すでに生成済みのオブジェクトのメソッドを呼ぶのみで、
`RepositoryReviewService`/`RepositoryExportService`を自ら生成・importしない）。
引数解析（argparse）は`app.py`が担当し、本モジュールはコマンドロジックのみを
提供する。`repositories/sqlite/`からの直接importは、下記Phase7統合の節が
説明する`connect()`のみの例外を除き行わない。

**Phase7統合（Task17-2）**: `fetch_stage_command`/`run_workflow_command`は
`bootstrap.build_job_orchestrator()`（Task17-1で追加）が返す`JobOrchestrator`
をProtocol型としてのみ呼び出す。`HTTPFetchClient`・`StandardFTPClient`・
`DefaultJobOrchestrator`等の具象実装は、`bootstrap.build_fetch_client()`/
`build_ftp_client()`/`build_job_orchestrator()`経由でのみ取得し、本モジュール
が直接インスタンス化することはない（Composition Root一本化、
architecture-contract.md 保証15）。

`_build_job_orchestrator()`は、`build_job_orchestrator()`が要求する
`SqliteRepositories`（Task17-1の既存シグネチャ、本Taskでは変更不可）を
`bootstrap.build_sqlite_repositories()`経由で組み立てるために、
`repositories.sqlite.connect()`のみを直接importする（他の具象Repository
クラスは一切importしない）。`connect()`は`bootstrap.py`の`__all__`に
含まれず`mypy --strict`のno-implicit-reexport制約で参照できないため、この
1関数のみ`repositories.sqlite`から直接importする。本モジュールの他のいかなる
箇所もRepository具象クラス・`sqlite3`を直接扱わない。

**Phase7統合Step4（Task17-4）**: `schedule_now_command`/`list_schedule_command`は
`bootstrap.build_scheduler()`（Task17-4で追加）が返す`Scheduler`をProtocol型
としてのみ呼び出す。`DefaultScheduler`は本モジュールが直接生成せず、
`bootstrap.build_scheduler()`経由でのみ取得する。両コマンドとも
`JobOrchestrator`を直接呼び出すことはない（`Scheduler`経由のみ）。
`FeatureStore`（`build_feature_store()`）は引き続き呼び出さない（`JobRunner`
への配線が未実装のため、Task17-1と同様に未使用のまま据え置く）。
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from mod_personnel_db.cli.bootstrap import (
    CompositionSettings,
    build_application,
    build_fetch_client,
    build_ftp_client,
    build_job_orchestrator,
    build_job_runner,
    build_scheduler,
    build_sqlite_repositories,
)
from mod_personnel_db.cli.exceptions import CliCommandError
from mod_personnel_db.cli.init import initialize_database
from mod_personnel_db.fetch import FetchRequest
from mod_personnel_db.models import (
    ExportFormat,
    GoldRecord,
    JobId,
    LearningRecord,
    LearningRecordId,
    ParserVersion,
    PdfId,
)
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.repositories.sqlite import connect
from mod_personnel_db.services import JobOrchestrator, Scheduler, WorkflowResult


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


def _build_job_orchestrator(settings: CompositionSettings) -> JobOrchestrator:
    """`fetch-stage`/`run-workflow`コマンド用に`JobOrchestrator`を取得する。

    `cli/bootstrap.py`（Composition Root、Task17-1）が提供するBuilder
    （`build_application`/`build_sqlite_repositories`/`build_fetch_client`/
    `build_ftp_client`/`build_job_orchestrator`）のみを呼び出して依存を組み立て、
    `HTTPFetchClient`・`StandardFTPClient`・`DefaultJobOrchestrator`等の
    具象実装を本モジュールが直接生成することはない。戻り値の型は`JobOrchestrator`
    Protocolであり、呼び出し元（`fetch_stage_command`/`run_workflow_command`）は
    Protocol経由でのみこれを利用する。
    """
    application = build_application(settings)
    connection = connect(settings.db_path)
    repositories = build_sqlite_repositories(connection)
    fetch_client = build_fetch_client()
    ftp_client = build_ftp_client(settings)
    return build_job_orchestrator(application, repositories, fetch_client, ftp_client)


def fetch_stage_command(
    settings: CompositionSettings, url: str, destination_path: str, published_date: date
) -> PdfId | None:
    """`fetch-stage`コマンド。`JobOrchestrator.fetch_and_stage()`を呼び出す。

    戻り値`None`は、取得した内容の`content_hash`が既存の`PdfRecord`と重複した
    ため保存しなかったことを意味する（`fetch_and_stage()`自身の既存契約）。
    """
    orchestrator = _build_job_orchestrator(settings)
    return orchestrator.fetch_and_stage(
        FetchRequest(url=url), destination_path=destination_path, published_date=published_date
    )


def run_workflow_command(
    settings: CompositionSettings,
    export_format: ExportFormat,
    export_destination: str,
    *,
    remote_path: str | None = None,
) -> WorkflowResult:
    """`run-workflow`コマンド。`JobOrchestrator.run_workflow()`を呼び出す。

    現時点ではCLI引数からのFetch対象一覧指定に対応しないため、`fetch_items`は
    常に空タプルである（個別のPDF取得は`fetch-stage`コマンドで行う）。
    `remote_path`を指定した場合のみ、生成したエクスポートをFTPでアップロード
    する（`JobOrchestrator.export_and_publish()`の既存契約）。
    """
    orchestrator = _build_job_orchestrator(settings)
    return orchestrator.run_workflow([], export_format, export_destination, remote_path=remote_path)


def _build_scheduler(settings: CompositionSettings) -> Scheduler:
    """`schedule-now`/`list-schedule`コマンド用に`Scheduler`を取得する。

    `_build_job_orchestrator()`が返す`JobOrchestrator`を`bootstrap.build_scheduler()`
    へ渡すのみであり、本モジュールが`DefaultScheduler`等の具象実装を直接生成する
    ことはない。周期実行対象（`JobSchedule`）はCLIからはまだ設定できないため
    空タプルとする（`list-schedule`は現時点で常に空を返す。`schedule-now`は
    登録済みの周期定義に依存せず動作するため影響を受けない）。現在時刻は
    `datetime.now(UTC)`をそのまま`clock`として注入する。
    """
    orchestrator = _build_job_orchestrator(settings)
    return build_scheduler(orchestrator, (), lambda: datetime.now(UTC))


def schedule_now_command(settings: CompositionSettings, job_type: str) -> JobId:
    """`schedule-now`コマンド。`Scheduler.trigger_now()`のみを呼び出す
    （`JobOrchestrator`を直接呼び出すことはない）。
    """
    scheduler = _build_scheduler(settings)
    return scheduler.trigger_now(job_type)


def list_schedule_command(settings: CompositionSettings) -> tuple[str, ...]:
    """`list-schedule`コマンド。`Scheduler.list_upcoming()`のみを呼び出す
    （`JobOrchestrator`を直接呼び出すことはない）。
    """
    scheduler = _build_scheduler(settings)
    return scheduler.list_upcoming()


__all__ = [
    "VersionInfo",
    "export_all_command",
    "export_person_command",
    "export_since_command",
    "fetch_stage_command",
    "init_db_command",
    "list_schedule_command",
    "review_approve_command",
    "review_list_command",
    "review_reject_command",
    "review_start_command",
    "run_job_command",
    "run_pending_command",
    "run_workflow_command",
    "schedule_now_command",
    "version_command",
]
