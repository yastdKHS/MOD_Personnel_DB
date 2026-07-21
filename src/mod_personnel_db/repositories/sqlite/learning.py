"""LearningRepositoryのSQLite実装。learning_dataset を担当する。"""

import sqlite3
from datetime import datetime

from mod_personnel_db.models import (
    CandidateId,
    Confidence,
    ConfidenceBand,
    ErrorCategory,
    KnowledgeItemId,
    LayoutId,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    ParserVersionId,
    PipelineStageName,
    RegressionStatus,
    ReviewItemId,
)
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import dt_to_str, last_id, str_to_dt
from mod_personnel_db.utils.exceptions import RepositoryError

_COLUMN_BY_FIELD: dict[str, str] = {
    "source_candidate_id": "source_candidate_record_id",
    "source_review_item_id": "source_review_change_id",
    "pipeline_stage": "pipeline_stage",
    "error_category": "error_category",
    "field_name": "field_name",
    "wrong_value": "wrong_value",
    "correct_value": "correct_value",
    "correction_summary": "correction_summary",
    "reviewer_comment": "reviewer_comment",
    "parser_version_id": "parser_version_id",
    "layout_id": "layout_id",
    "status": "status",
    "reflected_in_knowledge_item_id": "reflected_in_knowledge_item_id",
    "reflected_in_layout_id": "reflected_in_layout_id",
    "git_commit_hash": "git_commit_hash",
    "pull_request_url": "pull_request_url",
    "regression_status": "regression_status",
    "regression_run_at": "regression_run_at",
    "regression_details": "regression_details",
    "improvement_candidate": "improvement_candidate",
    "resolved_at": "resolved_at",
}
_DATETIME_FIELDS = frozenset({"regression_run_at", "resolved_at"})


def _split_confidence(confidence: Confidence | None) -> tuple[float | None, str | None]:
    if confidence is None:
        return None, None
    return confidence.score, str(confidence.band)


def _record_to_params(record: LearningRecord) -> tuple[object, ...]:
    confidence_score, confidence_band = _split_confidence(record.confidence)
    return (
        record.source_candidate_id,
        record.source_review_item_id,
        str(record.pipeline_stage),
        str(record.error_category),
        record.field_name,
        record.wrong_value,
        record.correct_value,
        record.correction_summary,
        record.reviewer_comment,
        record.parser_version_id,
        record.layout_id,
        confidence_score,
        confidence_band,
        str(record.status),
        record.reflected_in_knowledge_item_id,
        record.reflected_in_layout_id,
        record.git_commit_hash,
        record.pull_request_url,
        str(record.regression_status),
        None if record.regression_run_at is None else dt_to_str(record.regression_run_at),
        record.regression_details,
        record.improvement_candidate,
        dt_to_str(record.created_at),
        None if record.resolved_at is None else dt_to_str(record.resolved_at),
    )


def _row_to_confidence(row: sqlite3.Row) -> Confidence | None:
    if row["confidence_score"] is None:
        return None
    return Confidence(score=row["confidence_score"], band=ConfidenceBand(row["confidence_band"]))


def _row_to_record(row: sqlite3.Row) -> LearningRecord:
    return LearningRecord(
        id=LearningRecordId(row["id"]),
        source_candidate_id=(
            None
            if row["source_candidate_record_id"] is None
            else CandidateId(row["source_candidate_record_id"])
        ),
        source_review_item_id=(
            None
            if row["source_review_change_id"] is None
            else ReviewItemId(row["source_review_change_id"])
        ),
        pipeline_stage=PipelineStageName(row["pipeline_stage"]),
        error_category=ErrorCategory(row["error_category"]),
        field_name=row["field_name"],
        wrong_value=row["wrong_value"],
        correct_value=row["correct_value"],
        correction_summary=row["correction_summary"],
        reviewer_comment=row["reviewer_comment"],
        parser_version_id=(
            None if row["parser_version_id"] is None else ParserVersionId(row["parser_version_id"])
        ),
        layout_id=None if row["layout_id"] is None else LayoutId(row["layout_id"]),
        confidence=_row_to_confidence(row),
        status=LearningStatus(row["status"]),
        reflected_in_knowledge_item_id=(
            None
            if row["reflected_in_knowledge_item_id"] is None
            else KnowledgeItemId(row["reflected_in_knowledge_item_id"])
        ),
        reflected_in_layout_id=(
            None
            if row["reflected_in_layout_id"] is None
            else LayoutId(row["reflected_in_layout_id"])
        ),
        git_commit_hash=row["git_commit_hash"],
        pull_request_url=row["pull_request_url"],
        regression_status=RegressionStatus(row["regression_status"]),
        regression_run_at=(
            None if row["regression_run_at"] is None else str_to_dt(row["regression_run_at"])
        ),
        regression_details=row["regression_details"],
        improvement_candidate=row["improvement_candidate"],
        created_at=str_to_dt(row["created_at"]),
        resolved_at=None if row["resolved_at"] is None else str_to_dt(row["resolved_at"]),
    )


