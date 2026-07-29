"""必要最小限のCLIコマンド。`bootstrap.py`（合成ルート）が構築した`Application`
（`JobRunner`・`ReviewService`・`ExportService`＋読み取り専用アクセス）を
呼び出す。

コマンド関数はいずれも`bootstrap.application_session()`（`version_command`のみ
`bootstrap.version_dependencies_session()`、Task22-8）・
`cli.init.initialize_database()`のみに依存し、`knowledge/`・`learning/`・
`review/`・`export/`のいずれも直接importしない（`review_*_command`/
`export_*_command`は`Application.review_service`/`Application.export_service`
という、すでに生成済みのオブジェクトのメソッドを呼ぶのみで、
`RepositoryReviewService`/`RepositoryExportService`を自ら生成・importしない）。
引数解析（argparse）は`app.py`が担当し、本モジュールはコマンドロジックのみを
提供する。`repositories/sqlite/`からの直接importは、下記Task19-5の節が
説明する`connect()`のみの例外を除き行わない。

**Phase7統合（Task17-2）**: `fetch_stage_command`/`run_workflow_command`は
`bootstrap.job_orchestrator_session()`（Task22-8、Task17-1で追加した
`build_job_orchestrator()`をSession化）が`with`文でyieldする`JobOrchestrator`
をProtocol型としてのみ呼び出す。`HTTPFetchClient`・`StandardFTPClient`・
`DefaultJobOrchestrator`等の具象実装は、`bootstrap.build_fetch_client()`/
`build_ftp_client()`/`build_job_orchestrator()`経由でのみ取得し、本モジュール
が直接インスタンス化することはない（Composition Root一本化、
architecture-contract.md 保証15）。

**Task19-5**: `upload_db_command()`実行前のDB健全性検証（`_check_database_integrity()`）
は、`bootstrap.py`のSession Builder群（Task22-8）の対象外とする例外として、
引き続き`repositories.sqlite.connect()`を本モジュールから直接importし、
`PRAGMA integrity_check`実行後に`close()`する接続1本のみの軽量な検証を行う
（Task19-4のADR判断「新規サービス層は見送り」を踏まえた最小実装、Task22-7
設計レビューでも現状維持と判断した）。同関数は`sqlite3.Error`を捕捉するため
にのみ`sqlite3`モジュール自体もimportするが、Repository具象クラスは引き続き
一切importしない。`connect()`は`bootstrap.py`の`__all__`に含まれず
`mypy --strict`のno-implicit-reexport制約で参照できないため、この1関数のみ
`repositories.sqlite`から直接importする。

**Phase7統合Step4（Task17-4）**: `schedule_now_command`/`list_schedule_command`は
`bootstrap.scheduler_session()`（Task22-8、Task17-4で追加した
`build_scheduler()`をSession化）が`with`文でyieldする`Scheduler`をProtocol型
としてのみ呼び出す。`DefaultScheduler`は本モジュールが直接生成せず、
`bootstrap.scheduler_session()`経由でのみ取得する。両コマンドとも
`JobOrchestrator`を直接呼び出すことはない（`Scheduler`経由のみ）。
`FeatureStore`（`build_feature_store()`）は引き続き呼び出さない（`JobRunner`
への配線が未実装のため、Task17-1と同様に未使用のまま据え置く）。

**Task22-8**: Connection生成・close責務をComposition Root（`bootstrap.py`）へ
完全集約した（Task22-7設計レビューで選定した案A、Context Manager方式）。
`bootstrap.py`が提供する4つのSession Builder（`application_session()`/
`job_orchestrator_session()`/`scheduler_session()`/
`version_dependencies_session()`）はいずれも内部で`connect()`→`build_xxx()`→
`yield`→`finally: connection.close()`を実行するため、本モジュールは
`with bootstrap.xxx_session(settings) as yyy:`の形でのみ依存を取得し、
`sqlite3.Connection`型・`repositories.sqlite.connect()`を一切扱わない
（`_check_database_integrity()`のみ上記Task19-5の例外として`connect()`を
直接使う）。旧`_build_job_orchestrator()`/`_build_scheduler()`が返していた
`tuple[JobOrchestrator, sqlite3.Connection]`/`tuple[Scheduler,
sqlite3.Connection]`（Task21-1〜21-4で導入）は本Taskで廃止した。Task21-3で
選定した「close責務をコマンド層のtry/finallyに置く案B」は、Session Builder
自身（Context Manager）がclose責務を持つ設計（Composition Rootへの完全集約）
に置き換えられた。`build_application()`・`build_application_with_repositories()`・
`build_job_orchestrator()`・`build_scheduler()`・`build_version_dependencies()`
自体はSession Builder内部・既存テストから引き続き利用されるため`bootstrap.py`
から削除していない。

**Task22-3**: `version_command`は`build_application()`ではなく、`version`
専用の軽量Builder`bootstrap.build_version_dependencies()`（Task22-8以降は
`version_dependencies_session()`経由）を使う（Task22-2で設計）。
`ReviewService`/`ExportService`/`JobRunner`/`CandidateRepository`の生成、
および`parser_versions`への書き込み副作用（`_resolve_parser_version_id()`）
のいずれも発生しない。
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from mod_personnel_db.cli.bootstrap import (
    CompositionSettings,
    application_session,
    build_ftp_client,
    job_orchestrator_session,
    scheduler_session,
    version_dependencies_session,
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
from mod_personnel_db.services import WorkflowResult


def init_db_command(settings: CompositionSettings) -> None:
    """`init-db`コマンド。DBスキーマを`apply_schema()`で一度だけ適用する。"""
    initialize_database(settings.db_path)


def run_pending_command(settings: CompositionSettings) -> tuple[PipelineResult, ...]:
    """`run-pending`コマンド。`JobRunner.run_pending()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.job_runner.run_pending()


def run_job_command(settings: CompositionSettings, pdf_id: PdfId) -> PipelineResult:
    """`run-job`コマンド。`pdf_id`を解決し`JobRunner.run_for_pdf()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        pdf = application.read_pdf(pdf_id)
        if pdf is None:
            raise CliCommandError(f"pdf not found: pdf_id={int(pdf_id)}")
        return application.job_runner.run_for_pdf(pdf)


