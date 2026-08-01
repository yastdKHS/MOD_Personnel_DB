import ast
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr

import mod_personnel_db
from mod_personnel_db.cli import bootstrap
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings, SqliteRepositories
from mod_personnel_db.config import FtpSettings
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
from mod_personnel_db.services import (
    RUN_PENDING_JOB_TYPE,
    DefaultJobOrchestrator,
    DefaultScheduler,
    JobSchedule,
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


def test_build_application_with_repositories_reuses_same_pdf_instance(
    settings: CompositionSettings,
) -> None:
    """`build_application_with_repositories()`が返す`repositories.pdfs`は、
    `Application`が内部で保持する`_pdfs`と同一インスタンスである（Task22-6）。
    `_build_job_orchestrator()`が本関数の戻り値の`repositories`をそのまま
    JobOrchestrator生成へ渡せるのは、この同一性が保証されているため。
    """
    application, repositories = bootstrap.build_application_with_repositories(settings)

    assert isinstance(repositories, SqliteRepositories)
    assert repositories.pdfs is application._pdfs


def test_build_application_reuses_provided_connection(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`connection`を明示指定した場合、`build_application()`は新規に`connect()`しない
    （Task21-2、Task21-1で選定した案Bの前提。`cli/commands.py`の
    `_build_job_orchestrator()`が同一Connectionを共有するために必要）。
    """
    connect_calls: list[str] = []

    def counting_connect(db_path: str) -> sqlite3.Connection:
        connect_calls.append(db_path)
        return connect(db_path)

    connection = connect(settings.db_path)
    monkeypatch.setattr(bootstrap, "connect", counting_connect)

    application = bootstrap.build_application(settings, connection)

    assert isinstance(application, Application)
    assert connect_calls == []


def test_build_application_without_connection_still_connects(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`connection`省略時は従来どおり`connect()`で新規に接続を生成する
    （Task21-2、既存呼び出し元との後方互換性）。
    """
    connect_calls: list[str] = []

    def counting_connect(db_path: str) -> sqlite3.Connection:
        connect_calls.append(db_path)
        return connect(db_path)

    monkeypatch.setattr(bootstrap, "connect", counting_connect)

    application = bootstrap.build_application(settings)

    assert isinstance(application, Application)
    assert connect_calls == [settings.db_path]


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


def test_build_ftp_client_falls_back_to_placeholder_when_ftp_settings_unset(
    settings: CompositionSettings,
) -> None:
    """`settings.ftp`が`None`（Task18-1既定のfixtureはFTP環境変数を持たない）の場合、
    Task17-1時点と同じ`host=""`のプレースホルダを返し、FTPを利用しない既存コマンド
    （`fetch-stage`等）の後方互換性を維持する。
    """
    assert settings.ftp is None

    ftp_client = bootstrap.build_ftp_client(settings)

    assert isinstance(ftp_client, StandardFTPClient)
    assert ftp_client._config.host == ""
    assert ftp_client._config.remote_directory == ""


def test_build_ftp_client_uses_app_settings_ftp_when_configured(
    settings: CompositionSettings,
) -> None:
    """`settings.ftp`（`FtpSettings`）が設定されている場合、`build_ftp_client()`は
    プレースホルダではなくその実接続情報を`FTPConnectionConfig`へ反映する
    （レビュー項目「プレースホルダは禁止」）。`remote_directory`（Task18-9で
    配線）も含め、`FtpSettings`の全フィールドが漏れなく渡ることを確認する。
    """
    configured_settings = settings.model_copy(
        update={
            "ftp": FtpSettings(
                host="ftp.example.com",
                port=2121,
                username="publisher",
                password=SecretStr("s3cret"),
                remote_directory="/public",
                timeout=45.0,
            )
        }
    )

    ftp_client = bootstrap.build_ftp_client(configured_settings)

    assert isinstance(ftp_client, StandardFTPClient)
    config = ftp_client._config
    assert config.host == "ftp.example.com"
    assert config.port == 2121
    assert config.username == "publisher"
    assert config.password == "s3cret"
    assert config.timeout == 45.0
    assert config.remote_directory == "/public"


def test_build_ftp_client_passes_default_remote_directory_when_unspecified(
    settings: CompositionSettings,
) -> None:
    """`FtpSettings.remote_directory`を明示的に指定しない場合でも、`FtpSettings`
    自身の既定値（`"/"`）がそのまま`FTPConnectionConfig.remote_directory`へ渡る
    （Task18-9、`build_ftp_client()`は値を素通しするのみで独自の既定値判断は
    行わない）。
    """
    configured_settings = settings.model_copy(update={"ftp": FtpSettings(host="ftp.example.com")})

    ftp_client = bootstrap.build_ftp_client(configured_settings)

    assert ftp_client._config.remote_directory == "/"


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
    "DefaultScheduler",
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


def test_job_orchestrator_session_calls_connect_exactly_once(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`bootstrap.job_orchestrator_session()`は`connect()`を1回のみ呼び出し、
    Application生成（`build_application_with_repositories()`）とJobOrchestrator
    生成（`build_sqlite_repositories()`が返す`repositories.pdfs`）とで同一
    Connectionを共有する（Task21-2、Task22-8でSession Builder化）。以前は
    `build_application()`内部でも独自に`connect()`が呼ばれ、同一`db_path`への
    接続が1回のコマンド実行あたり2本生成されていた（Task20-2で判明）。
    """
    connect_calls: list[str] = []

    def counting_connect(db_path: str) -> sqlite3.Connection:
        connect_calls.append(db_path)
        return connect(db_path)

    monkeypatch.setattr(bootstrap, "connect", counting_connect)

    with bootstrap.job_orchestrator_session(settings) as orchestrator:
        assert orchestrator is not None

    assert connect_calls == [settings.db_path]


def test_job_orchestrator_session_calls_build_sqlite_repositories_exactly_once(
    monkeypatch: pytest.MonkeyPatch, settings: CompositionSettings
) -> None:
    """`bootstrap.job_orchestrator_session()`は`build_application_with_repositories()`を
    経由して`build_sqlite_repositories()`を1回のみ呼び出す（Task22-6、Task22-8で
    Session Builder化）。以前は`build_application()`用とJobOrchestrator用とで
    それぞれ1回ずつ、計2回`build_sqlite_repositories()`が呼ばれ、`jobs`/`gold`/
    `knowledge`/`review`/`export`/`learning`の各Repositoryが未使用のまま二重生成
    されていた（Task20-2で判明、Task21-6/21-7で改善候補化）。
    """
    build_sqlite_repositories_calls: list[sqlite3.Connection] = []
    original_build_sqlite_repositories = bootstrap.build_sqlite_repositories

    def counting_build_sqlite_repositories(
        connection: sqlite3.Connection,
    ) -> bootstrap.SqliteRepositories:
        build_sqlite_repositories_calls.append(connection)
        return original_build_sqlite_repositories(connection)

    monkeypatch.setattr(bootstrap, "build_sqlite_repositories", counting_build_sqlite_repositories)

    with bootstrap.job_orchestrator_session(settings) as orchestrator:
        assert orchestrator is not None

    assert len(build_sqlite_repositories_calls) == 1


# --- Phase7統合Step4（Task17-4）: build_scheduler ---


def test_build_scheduler_wires_dependencies_via_constructor_injection(
    settings: CompositionSettings,
) -> None:
    """`build_scheduler()`は呼び出し元が渡した`JobOrchestrator`・スケジュール一覧・
    `clock`を`DefaultScheduler`へ束ねるのみであり、新たな具象実装を生成しない
    （Constructor Injectionのみ）。
    """
    connection = connect(settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)
    application = bootstrap.build_application(settings)
    fetch_client = bootstrap.build_fetch_client()
    ftp_client = bootstrap.build_ftp_client(settings)
    orchestrator = bootstrap.build_job_orchestrator(
        application, repositories, fetch_client, ftp_client
    )
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(
        job_type=RUN_PENDING_JOB_TYPE, interval=timedelta(hours=6), anchor=anchor
    )
    fixed_now = anchor + timedelta(hours=7)

    scheduler = bootstrap.build_scheduler(orchestrator, (schedule,), lambda: fixed_now)

    assert isinstance(scheduler, DefaultScheduler)
    assert scheduler.list_upcoming() == (f"{RUN_PENDING_JOB_TYPE} at 2026-01-01T12:00:00+00:00",)


def test_build_scheduler_does_not_construct_new_types_in_body() -> None:
    """`build_scheduler()`の本体は`DefaultScheduler(...)`の呼び出しのみであり、
    他の関数呼び出し（＝新たな具象生成）を含まないことをASTで確認する。
    """
    source_path = Path(bootstrap.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    func_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_scheduler"
    )
    called_names = {
        n.func.id
        for n in ast.walk(func_node)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert called_names == {"DefaultScheduler"}
