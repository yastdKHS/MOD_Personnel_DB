"""`DefaultJobOrchestrator`と実装済みパッケージ群との結合テスト（Phase7 Task16-4）。

`tests/unit/services/test_orchestrator.py`がStubで呼び出し規約を検証する
のに対し、本テストは実際のHTTPサーバ（標準ライブラリの`http.server`）・
実際のSQLiteデータベース・実際の`JobRunner`/`ReviewService`/`ExportService`
（`pipeline/`・`review/`・`export/`は一切変更していない）・実際の
`InMemoryFTPClient`（`ftp/`が提供するテスト用実装）を組み合わせ、
`services/`が正しくこれらを配線・呼び出すことを確認する。

`cli.bootstrap.build_application()`/`cli.app.main()`は、既に実装済みの
Composition Rootをテストのフィクスチャ構築（Arrange）のためだけに再利用する
（`tests/integration/config/test_settings_integration.py`・
`tests/integration/cli/_fixtures.py`と同じ扱いであり、`services/`自身の
実行時コード（`src/mod_personnel_db/services/`）が`cli/`に依存するわけでは
ない。`tests/unit/services/test_dependency_ownership.py`が後者を保証する）。

中核パイプラインの実行結果自体の正しさはGolden Test（ADR-0007）が別途担保
するため、本テストは`run_pending_pipeline()`を未処理PDFが存在しない状態
（空の`pdfs`テーブル）で呼び出し、オーケストレーションの配線のみを検証する。
"""

import http.server
import threading
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest

from mod_personnel_db.cli import app
from mod_personnel_db.cli.bootstrap import CompositionSettings, build_application
from mod_personnel_db.fetch import FetchRequest, HTTPFetchClient
from mod_personnel_db.ftp import InMemoryFTPClient
from mod_personnel_db.repositories.sqlite import SqlitePdfRepository, connect
from mod_personnel_db.services.orchestrator import DefaultJobOrchestrator, OrchestratorDependencies

_PDF_BODY = b"%PDF-1.4 sample-order-body"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(_PDF_BODY)))
        self.end_headers()
        self.wfile.write(_PDF_BODY)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def server_url() -> Iterator[str]:
    httpd = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join()


@pytest.fixture
def settings(tmp_path: Path) -> CompositionSettings:
    db_path = tmp_path / "mod_personnel.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    layouts_root = tmp_path / "layouts"
    knowledge_root.mkdir()
    layouts_root.mkdir()
    resolved = CompositionSettings(
        db_path=str(db_path),
        knowledge_root=knowledge_root,
        layouts_root=layouts_root,
        parser_code_version="v1.0.0",
    )
    exit_code = app.main(
        [
            "--db-path",
            resolved.db_path,
            "--knowledge-root",
            str(resolved.knowledge_root),
            "--layouts-root",
            str(resolved.layouts_root),
            "--parser-code-version",
            resolved.parser_code_version,
            "init-db",
        ]
    )
    assert exit_code == 0
    return resolved


@pytest.fixture
def orchestrator_factory(
    settings: CompositionSettings,
) -> Iterator[Callable[[InMemoryFTPClient], DefaultJobOrchestrator]]:
    application = build_application(settings)
    connection = connect(settings.db_path)
    pdf_repository = SqlitePdfRepository(connection)

    def factory(ftp_client: InMemoryFTPClient) -> DefaultJobOrchestrator:
        return DefaultJobOrchestrator(
            OrchestratorDependencies(
                fetch_client=HTTPFetchClient(),
                ftp_client=ftp_client,
                pdf_repository=pdf_repository,
                job_runner=application.job_runner,
                review_service=application.review_service,
                export_service=application.export_service,
            )
        )

    try:
        yield factory
    finally:
        connection.close()


def test_fetch_and_stage_persists_real_pdf_via_real_http_and_sqlite(
    server_url: str,
    orchestrator_factory: Callable[[InMemoryFTPClient], DefaultJobOrchestrator],
    tmp_path: Path,
) -> None:
    orchestrator = orchestrator_factory(InMemoryFTPClient())
    destination = str(tmp_path / "order.pdf")

    pdf_id = orchestrator.fetch_and_stage(
        FetchRequest(url=f"{server_url}/order.pdf", expected_content_types=("application/pdf",)),
        destination_path=destination,
        published_date=date(2026, 1, 1),
    )

    assert pdf_id is not None
    assert Path(destination).read_bytes() == _PDF_BODY

    # 同一内容を再取得すると、content_hashの重複によりNoneが返る（実SQLiteでの
    # UNIQUE制約付き列に基づくdedup確認）。
    duplicate_destination = str(tmp_path / "order-again.pdf")
    duplicate_id = orchestrator.fetch_and_stage(
        FetchRequest(url=f"{server_url}/order.pdf"),
        destination_path=duplicate_destination,
        published_date=date(2026, 1, 1),
    )
    assert duplicate_id is None
    assert not Path(duplicate_destination).exists()


def test_run_pending_pipeline_with_no_staged_pdfs_returns_empty(
    orchestrator_factory: Callable[[InMemoryFTPClient], DefaultJobOrchestrator],
) -> None:
    orchestrator = orchestrator_factory(InMemoryFTPClient())

    results = orchestrator.run_pending_pipeline()

    assert results == ()


def test_list_pending_reviews_with_empty_learning_dataset_returns_empty(
    orchestrator_factory: Callable[[InMemoryFTPClient], DefaultJobOrchestrator],
) -> None:
    orchestrator = orchestrator_factory(InMemoryFTPClient())

    reviews = orchestrator.list_pending_reviews()

    assert reviews == ()


def test_export_and_publish_uploads_real_export_via_in_memory_ftp(
    orchestrator_factory: Callable[[InMemoryFTPClient], DefaultJobOrchestrator],
    tmp_path: Path,
) -> None:
    ftp_client = InMemoryFTPClient()
    orchestrator = orchestrator_factory(ftp_client)
    destination = tmp_path / "export.json"

    artifact = orchestrator.export_and_publish(
        "json", destination, remote_path="remote/export.json"
    )

    assert artifact.record_count == 0
    assert destination.exists()

    ftp_client.connect()
    downloaded = tmp_path / "downloaded.json"
    ftp_client.download("remote/export.json", str(downloaded))
    assert downloaded.read_bytes() == destination.read_bytes()