def review_list_command(settings: CompositionSettings) -> tuple[LearningRecord, ...]:
    """`review list`コマンド。`ReviewService.list_pending()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.review_service.list_pending()


def review_start_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review start`コマンド。`ReviewService.start_review()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.review_service.start_review(record_id)


def review_approve_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review approve`コマンド。`ReviewService.approve()`を呼び出す
    （GoldPromotion指定は対象外）。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.review_service.approve(record_id)


def review_reject_command(
    settings: CompositionSettings, record_id: LearningRecordId
) -> LearningRecord:
    """`review reject`コマンド。`ReviewService.reject()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.review_service.reject(record_id)


def export_all_command(settings: CompositionSettings) -> tuple[GoldRecord, ...]:
    """`export all`コマンド。`ExportService.export_all()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.export_service.export_all()


def export_person_command(settings: CompositionSettings, person_key: str) -> tuple[GoldRecord, ...]:
    """`export person`コマンド。`ExportService.export_person()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.export_service.export_person(person_key)


def export_since_command(settings: CompositionSettings, since: datetime) -> tuple[GoldRecord, ...]:
    """`export since`コマンド。`ExportService.export_since()`を呼び出す。

    Task22-8: `bootstrap.application_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with application_session(settings) as application:
        return application.export_service.export_since(since)


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """`version`コマンドの表示内容。"""

    parser_version: ParserVersion | None
    knowledge_snapshot_checksum: str
    knowledge_item_count: int
    knowledge_as_of: date


def version_command(settings: CompositionSettings) -> VersionInfo:
    """`version`コマンド。最新`ParserVersion`と`KnowledgeSnapshot`の要約を返す。

    Task22-8: `bootstrap.version_dependencies_session()`がConnectionの
    生成・close責務を持つ（Composition Rootへの集約）。
    Task22-3: `build_application()`は使わず、`version`専用の軽量Builder
    （`build_version_dependencies()`）のみを使う。`ReviewService`/`ExportService`/
    `JobRunner`/`CandidateRepository`の生成、および`parser_versions`への
    書き込み副作用（`_resolve_parser_version_id()`）のいずれも発生しない。
    """
    with version_dependencies_session(settings) as dependencies:
        snapshot = dependencies.read_knowledge_snapshot()
        return VersionInfo(
            parser_version=dependencies.read_latest_parser_version(),
            knowledge_snapshot_checksum=snapshot.snapshot_checksum,
            knowledge_item_count=len(snapshot.items),
            knowledge_as_of=snapshot.as_of,
        )


def fetch_stage_command(
    settings: CompositionSettings, url: str, destination_path: str, published_date: date
) -> PdfId | None:
    """`fetch-stage`コマンド。`JobOrchestrator.fetch_and_stage()`を呼び出す。

    戻り値`None`は、取得した内容の`content_hash`が既存の`PdfRecord`と重複した
    ため保存しなかったことを意味する（`fetch_and_stage()`自身の既存契約）。
    Task22-8: `bootstrap.job_orchestrator_session()`がConnectionの生成・close
    責務を持つ（Composition Rootへの集約）。
    """
    with job_orchestrator_session(settings) as orchestrator:
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
    Task22-8: `bootstrap.job_orchestrator_session()`がConnectionの生成・close
    責務を持つ（Composition Rootへの集約）。
    """
    with job_orchestrator_session(settings) as orchestrator:
        return orchestrator.run_workflow(
            [], export_format, export_destination, remote_path=remote_path
        )


def schedule_now_command(settings: CompositionSettings, job_type: str) -> JobId:
    """`schedule-now`コマンド。`Scheduler.trigger_now()`のみを呼び出す
    （`JobOrchestrator`を直接呼び出すことはない）。
    Task22-8: `bootstrap.scheduler_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with scheduler_session(settings) as scheduler:
        return scheduler.trigger_now(job_type)


def list_schedule_command(settings: CompositionSettings) -> tuple[str, ...]:
    """`list-schedule`コマンド。`Scheduler.list_upcoming()`のみを呼び出す
    （`JobOrchestrator`を直接呼び出すことはない）。
    Task22-8: `bootstrap.scheduler_session()`がConnectionの生成・close責務を
    持つ（Composition Rootへの集約）。
    """
    with scheduler_session(settings) as scheduler:
        return scheduler.list_upcoming()


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
    行わない。Task22-8のSession Builder化の対象外とする例外であり、本関数
    のみが引き続き`connect()`を直接呼び出す（Task22-7設計レビューで現状維持
    と判断）。
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
