"""`DefaultFeatureStore`と実`LearningService`（SQLite永続化）との結合テスト（Phase7 Task16-2）。

`tests/unit/features/test_store.py`が`LearningService`をスタブ化して
`compute()`の呼び出し規約を検証するのに対し、本テストは実際の
`RepositoryLearningService`（`SqliteLearningRepository`、実ファイル
データベースに接続）を`DefaultFeatureStore`へ注入し、`learning/`・
`repositories/sqlite/`を跨いだ実結合の下で`learning_open_error_count`
特徴量が正しく計算されることを確認する。

`features/`パッケージ自身は`repositories/`をimportしない
（`tests/unit/features/test_dependency_ownership.py`が保証する）。
本テストファイルはテストの前提条件（Arrange）を組み立てるためだけに
`repositories.sqlite`を直接利用しており、`features/`の実行時依存グラフの
一部ではない（`tests/integration/cli/_fixtures.py`と同じ扱い）。
"""

from datetime import UTC, datetime
from pathlib import Path

from mod_personnel_db.features import DefaultFeatureStore
from mod_personnel_db.learning import RepositoryLearningService
from mod_personnel_db.models import (
    ErrorCategory,
    LearningRecord,
    LearningStatus,
    PipelineStageName,
    RawRecord,
    RegressionStatus,
)
from mod_personnel_db.repositories.sqlite import SqliteLearningRepository, apply_schema, connect


def _open_learning_record() -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.VALIDATOR,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="大将?",
        correct_value="大将",
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=None,
        layout_id=None,
        confidence=None,
        status=LearningStatus.OPEN,
        reflected_in_knowledge_item_id=None,
        reflected_in_layout_id=None,
        git_commit_hash=None,
        pull_request_url=None,
        regression_status=RegressionStatus.NOT_RUN,
        regression_run_at=None,
        regression_details=None,
        improvement_candidate=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        resolved_at=None,
    )


def test_compute_reflects_real_open_learning_record_count(tmp_path: Path) -> None:
    db_path = tmp_path / "features_integration.sqlite3"
    connection = connect(str(db_path))
    try:
        apply_schema(connection)
        repository = SqliteLearningRepository(connection)
        repository.add(_open_learning_record())
        repository.add(_open_learning_record())
        learning_service = RepositoryLearningService(repository)

        store = DefaultFeatureStore(learning_service=learning_service)
        record = RawRecord(
            section_ref=None,
            layout_id="format_a",
            record_index=0,
            raw_fields={"rank": "1佐"},
            extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

        vector = store.compute(record)

        assert vector.features["learning_open_error_count"] == 2.0
    finally:
        connection.close()
