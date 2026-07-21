"""Composition Root本体。docs/api/dependency-rule.md#合成ルートcomposition-root,
ADR-0046に対応する。

`repositories/sqlite/`の各具象クラス・`FileKnowledgeService`・
`RepositoryLearningService`を生成し、`JobRunner`へ個別にコンストラクタ注入
（Protocol型）する唯一の場所である。以下の順序でのみ依存を構築する
（ADR-0046「Composition Rootの責務チェーン」）。

1. SQLite Repository具象生成
2. `KnowledgeService`生成（Repositoryは渡さない、Task11-2）
3. `LearningService`生成（`LearningRepository`のみ注入、Task11-4）
4. `JobRunnerRepositories`生成
5. `JobRunner`生成

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
"""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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


@dataclass(frozen=True, slots=True)
class CompositionSettings:
    """合成ルートが依存生成に必要とする最小限の設定値。"""

    db_path: str
    knowledge_root: Path
    layouts_root: Path
    parser_code_version: str


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
    """生成順序1〜5の最終成果物。`JobRunner`と、CLIコマンド層向けの
    Repository非公開な読み取り専用アクセスを束ねる（Task11-6）。
    """

    job_runner: JobRunner
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
    """合成ルート本体。生成順序1〜5をこの順序でのみ実行し、`Application`を返す。"""
    connection = connect(settings.db_path)
    repositories = build_sqlite_repositories(connection)
    knowledge_service = build_knowledge_service(settings)
    learning_service = build_learning_service(repositories)
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
        _pdfs=repositories.pdfs,
        _jobs=repositories.jobs,
        _knowledge_service=knowledge_service,
    )


def build_job_runner(settings: CompositionSettings) -> JobRunner:
    """合成ルート本体（Task11-5）。`build_application`が返す`JobRunner`を返す。"""
    return build_application(settings).job_runner


__all__ = [
    "Application",
    "CompositionSettings",
    "SqliteRepositories",
    "build_application",
    "build_job_runner",
    "build_knowledge_service",
    "build_learning_service",
    "build_sqlite_repositories",
]
