import ast
from collections.abc import Callable
from pathlib import Path

import pytest

import mod_personnel_db
from mod_personnel_db.cli import bootstrap
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings, SqliteRepositories
from mod_personnel_db.export import ExportService
from mod_personnel_db.export.service import RepositoryExportService
from mod_personnel_db.features import DefaultFeatureStore
from mod_personnel_db.fetch import FetchClient, HTTPFetchClient
from mod_personnel_db.ftp import FTPClient, StandardFTPClient
from mod_personnel_db.knowledge import FileKnowledgeService, KnowledgeService
from mod_personnel_db.learning import LearningService, RepositoryLearningService
from mod_personnel_db.models import LearningStatus, PdfId
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
from mod_personnel_db.services import DefaultJobOrchestrator


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


# --- Phase7統合（Task17-0/17-1）: build_fetch_client / build_ftp_client /
# build_feature_store / build_job_orchestrator ---


def test_build_fetch_client_returns_http_fetch_client() -> None:
    """`build_fetch_client()`は`HTTPFetchClient`のみを生成する（Mockは生成しない）。"""
    fetch_client = bootstrap.build_fetch_client()

    assert isinstance(fetch_client, HTTPFetchClient)
    fetch_protocol: FetchClient = fetch_client
    assert fetch_protocol is fetch_client


def test_build_ftp_client_returns_standard_ftp_client(settings: CompositionSettings) -> None:
    """`build_ftp_client()`は`StandardFTPClient`のみを生成する（Mockは生成しない）。"""
    ftp_client = bootstrap.build_ftp_client(settings)

    assert isinstance(ftp_client, StandardFTPClient)
    ftp_protocol: FTPClient = ftp_client
    assert ftp_protocol is ftp_client


def test_build_feature_store_returns_default_feature_store() -> None:
    """`build_feature_store()`は`DefaultFeatureStore`を生成するが、他のいかなる
    `build_*`関数からも呼び出されない（`JobRunner`への配線は行わない、Task17-0設計）。
    """
    feature_store = bootstrap.build_feature_store()

    assert isinstance(feature_store, DefaultFeatureStore)


def test_build_job_orchestrator_wires_dependencies_via_constructor_injection(
    settings: CompositionSettings,
) -> None:
    """`build_job_orchestrator()`は既存の生成順序1〜9の成果物を`OrchestratorDependencies`
    へ束ねるのみであり、新たな具象実装を生成しない（Constructor Injectionのみ）。
    """
    connection = connect(settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)
    application = bootstrap.build_application(settings)
    fetch_client = bootstrap.build_fetch_client()
    ftp_client = bootstrap.build_ftp_client(settings)

    orchestrator = bootstrap.build_job_orchestrator(
        application, repositories, fetch_client, ftp_client
    )

    assert isinstance(orchestrator, DefaultJobOrchestrator)
    assert orchestrator.run_pending_pipeline() == ()
    assert orchestrator.list_pending_reviews() == ()


def test_build_application_backward_compatible_after_phase7_integration(
    settings: CompositionSettings,
) -> None:
    """Phase7統合の追加後も`build_application()`の戻り値・公開属性は変更されない。"""
    application = bootstrap.build_application(settings)

    assert isinstance(application, Application)
    assert isinstance(application.job_runner, JobRunner)
    assert isinstance(application.review_service, RepositoryReviewService)
    assert isinstance(application.export_service, RepositoryExportService)
    assert application.read_pdf(PdfId(1)) is None
    # build_application()自体がParserVersionを解決・記録する副作用を持つため
    # （既存の_resolve_parser_version_id()、Phase7統合前から変わらない挙動）、
    # Noneではなくsettingsのparser_code_versionと一致するレコードを期待する。
    latest_version = application.read_latest_parser_version()
    assert latest_version is not None
    assert latest_version.code_version == settings.parser_code_version
    assert application.read_knowledge_snapshot().items == ()


_FORBIDDEN_PHASE7_CONSTRUCTOR_CALLS = {
    "HTTPFetchClient",
    "StandardFTPClient",
    "DefaultJobOrchestrator",
}


def _called_names(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def test_only_composition_root_constructs_phase7_concrete_implementations() -> None:
    """`HTTPFetchClient`・`StandardFTPClient`・`DefaultJobOrchestrator`の直接インスタンス化は
    `cli/bootstrap.py`（Composition Root）以外のいかなる`src/mod_personnel_db/`配下モジュールにも
    存在しないことをASTで確認する（レビュー項目「Composition Root一本化維持」）。
    """
    src_root = Path(mod_personnel_db.__file__).parent
    bootstrap_path = Path(bootstrap.__file__)

    for source_path in sorted(src_root.rglob("*.py")):
        if source_path == bootstrap_path:
            continue
        called = _called_names(source_path)
        violations = called & _FORBIDDEN_PHASE7_CONSTRUCTOR_CALLS
        assert not violations, f"{source_path} constructs concrete types: {violations}"


def test_build_job_orchestrator_does_not_construct_new_types_in_body() -> None:
    """`build_job_orchestrator()`の本体は`DefaultJobOrchestrator(OrchestratorDependencies(...))`
    の呼び出しのみであり、他の関数呼び出し（＝新たな具象生成）を含まないことをASTで確認する。
    """
    source_path = Path(bootstrap.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    func_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_job_orchestrator"
    )
    called_names = {
        n.func.id
        for n in ast.walk(func_node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert called_names == {"DefaultJobOrchestrator", "OrchestratorDependencies"}
