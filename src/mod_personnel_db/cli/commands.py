"""必要最小限のCLIコマンド。`bootstrap.py`（合成ルート）が構築した`Application`
（`JobRunner`・`ReviewService`・`ExportService`＋読み取り専用アクセス）を
呼び出す。

コマンド関数はいずれも`bootstrap.build_application()`（`version_command`のみ
`bootstrap.build_version_dependencies()`、Task22-3）・
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
1関数のみ`repositories.sqlite`から直接importする。

**Task19-5**: `upload_db_command()`実行前のDB健全性検証（`_check_database_integrity()`）
でも、新規のRepository・サービス層を追加せず、この既存`connect()`importを
再利用する（`PRAGMA integrity_check`実行後に`close()`する接続1本のみの
軽量な検証であり、Task19-4のADR判断（新規サービス層は見送り）を踏まえた
最小実装）。同関数は`sqlite3.Error`を捕捉するためにのみ`sqlite3`モジュール
自体もimportするが、Repository具象クラスは引き続き一切importしない。

**Phase7統合Step4（Task17-4）**: `schedule_now_command`/`list_schedule_command`は
`bootstrap.build_scheduler()`（Task17-4で追加）が返す`Scheduler`をProtocol型
としてのみ呼び出す。`DefaultScheduler`は本モジュールが直接生成せず、
`bootstrap.build_scheduler()`経由でのみ取得する。両コマンドとも
`JobOrchestrator`を直接呼び出すことはない（`Scheduler`経由のみ）。
`FeatureStore`（`build_feature_store()`）は引き続き呼び出さない（`JobRunner`
への配線が未実装のため、Task17-1と同様に未使用のまま据え置く）。

**Task21-4**: Connectionのclose責務をCLIコマンド層（本モジュール）に一本化する
（Task21-3で選定した案B）。`run_pending_command`/`run_job_command`/
`review_*_command`/`export_*_command`は、`connect()`で生成したConnectionを
`try/finally`で必ず`close()`する（正常終了・例外終了のいずれでも）。
`fetch_stage_command`/`run_workflow_command`/`schedule_now_command`/
`list_schedule_command`は、`_build_job_orchestrator()`/`_build_scheduler()`が
Task21-2で共有した単一Connectionを戻り値の一部として受け取り、同様に
`try/finally`で1回だけ`close()`する（二重closeはしない）。Repository層・
`bootstrap.py`・Service層にはclose責務を追加しない。`version_command`は
Task21-4の対象コマンド一覧に含まれていなかったが、Task22-1で他コマンドと
同一パターンへ統一し、close漏れを解消した。

**Task22-3**: `version_command`は`build_application()`ではなく、`version`
専用の軽量Builder`bootstrap.build_version_dependencies()`を使う（Task22-2で
設計）。`ReviewService`/`ExportService`/`JobRunner`/`CandidateRepository`の
生成、および`parser_versions`への書き込み副作用（`_resolve_parser_version_id()`）
のいずれも発生しない。
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from mod_personnel_db.cli.bootstrap import (
    CompositionSettings,
    build_application,
    build_fetch_client,
    build_ftp_client,
    build_job_orchestrator,
    build_scheduler,
    build_sqlite_repositories,
    build_version_dependencies,
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
    """`run-pending`コマンド。`JobRunner.run_pending()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.job_runner.run_pending()
    finally:
        connection.close()


def run_job_command(settings: CompositionSettings, pdf_id: PdfId) -> PipelineResult:
    """`run-job`コマンド。`pdf_id`を解決し`JobRunner.run_for_pdf()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        pdf = application.read_pdf(pdf_id)
        if pdf is None:
            raise CliCommandError(f"pdf not found: pdf_id={int(pdf_id)}")
        return application.job_runner.run_for_pdf(pdf)
    finally:
        connection.close()


def review_list_command(settings: CompositionSettings) -> tuple[LearningRecord, ...]:
    """`review list`コマンド。`ReviewService.list_pending()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.review_service.list_pending()
    finally:
        connection.close()


def review_start_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review start`コマンド。`ReviewService.start_review()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.review_service.start_review(record_id)
    finally:
        connection.close()


def review_approve_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review approve`コマンド。`ReviewService.approve()`を呼び出す
    （GoldPromotion指定は対象外）。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.review_service.approve(record_id)
    finally:
        connection.close()


def review_reject_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review reject`コマンド。`ReviewService.reject()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.review_service.reject(record_id)
    finally:
        connection.close()


def export_all_command(settings: CompositionSettings) -> tuple[GoldRecord, ...]:
    """`export all`コマンド。`ExportService.export_all()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.export_service.export_all()
    finally:
        connection.close()


def export_person_command(settings: CompositionSettings, person_key: str) -> tuple[GoldRecord, ...]:
    """`export person`コマンド。`ExportService.export_person()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.export_service.export_person(person_key)
    finally:
        connection.close()


