"""Phase7統合（Task17-0/17-1）の結合テスト。

`build_fetch_client()`/`build_ftp_client()`/`build_feature_store()`/
`build_job_orchestrator()`（`cli/bootstrap.py`、Task17-1で新設）が、
`app.main([..., "init-db"])`（CLI公開API）経由でスキーマ適用済みの実SQLite
データベースに対して実際に生成できることを確認する。既存の
`build_application()`（Task11-5〜Task12-2）との組み合わせにより、Phase7統合
（`docs/phase7-integration-design.md`）が設計した生成順序8〜10が実際に動作
することの検証であり、`tests/unit/cli/test_bootstrap.py`のUnit Testが確認
する個別のシグネチャ・型の妥当性とは異なる観点（実データベース・実接続を
用いた結線）を扱う。
"""

from mod_personnel_db.cli import bootstrap
from mod_personnel_db.cli.bootstrap import Application, CompositionSettings
from mod_personnel_db.features import DefaultFeatureStore
from mod_personnel_db.fetch import HTTPFetchClient
from mod_personnel_db.ftp import StandardFTPClient
from mod_personnel_db.models import PdfId
from mod_personnel_db.repositories.sqlite import connect
from mod_personnel_db.services import DefaultJobOrchestrator


def test_build_application_produces_real_application(
    initialized_settings: CompositionSettings,
) -> None:
    application = bootstrap.build_application(initialized_settings)

    assert isinstance(application, Application)
    assert application.read_pdf(PdfId(1)) is None


def test_build_fetch_client_produces_real_http_fetch_client(
    initialized_settings: CompositionSettings,
) -> None:
    del initialized_settings  # FetchClient生成は設定値に依存しない（生成順序8）
    fetch_client = bootstrap.build_fetch_client()

    assert isinstance(fetch_client, HTTPFetchClient)


def test_build_ftp_client_produces_real_standard_ftp_client(
    initialized_settings: CompositionSettings,
) -> None:
    ftp_client = bootstrap.build_ftp_client(initialized_settings)

    assert isinstance(ftp_client, StandardFTPClient)


def test_build_feature_store_produces_real_default_feature_store(
    initialized_settings: CompositionSettings,
) -> None:
    del initialized_settings  # FeatureStore生成は設定値に依存しない
    feature_store = bootstrap.build_feature_store()

    assert isinstance(feature_store, DefaultFeatureStore)


def test_build_job_orchestrator_produces_real_default_job_orchestrator(
    initialized_settings: CompositionSettings,
) -> None:
    connection = connect(initialized_settings.db_path)
    repositories = bootstrap.build_sqlite_repositories(connection)
    application = bootstrap.build_application(initialized_settings)
    fetch_client = bootstrap.build_fetch_client()
    ftp_client = bootstrap.build_ftp_client(initialized_settings)

    orchestrator = bootstrap.build_job_orchestrator(
        application, repositories, fetch_client, ftp_client
    )

    assert isinstance(orchestrator, DefaultJobOrchestrator)
    # 生成順序10の結線が正しいことを、未処理PDF・未レビュー項目が存在しない
    # 初期状態に対する呼び出しの成功（実SQLiteアクセスの往復）で確認する。
    assert orchestrator.run_pending_pipeline() == ()
    assert orchestrator.list_pending_reviews() == ()
