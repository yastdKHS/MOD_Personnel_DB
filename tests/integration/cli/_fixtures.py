"""E2Eテストの前提データを用意するためのヘルパー。

ここでのRepository直接利用は、テストの「前提条件（Arrange）」を組み立てる
ためのものであり、CLIが検証対象として実際に駆動される部分（Act/Assert）
ではない。CLIの振る舞い自体は`app.main()`（公開API）のみを経由して検証する
（`tests/unit/cli/test_app.py`が既に確立した方針と同じ）。
"""

import sqlite3
import uuid
from datetime import UTC, date, datetime

from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.models import (
    CandidateId,
    ErrorCategory,
    GoldRecord,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    NormalizedRecord,
    NormalizedValue,
    PipelineStageName,
    RawRecord,
    RegressionStatus,
)
from mod_personnel_db.repositories.sqlite import (
    SqliteGoldRepository,
    SqliteLearningRepository,
    connect,
)


def _make_learning_record(status: LearningStatus) -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.VALIDATOR,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="大将?",
        # `review start`はcorrect_valueを追加のCLI引数として受け取らないため、
        # 'open'時点で既に確定している想定で前提データを用意する。
        correct_value="大将",
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=None,
        layout_id=None,
        confidence=None,
        status=status,
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


def insert_learning_record(
    settings: CompositionSettings, status: LearningStatus = LearningStatus.OPEN
) -> LearningRecordId:
    connection = connect(settings.db_path)
    try:
        return SqliteLearningRepository(connection).add(_make_learning_record(status))
    finally:
        connection.close()


def _insert_candidate_id(connection: sqlite3.Connection) -> CandidateId:
    """`gold_records.candidate_record_id`のFOREIGN KEY制約を満たす最小限の先行データ
    （parser_versions/pdfs/layouts/personnel_sections/candidate_records）を作成する。
    """
    unique = uuid.uuid4().hex
    parser_version_id = connection.execute(
        "INSERT INTO parser_versions (code_version, knowledge_snapshot_checksum) VALUES (?, ?)",
        (f"v1.0.0-test-{unique}", "c" * 64),
    ).lastrowid
    pdf_id = connection.execute(
        "INSERT INTO pdfs (content_hash, source_url, published_date, file_path, file_size_bytes) "
        "VALUES (?, 'https://example.mod.go.jp/x.pdf', '2026-01-01', ?, 1024)",
        (unique, f"bb/bb/{unique}.pdf"),
    ).lastrowid
    layout_id = connection.execute(
        "INSERT INTO layouts (era_id, manifest_path, manifest_checksum, valid_from) "
        "VALUES (?, 'layouts/reiwa/manifest.yaml', ?, '2019-05-01')",
        (f"reiwa-{unique}", "d" * 64),
    ).lastrowid
    section_id = connection.execute(
        "INSERT INTO personnel_sections "
        "(pdf_id, layout_id, parser_version_id, section_index, section_text) "
        "VALUES (?, ?, ?, 0, 'text')",
        (pdf_id, layout_id, parser_version_id),
    ).lastrowid
    candidate_id = connection.execute(
        "INSERT INTO candidate_records "
        "(personnel_section_id, parser_version_id, record_index, raw_fields) "
        'VALUES (?, ?, 0, \'{"rank": "大将?"}\')',
        (section_id, parser_version_id),
    ).lastrowid
    connection.commit()
    assert candidate_id is not None
    return CandidateId(candidate_id)


def insert_gold_record(settings: CompositionSettings, person_key: str) -> GoldRecord:
    connection = connect(settings.db_path)
    try:
        candidate_id = _insert_candidate_id(connection)
        repository = SqliteGoldRepository(connection)
        raw = RawRecord(
            section_ref=None,
            layout_id="reiwa",
            record_index=0,
            raw_fields={"rank": "大将?"},
            extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        record = NormalizedRecord(
            raw_record_ref=raw,
            normalized_fields={"rank": NormalizedValue(value="大将", raw="大将?")},
            normalization_applied=(),
            normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        record_id = repository.add_version(
            candidate_id, record, person_key, date(2026, 1, 1), "promotion"
        )
        current = repository.get_current(person_key, date(2026, 1, 1))
        assert current is not None
        assert current.id == record_id
        return current
    finally:
        connection.close()