def export_since_command(settings: CompositionSettings, since: datetime) -> tuple[GoldRecord, ...]:
    """`export since`コマンド。`ExportService.export_since()`を呼び出す。

    Task21-4: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    """
    connection = connect(settings.db_path)
    try:
        application = build_application(settings, connection)
        return application.export_service.export_since(since)
    finally:
        connection.close()


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """`version`コマンドの表示内容。"""

    parser_version: ParserVersion | None
    knowledge_snapshot_checksum: str
    knowledge_item_count: int
    knowledge_as_of: date


def version_command(settings: CompositionSettings) -> VersionInfo:
    """`version`コマンド。最新`ParserVersion`と`KnowledgeSnapshot`の要約を返す。

    Task22-1: `connect()`で生成したConnectionを`try/finally`で必ず`close()`する。
    Task22-3: `build_application()`は使わず、`version`専用の軽量Builder
    （`build_version_dependencies()`）のみを使う。`ReviewService`/`ExportService`/
    `JobRunner`/`CandidateRepository`の生成、および`parser_versions`への
    書き込み副作用（`_resolve_parser_version_id()`）のいずれも発生しない。
    """
    connection = connect(settings.db_path)
    try:
        dependencies = build_version_dependencies(settings, connection)
        snapshot = dependencies.read_knowledge_snapshot()
        return VersionInfo(
            parser_version=dependencies.read_latest_parser_version(),
            knowledge_snapshot_checksum=snapshot.snapshot_checksum,
            knowledge_item_count=len(snapshot.items),
            knowledge_as_of=snapshot.as_of,
        )
    finally:
        connection.close()


def _build_job_orchestrator(
    settings: CompositionSettings,
) -> tuple[JobOrchestrator, sqlite3.Connection]:
    """`fetch-stage`/`run-workflow`コマンド用に`JobOrchestrator`を取得する。

    `cli/bootstrap.py`（Composition Root、Task17-1）が提供するBuilder
    （`build_application`/`build_sqlite_repositories`/`build_fetch_client`/
    `build_ftp_client`/`build_job_orchestrator`）のみを呼び出して依存を組み立て、
    `HTTPFetchClient`・`StandardFTPClient`・`DefaultJobOrchestrator`等の
    具象実装を本モジュールが直接生成することはない。戻り値の型は`JobOrchestrator`
    Protocolであり、呼び出し元（`fetch_stage_command`/`run_workflow_command`）は
    Protocol経由でのみこれを利用する。

    **Task21-2**: `connect()`は本関数内で1回のみ呼び出し、`build_application()`
    （Application生成）と`build_sqlite_repositories()`（JobOrchestrator用の
    Repository生成）の両方へ同一Connectionを渡す（Task21-1で選定した案B）。
    以前は`build_application()`が内部で独自に`connect()`していたため、同一
    `db_path`への接続が1回のコマンド実行あたり2本生成されていた（Task20-2で
    判明）。Repository自体は従来どおり`build_sqlite_repositories()`で
    Application用・JobOrchestrator用にそれぞれ生成する（Repository生成構造は
    変更しない）。

    **Task21-4**: 生成したConnectionは本関数ではcloseせず、戻り値
    （`tuple[JobOrchestrator, sqlite3.Connection]`）に含めて呼び出し元へ返す。
    close責務は呼び出し元のコマンド関数が`try/finally`で持つ（Task21-3で
    選定した案B）。
    """
    connection = connect(settings.db_path)
    application = build_application(settings, connection)
    repositories = build_sqlite_repositories(connection)
    fetch_client = build_fetch_client()
    ftp_client = build_ftp_client(settings)
    orchestrator = build_job_orchestrator(application, repositories, fetch_client, ftp_client)
    return orchestrator, connection


