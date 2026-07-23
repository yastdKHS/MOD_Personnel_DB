"""Composition Root本体。docs/api/dependency-rule.md#合成ルートcomposition-root,
ADR-0046に対応する。

`repositories/sqlite/`の各具象クラス・`FileKnowledgeService`・
`RepositoryLearningService`・`RepositoryReviewService`・
`RepositoryExportService`を生成し、`JobRunner`へ個別にコンストラクタ注入
（Protocol型）する唯一の場所である。以下の順序でのみ依存を構築する
（ADR-0046「Composition Rootの責務チェーン」、Task12-2でReview/Export生成
を追加）。

1. SQLite Repository具象生成
2. `KnowledgeService`生成（Repositoryは渡さない、Task11-2）
3. `LearningService`生成（`LearningRepository`のみ注入、Task11-4）
4. `ReviewService`生成（`LearningRepository`・`GoldRepository`・
   `LearningService`のみ注入、Task12-0）
5. `ExportService`生成（`GoldRepository`のみ注入、Task12-1）
6. `JobRunnerRepositories`生成
7. `JobRunner`生成

`SqliteCandidateRepository`は（本タスクより前のTaskで確定した既存実装として）
コンストラクタで`ParserVersionId`を要求するため、8 Repositoryのうち
`CandidateRepository`のみは技術的に順序1の内部で即時生成できない
（`ParserVersionId`は順序2で生成する`KnowledgeService`のスナップショット
チェックサムを用いて解決するため）。本モジュールはこれを、順序1で残り7
Repositoryを生成し、順序2の直後に`ParserVersionId`を解決してから
`CandidateRepository`を生成する形で扱う。「Repository具象生成が先、
Knowledge/Learning生成が後」という順序制約自体（ADR-0046の核心）は
変更していない。

`UnitOfWork`・Service Locator・Singleton・グローバル可変状態・DIコンテナ
ライブラリのいずれも用いない。DBスキーマの適用（`apply_schema`）は
`cli/init.py`の責務であり、本モジュールは行わない。

`Application`（Task11-6で追加）は、`cli/`のコマンド層（`commands.py`・
`app.py`・`__main__.py`）が`JobRunner`に加えて必要とするごく少数の
読み取り専用アクセス（`run-job`用のPDF解決、`version`用の最新
ParserVersion/KnowledgeSnapshot取得）を、Repositoryオブジェクトそのもの
を渡さずに提供するための束である。コマンド層は`Application`のメソッド
（ドメイン値のみを返す）を通じてのみ間接的にアクセスし、`SqlitePdfRepository`
等を直接import・保持しない。

`CompositionSettings`（合成ルートが依存生成に必要とする設定値）は、
Phase6 Task14-5以降`config.AppSettings`（Pydantic Settings、ADR-0028）の
別名である。フィールド構成（`db_path`/`knowledge_root`/`layouts_root`/
`parser_code_version`）はTask14-5より前のローカルdataclass実装と等価
だが、環境変数・`.env`ファイルからの読み込みにも対応する。`AppSettings`の
生成は本モジュールの`build_settings()`経由のみに限定し、`cli/app.py`等の
呼び出し元は`build_settings()`を呼ぶのみで自らSettingsを生成しない。

**Phase7統合（Task17-0で確定した設計・Task17-1で実装）**: 上記の生成順序
1〜7（`build_application()`）に続けて、順序8「`FetchClient`生成」・
順序9「`FTPClient`生成」・順序10「`JobOrchestrator`生成」を追加する
（docs/phase7-integration-design.md）。既存の生成順序1〜7・`build_settings()`
等の既存公開関数のシグネチャはこの統合によって変更しない（加算的統合）。
`build_feature_store()`は`FeatureStore`を生成するが、`JobRunner`の
コンストラクタ拡張（別途新規ADRを前提とする将来タスク）が未実装であるため、
現時点ではどこからも呼び出されない未使用のBuilderとして提供する。新規CLI
サブコマンドの追加は本Taskの対象外である。
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mod_personnel_db.config import AppSettings
from mod_personnel_db.export.service import RepositoryExportService
from mod_personnel_db.features import DefaultFeatureStore
from mod_personnel_db.fetch import FetchClient, HTTPFetchClient
from mod_personnel_db.ftp import FTPClient, FTPConnectionConfig, StandardFTPClient
from mod_personnel_db.knowledge import FileKnowledgeService
from mod_personnel_db.layout.definitions import load_layout_definitions
from mod_personnel_db.learning import RepositoryLearningService
from mod_personnel_db.models import (
    KnowledgeSnapshot,
    ParserVersion,
    ParserVersionId,
    PdfId,
    PdfRecord,
)
from mod_personnel_db.pipeline.job_runner import JobRunner, JobRunnerRepositories
from mod_personnel_db.repositories.sqlite import (
    SqliteCandidateRepository,
    SqliteExportRepository,
    SqliteGoldRepository,
    SqliteJobRepository,
    SqliteKnowledgeRepository,
    SqliteLearningRepository,
    SqlitePdfRepository,
    SqliteReviewRepository,
    connect,
)
from mod_personnel_db.review.service import RepositoryReviewService
from mod_personnel_db.services import DefaultJobOrchestrator, OrchestratorDependencies

#: 合成ルートが依存生成に必要とする設定値の型。Phase6 Task14-5以降
#: `config.AppSettings`（Pydantic Settings、ADR-0028）の別名であり、
#: `cli/commands.py`・`cli/app.py`・既存テストは変更なしに継続して
#: この名前をimportできる。
CompositionSettings = AppSettings


def build_settings(
    *,
    db_path: str,
    knowledge_root: Path,
    layouts_root: Path,
    parser_code_version: str,
) -> AppSettings:
    """CLI引数から`AppSettings`を生成する唯一の入り口（合成ルート、ADR-0028）。

    `AppSettings`の生成は本関数経由のみに限定する。`cli/app.py`はこの
    関数を呼び出すのみで、`AppSettings`/`CompositionSettings`を自ら
    構築しない。
    """
    return AppSettings(
        db_path=db_path,
        knowledge_root=knowledge_root,
        layouts_root=layouts_root,
        parser_code_version=parser_code_version,
    )


@dataclass(frozen=True, slots=True)
class SqliteRepositories:
    """生成順序1の成果物: `CandidateRepository`を除くSQLite Repository具象実装の束。"""

    pdfs: SqlitePdfRepository
    jobs: SqliteJobRepository
    gold: SqliteGoldRepository
    knowledge: SqliteKnowledgeRepository
    review: SqliteReviewRepository
    export: SqliteExportRepository
    learning: SqliteLearningRepository


def build_sqlite_repositories(connection: sqlite3.Connection) -> SqliteRepositories:
    """生成順序1: `CandidateRepository`を除くSQLite Repository具象実装を生成する。"""
    return SqliteRepositories(
        pdfs=SqlitePdfRepository(connection),
        jobs=SqliteJobRepository(connection),
        gold=SqliteGoldRepository(connection),
        knowledge=SqliteKnowledgeRepository(connection),
        review=SqliteReviewRepository(connection),
        export=SqliteExportRepository(connection),
        learning=SqliteLearningRepository(connection),
    )


def build_knowledge_service(settings: CompositionSettings) -> FileKnowledgeService:
    """生成順序2: KnowledgeServiceを生成する。Repositoryは渡さない（Task11-2）。"""
    return FileKnowledgeService(settings.knowledge_root)


def build_learning_service(repositories: SqliteRepositories) -> RepositoryLearningService:
    """生成順序3: LearningServiceを生成する。LearningRepositoryのみを注入する（Task11-4）。"""
    return RepositoryLearningService(repositories.learning)


def build_review_service(
    repositories: SqliteRepositories, learning_service: RepositoryLearningService
) -> RepositoryReviewService:
    """生成順序4: ReviewServiceを生成する。LearningRepository・GoldRepository・
    LearningServiceのみを注入する（Task12-0）。Repository具象は自ら生成しない。
    """
    return RepositoryReviewService(repositories.learning, repositories.gold, learning_service)


def build_export_service(repositories: SqliteRepositories) -> RepositoryExportService:
    """生成順序5: ExportServiceを生成する。GoldRepositoryのみを注入する（Task12-1）。"""
    return RepositoryExportService(repositories.gold)


def _resolve_parser_version_id(
    jobs: SqliteJobRepository,
    knowledge_service: FileKnowledgeService,
    code_version: str,
) -> ParserVersionId:
    existing = jobs.get_parser_version(code_version)
    if existing is not None and existing.id is not None:
        return existing.id
    checksum = knowledge_service.load_snapshot().snapshot_checksum
    new_version = ParserVersion(
        id=None,
        code_version=code_version,
        knowledge_snapshot_checksum=checksum,
        released_at=datetime.now(UTC),
        notes=None,
    )
    return jobs.record_parser_version(new_version)


@dataclass(frozen=True, slots=True)
class Application:
    """生成順序1〜7の最終成果物。`JobRunner`・`ReviewService`・`ExportService`と、
    CLIコマンド層向けのRepository非公開な読み取り専用アクセスを束ねる
    （Task11-6、Task12-2でreview_service/export_serviceを追加）。

    `review_service`・`export_service`はそれ自身が既にRepository内部構造を
    公開しない安全な公開APIであるため（Task12-0/Task12-1）、
    `read_pdf`等とは異なり公開属性としてそのまま保持する。
    """

    job_runner: JobRunner
    review_service: RepositoryReviewService
    export_service: RepositoryExportService
    _pdfs: SqlitePdfRepository
    _jobs: SqliteJobRepository
    _knowledge_service: FileKnowledgeService

    def read_pdf(self, pdf_id: PdfId) -> PdfRecord | None:
        """`run-job`コマンドが対象PDFを解決するための読み取り専用アクセス。"""
        return self._pdfs.get(pdf_id)

    def read_latest_parser_version(self) -> ParserVersion | None:
        """`version`コマンドが表示する最新`ParserVersion`。"""
        return self._jobs.get_latest_parser_version()

    def read_knowledge_snapshot(self) -> KnowledgeSnapshot:
        """`version`コマンドが表示する`KnowledgeSnapshot`。"""
        return self._knowledge_service.load_snapshot()


def build_application(settings: CompositionSettings) -> Application:
    """合成ルート本体。生成順序1〜7をこの順序でのみ実行し、`Application`を返す。"""
    connection = connect(settings.db_path)
    repositories = build_sqlite_repositories(connection)
    knowledge_service = build_knowledge_service(settings)
    learning_service = build_learning_service(repositories)
    review_service = build_review_service(repositories, learning_service)
    export_service = build_export_service(repositories)
    parser_version_id = _resolve_parser_version_id(
        repositories.jobs, knowledge_service, settings.parser_code_version
    )
    candidates = SqliteCandidateRepository(connection, parser_version_id)
    layout_definitions = load_layout_definitions(settings.layouts_root)
    job_runner_repositories = JobRunnerRepositories(
        pdfs=repositories.pdfs,
        jobs=repositories.jobs,
        candidates=candidates,
    )
    job_runner = JobRunner(
        repositories=job_runner_repositories,
        knowledge=knowledge_service,
        learning=learning_service,
        parser_version_id=parser_version_id,
        layout_definitions=layout_definitions,
    )
    return Application(
        job_runner=job_runner,
        review_service=review_service,
        export_service=export_service,
        _pdfs=repositories.pdfs,
        _jobs=repositories.jobs,
        _knowledge_service=knowledge_service,
    )


def build_job_runner(settings: CompositionSettings) -> JobRunner:
    """合成ルート本体（Task11-5）。`build_application`が返す`JobRunner`を返す。"""
    return build_application(settings).job_runner


def build_fetch_client() -> HTTPFetchClient:
    """生成順序8（Phase7 Task17-0/17-1）: `FetchClient`を生成する。

    `HTTPFetchClient`（標準ライブラリの`urllib`ベース）のみを生成する。設定値
    への依存を持たないため、他のいかなる`build_*`関数よりも先に呼び出せる
    （docs/phase7-integration-design.md#5-fetchclient生成位置）。テスト用の
    `MockFetchClient`は合成ルートでは生成しない。
    """
    return HTTPFetchClient()


def build_ftp_client(settings: CompositionSettings) -> StandardFTPClient:
    """生成順序9（Phase7 Task17-0/17-1）: `FTPClient`を生成する。

    `StandardFTPClient`（`ftplib`ベース）のみを生成する。テスト用の
    `InMemoryFTPClient`は合成ルートでは生成しない。

    TODO(Phase7統合、`config/`拡張待ち): `AppSettings`は現時点でFTP接続情報
    （host/port/username/password等）を持たない。`docs/configuration.md`が
    設計する`FtpSettings`（`SecretStr`によるパスワード秘匿を含むネスト設定）
    が`config/`へ追加された後、`settings.ftp`から実接続情報を取得するよう
    本関数を更新する（docs/phase7-integration-design.md#6-ftpclient生成位置）。
    それまでは`settings`引数はTask17-0が確定したシグネチャ整合のためにのみ
    保持し、内部では使用しない。
    """
    del settings
    return StandardFTPClient(FTPConnectionConfig(host=""))


def build_feature_store() -> DefaultFeatureStore:
    """Phase7 Task17-0/17-1: `FeatureStore`を生成する。

    `JobRunner`（`pipeline/job_runner.py`）が`FeatureStore`をコンストラクタ
    注入で受け取る拡張は未実装であるため、本関数は現時点でどこからも
    呼び出されない未使用のBuilderとして提供する（`JobRunner`への配線は行わない、
    docs/phase7-integration-design.md#7-featurestore生成位置）。
    """
    return DefaultFeatureStore()


def build_job_orchestrator(
    application: Application,
    repositories: SqliteRepositories,
    fetch_client: FetchClient,
    ftp_client: FTPClient,
) -> DefaultJobOrchestrator:
    """生成順序10（Phase7 Task17-0/17-1）: `JobOrchestrator`を生成する。

    既存の生成順序1〜7（`build_application()`）・順序8〜9（`build_fetch_client()`/
    `build_ftp_client()`）が構築済みのインスタンスを`OrchestratorDependencies`へ
    束ねるのみであり、本関数自身は新たな具象実装を生成しない（Constructor
    Injectionのみで依存を解決する、docs/phase7-integration-design.md
    #4-joborchestrator生成位置）。
    """
    return DefaultJobOrchestrator(
        OrchestratorDependencies(
            fetch_client=fetch_client,
            ftp_client=ftp_client,
            pdf_repository=repositories.pdfs,
            job_runner=application.job_runner,
            review_service=application.review_service,
            export_service=application.export_service,
        )
    )


__all__ = [
    "Application",
    "CompositionSettings",
    "SqliteRepositories",
    "build_application",
    "build_export_service",
    "build_feature_store",
    "build_fetch_client",
    "build_ftp_client",
    "build_job_orchestrator",
    "build_job_runner",
    "build_knowledge_service",
    "build_learning_service",
    "build_review_service",
    "build_settings",
    "build_sqlite_repositories",
]