def _confidence_assignments(value: object) -> list[tuple[str, object]]:
    if value is None:
        return [("confidence_score", None), ("confidence_band", None)]
    if not isinstance(value, Confidence):
        raise RepositoryError(f"field 'confidence' must be Confidence or None, got {type(value)!r}")
    return [("confidence_score", value.score), ("confidence_band", str(value.band))]


def _serialize_value(name: str, value: object) -> object:
    if value is None:
        return None
    if name in _DATETIME_FIELDS:
        if not isinstance(value, datetime):
            raise RepositoryError(f"field {name!r} must be datetime or None, got {type(value)!r}")
        return dt_to_str(value)
    return value


def _build_assignments(fields: dict[str, object]) -> list[tuple[str, object]]:
    assignments: list[tuple[str, object]] = []
    for name, value in fields.items():
        if name == "confidence":
            assignments.extend(_confidence_assignments(value))
            continue
        if name not in _COLUMN_BY_FIELD:
            raise RepositoryError(f"unknown LearningRecord field: {name!r}")
        assignments.append((_COLUMN_BY_FIELD[name], _serialize_value(name, value)))
    return assignments


class SqliteLearningRepository(SqliteRepositoryBase):
    def add(self, record: LearningRecord) -> LearningRecordId:
        cursor = self.conn.execute(
            """
            INSERT INTO learning_dataset (
                source_candidate_record_id, source_review_change_id, pipeline_stage,
                error_category, field_name, wrong_value, correct_value, correction_summary,
                reviewer_comment, parser_version_id, layout_id, confidence_score,
                confidence_band, status, reflected_in_knowledge_item_id,
                reflected_in_layout_id, git_commit_hash, pull_request_url,
                regression_status, regression_run_at, regression_details,
                improvement_candidate, created_at, resolved_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _record_to_params(record),
        )
        self.conn.commit()
        return LearningRecordId(last_id(cursor))

    def update(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        assignments = _build_assignments(fields)
        if assignments:
            set_clause = ", ".join(f"{column} = ?" for column, _ in assignments)
            params = tuple(value for _, value in assignments)
            cursor = self.conn.execute(
                f"UPDATE learning_dataset SET {set_clause} WHERE id = ?",
                (*params, record_id),
            )
            if cursor.rowcount == 0:
                raise RepositoryError(f"learning_dataset.id={record_id} not found")
            self.conn.commit()
        updated = self.get(record_id)
        if updated is None:
            raise RepositoryError(f"learning_dataset.id={record_id} not found")
        return updated

    def get(self, record_id: LearningRecordId) -> LearningRecord | None:
        row = self.conn.execute(
            "SELECT * FROM learning_dataset WHERE id = ?", (record_id,)
        ).fetchone()
        return None if row is None else _row_to_record(row)

    def list_by_status(self, status: LearningStatus) -> tuple[LearningRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM learning_dataset WHERE status = ? ORDER BY id", (str(status),)
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)

    def list_by_error_category(self, category: str) -> tuple[LearningRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM learning_dataset WHERE error_category = ? ORDER BY id", (category,)
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)

    def list_by_parser_version(
        self, parser_version_id: ParserVersionId
    ) -> tuple[LearningRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM learning_dataset WHERE parser_version_id = ? ORDER BY id",
            (parser_version_id,),
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)
