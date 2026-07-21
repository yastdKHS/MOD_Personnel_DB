import pytest

from mod_personnel_db.cli import bootstrap
from mod_personnel_db.cli.bootstrap import CompositionSettings, SqliteRepositories
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


def test_build_job_runner_returns_job_runner(settings: CompositionSettings) -> None:
    job_runner = bootstrap.build_job_runner(settings)

    assert isinstance(job_runner, JobRunner)


def test_build_job_runner_generation_order(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    order: list[str] = []

    real_build_repos = bootstrap.build_sqlite_repositories
    real_build_knowledge = bootstrap.build_knowledge_service
    real_build_learning = bootstrap.build_learning_service
    real_candidate_repository = SqliteCandidateRepository
    real_job_runner_repositories = JobRunnerRepositories
    real_job_runner = JobRunner

    def traced_build_repos(connection: object) -> SqliteRepositories:
        order.append("repositories")
        return real_build_repos(connection)  # type: ignore[arg-type]

    def traced_build_knowledge(settings_arg: CompositionSettings) -> FileKnowledgeService:
        order.append("knowledge")
        return real_build_knowledge(settings_arg)

    def traced_build_learning(repositories: SqliteRepositories) -> RepositoryLearningService:
        order.append("learning")
        return real_build_learning(repositories)

    def traced_candidate_repository(*args: object, **kwargs: object) -> SqliteCandidateRepository:
        order.append("candidates")
        return real_candidate_repository(*args, **kwargs)  # type: ignore[arg-type]

    def traced_job_runner_repositories(**kwargs: object) -> JobRunnerRepositories:
        order.append("job_runner_repositories")
        return real_job_runner_repositories(**kwargs)  # type: ignore[arg-type]

    def traced_job_runner(**kwargs: object) -> JobRunner:
        order.append("job_runner")
        return real_job_runner(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(bootstrap, "build_sqlite_repositories", traced_build_repos)
    monkeypatch.setattr(bootstrap, "build_knowledge_service", traced_build_knowledge)
    monkeypatch.setattr(bootstrap, "build_learning_service", traced_build_learning)
    monkeypatch.setattr(bootstrap, "SqliteCandidateRepository", traced_candidate_repository)
    monkeypatch.setattr(bootstrap, "JobRunnerRepositories", traced_job_runner_repositories)
    monkeypatch.setattr(bootstrap, "JobRunner", traced_job_runner)

    bootstrap.build_job_runner(settings)

    assert order == [
        "repositories",
        "knowledge",
        "learning",
        "candidates",
        "job_runner_repositories",
        "job_runner",
    ]


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
