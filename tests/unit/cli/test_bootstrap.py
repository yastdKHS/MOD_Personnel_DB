from collections.abc import Callable

import pytest

from mod_personnel_db.cli import bootstrap
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings, SqliteRepositories
from mod_personnel_db.export import ExportService
from mod_personnel_db.export.service import RepositoryExportService
from mod_personnel_db.knowledge import FileKnowledgeService, KnowledgeService
from mod_personnel_db.learning import LearningService, RepositoryLearningService
from mod_personnel_db.models import LearningStatus
from mod_personnel_db.pipeline.job_runner import JobRunner, JobRunnerRepositories
from mod_personnel_db.repositories import CandidateRepository, JobRepository, PDFRepository
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
from mod_personnel_db.review import ReviewService
from mod_personnel_db.review.service import RepositoryReviewService


def test_build_sqlite_repositories_creates_seven_concrete_instances(
    settings: CompositionSettings,
) -> None:
    connection = connect(settings.db_path)

    repositories = bootstrap.build_sqlite_repositories(connection)

    assert isinstance(repositories, SqliteRepositories)
    assert isinstance(repositories.pdfs, SqlitePdfRepository)
    assert isinstance(repositories.jobs, SqliteJobRepository)
    assert isinstance(repositories.gold, SqliteGoldRepository)
    assert isinstance(repositories.knowledge, SqliteKnowledgeRepository)
    assert isinstance(repositories.review, SqliteReviewRepository)
    assert isinstance(repositories.export, SqliteExportRepository)
    assert isinstance(repositories.learning, SqliteLearningRepository)


def test_build_knowledge_service_returns_file_knowledge_service_without_repository(
    settings: CompositionSettings,
) -> None:
    knowledge_service = bootstrap.build_knowledge_service(settings)

    assert isinstance(knowledge_service, FileKnowledgeService)
    # FileKnowledgeService(Task11-2)はRepositoryを一切参照しないため、
    # knowledge_root（YAMLパス）のみでスナップショットを読み込めることを確認する。
    snapshot = knowledge_service.load_snapshot()
    assert snapshot.items == ()


def test_build_learning_service_injects_sqlite_learning_repository(
    settings: CompositionSettings,
) -> None:
    connection = connect(settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)

    learning_service = bootstrap.build_learning_service(repositories)

    assert isinstance(learning_service, RepositoryLearningService)
    open_records = learning_service.list_open()
    assert open_records == repositories.learning.list_by_status(LearningStatus.OPEN)


def test_build_review_service_injects_learning_and_gold_repositories(
    settings: CompositionSettings,
) -> None:
    connection = connect(settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)
    learning_service = bootstrap.build_learning_service(repositories)

    review_service = bootstrap.build_review_service(repositories, learning_service)

    assert isinstance(review_service, RepositoryReviewService)
    pending = review_service.list_pending()
    assert pending == repositories.learning.list_by_status(LearningStatus.OPEN)


def test_build_export_service_injects_gold_repository(settings: CompositionSettings) -> None:
    connection = connect(settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)

    export_service = bootstrap.build_export_service(repositories)

    assert isinstance(export_service, RepositoryExportService)
    assert export_service.export_all() == repositories.gold.list_current()


def test_build_application_holds_review_and_export_services(
    settings: CompositionSettings,
) -> None:
    application = bootstrap.build_application(settings)

    assert isinstance(application, Application)
    assert isinstance(application.review_service, RepositoryReviewService)
    assert isinstance(application.export_service, RepositoryExportService)


def test_build_job_runner_returns_job_runner(settings: CompositionSettings) -> None:
    job_runner = bootstrap.build_job_runner(settings)

    assert isinstance(job_runner, JobRunner)


def _tracer(order: list[str], label: str, real: Callable[..., object]) -> Callable[..., object]:
    """呼び出しを`order`へ記録してから`real`へ委譲するラッパーを返す。"""

    def wrapper(*args: object, **kwargs: object) -> object:
        order.append(label)
        return real(*args, **kwargs)

    return wrapper


_GENERATION_ORDER_TARGETS = (
    ("build_sqlite_repositories", "repositories"),
    ("build_knowledge_service", "knowledge"),
    ("build_learning_service", "learning"),
    ("build_review_service", "review"),
    ("build_export_service", "export"),
    ("SqliteCandidateRepository", "candidates"),
    ("JobRunnerRepositories", "job_runner_repositories"),
    ("JobRunner", "job_runner"),
)


def test_build_job_runner_generation_order(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    order: list[str] = []
    for attr_name, label in _GENERATION_ORDER_TARGETS:
        real = getattr(bootstrap, attr_name)
        monkeypatch.setattr(bootstrap, attr_name, _tracer(order, label, real))

    bootstrap.build_job_runner(settings)

    assert order == [label for _, label in _GENERATION_ORDER_TARGETS]


def test_job_runner_dependencies_are_protocol_typed(settings: CompositionSettings) -> None:
    """`FileKnowledgeService`等がProtocol型のみで注入可能であることをmypyで確認する。"""
    connection = connect(settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)
    knowledge_service = bootstrap.build_knowledge_service(settings)
    learning_service = bootstrap.build_learning_service(repositories)
    parser_version_id = bootstrap._resolve_parser_version_id(
        repositories.jobs, knowledge_service, settings.parser_code_version
    )

    pdfs_protocol: PDFRepository = repositories.pdfs
    jobs_protocol: JobRepository = repositories.jobs
    candidates_protocol: CandidateRepository = SqliteCandidateRepository(
        connection, parser_version_id
    )
    knowledge_protocol: KnowledgeService = knowledge_service
    learning_protocol: LearningService = learning_service

    job_runner_repositories = JobRunnerRepositories(
        pdfs=pdfs_protocol, jobs=jobs_protocol, candidates=candidates_protocol
    )
    job_runner = JobRunner(
        repositories=job_runner_repositories,
        knowledge=knowledge_protocol,
        learning=learning_protocol,
        parser_version_id=parser_version_id,
    )

    assert isinstance(job_runner, JobRunner)


def test_application_services_are_protocol_typed(settings: CompositionSettings) -> None:
    """`review_service`/`export_service`がProtocol型のみで保持可能であることをmypyで確認する。"""
    application = bootstrap.build_application(settings)

    review_protocol: ReviewService = application.review_service
    export_protocol: ExportService = application.export_service

    assert review_protocol.list_pending() == ()
    assert export_protocol.export_all() == ()