def fetch_stage_command(
    settings: CompositionSettings, url: str, destination_path: str, published_date: date
) -> PdfId | None:
    """`fetch-stage`コマンド。`JobOrchestrator.fetch_and_stage()`を呼び出す。

    戻り値`None`は、取得した内容の`content_hash`が既存の`PdfRecord`と重複した
    ため保存しなかったことを意味する（`fetch_and_stage()`自身の既存契約）。
    Task21-4: `_build_job_orchestrator()`が返すConnectionを`try/finally`で
    必ず`close()`する。
    """
    orchestrator, connection = _build_job_orchestrator(settings)
    try:
        return orchestrator.fetch_and_stage(
            FetchRequest(url=url), destination_path=destination_path, published_date=published_date
        )
    finally:
        connection.close()


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
    Task21-4: `_build_job_orchestrator()`が返すConnectionを`try/finally`で
    必ず`close()`する。
    """
    orchestrator, connection = _build_job_orchestrator(settings)
    try:
        return orchestrator.run_workflow(
            [], export_format, export_destination, remote_path=remote_path
        )
    finally:
        connection.close()


def _build_scheduler(settings: CompositionSettings) -> tuple[Scheduler, sqlite3.Connection]:
    """`schedule-now`/`list-schedule`コマンド用に`Scheduler`を取得する。

    `_build_job_orchestrator()`が返す`JobOrchestrator`を`bootstrap.build_scheduler()`
    へ渡すのみであり、本モジュールが`DefaultScheduler`等の具象実装を直接生成する
    ことはない。周期実行対象（`JobSchedule`）はCLIからはまだ設定できないため
    空タプルとする（`list-schedule`は現時点で常に空を返す。`schedule-now`は
    登録済みの周期定義に依存せず動作するため影響を受けない）。現在時刻は
    `datetime.now(UTC)`をそのまま`clock`として注入する。

    **Task21-4**: `_build_job_orchestrator()`が返すConnectionをそのまま呼び出し元へ
    引き継ぐ（`tuple[Scheduler, sqlite3.Connection]`）。本関数自身はcloseしない。
    """
    orchestrator, connection = _build_job_orchestrator(settings)
    scheduler = build_scheduler(orchestrator, (), lambda: datetime.now(UTC))
    return scheduler, connection


def schedule_now_command(settings: CompositionSettings, job_type: str) -> JobId:
    """`schedule-now`コマンド。`Scheduler.trigger_now()`のみを呼び出す
    （`JobOrchestrator`を直接呼び出すことはない）。
    Task21-4: `_build_scheduler()`が返すConnectionを`try/finally`で必ず`close()`する。
    """
    scheduler, connection = _build_scheduler(settings)
    try:
        return scheduler.trigger_now(job_type)
    finally:
        connection.close()


def list_schedule_command(settings: CompositionSettings) -> tuple[str, ...]:
    """`list-schedule`コマンド。`Scheduler.list_upcoming()`のみを呼び出す
    （`JobOrchestrator`を直接呼び出すことはない）。
    Task21-4: `_build_scheduler()`が返すConnectionを`try/finally`で必ず`close()`する。
    """
    scheduler, connection = _build_scheduler(settings)
    try:
        return scheduler.list_upcoming()
    finally:
        connection.close()


def download_db_command(settings: CompositionSettings, remote_path: str) -> None:
    """`download-db`コマンド。`FTPClient.download()`のみを呼び出し、
    `remote_path`のDBファイルを`settings.db_path`へ取得する（Task18-17）。
    `bootstrap.build_ftp_client()`が返す`FTPClient`をProtocol経由でのみ
    利用し、`StandardFTPClient`等の具象実装は本モジュールが直接生成しない。
    """
    ftp_client = build_ftp_client(settings)
    ftp_client.connect()
    try:
        ftp_client.download(remote_path, settings.db_path)
    finally:
        ftp_client.disconnect()


def _check_database_integrity(db_path: str) -> None:
    """`db_path`のSQLiteファイルへ`PRAGMA integrity_check`を実行する（Task19-5）。

    破損したDBファイルがそのままFTPサーバへ書き戻される事故を防ぐための
    軽量な検証であり、専用サービス層は設けない（Task19-4のADR判断を踏まえた
    最小実装）。異常時（ファイル不在・SQLiteとして開けない・`integrity_check`が
    `ok`以外を返す場合）は`CliCommandError`を送出し、呼び出し元はFTP通信を
    行わない。
    """
    if not Path(db_path).exists():
        raise CliCommandError(f"DBファイルが存在しません: {db_path}")
    connection = connect(db_path)
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise CliCommandError(f"DB健全性検証に失敗しました: {db_path} ({exc})") from exc
    finally:
        connection.close()
    result = row[0] if row is not None else None
    if result != "ok":
        raise CliCommandError(f"DB健全性検証に失敗しました: {db_path} (結果: {result})")


def upload_db_command(settings: CompositionSettings, remote_path: str) -> None:
    """`upload-db`コマンド。`FTPClient.upload()`のみを呼び出し、
    `settings.db_path`のDBファイルを`remote_path`へ書き戻す（Task18-17）。
    アップロード前に`_check_database_integrity()`でDBの健全性を確認し、
    異常があればFTP通信を一切行わずに中断する（Task19-5）。
    """
    _check_database_integrity(settings.db_path)
    ftp_client = build_ftp_client(settings)
    ftp_client.connect()
    try:
        ftp_client.upload(settings.db_path, remote_path)
    finally:
        ftp_client.disconnect()


__all__ = [
    "VersionInfo",
    "download_db_command",
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
    "upload_db_command",
    "version_command",
]
