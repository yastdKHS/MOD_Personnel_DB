"""ReviewRepository（簡略版）のSQLite実装。review_sessions と review_changes を担当する。"""

import sqlite3

from mod_personnel_db.models import (
    CandidateId,
    GoldRecordId,
    ReviewItem,
    ReviewItemId,
    ReviewSessionId,
)
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import last_id, str_to_dt

# review_changesテーブルはreviewer列を持たない（reviewerはreview_sessions側の属性）。
# ReviewItemモデルがreviewerを要求するため、読み取り時はJOINで補う。
_SELECT_CHANGES_WITH_REVIEWER = """
    SELECT c.*, s.reviewer AS session_reviewer
    FROM review_changes AS c
    JOIN review_sessions AS s ON s.id = c.review_session_id
"""


def _row_to_item(row: sqlite3.Row) -> ReviewItem:
    target_table = row["target_table"]
    target_id = (
        CandidateId(row["target_id"])
        if target_table == "candidate_records"
        else GoldRecordId(row["target_id"])
    )
    return ReviewItem(
        session_id=ReviewSessionId(row["review_session_id"]),
        target_table=target_table,
        target_id=target_id,
        field_name=row["field_name"],
        old_value=row["old_value"],
        new_value=row["new_value"],
        change_reason=row["change_reason"],
        reviewer=row["session_reviewer"],
        created_at=str_to_dt(row["created_at"]),
    )


class SqliteReviewRepository(SqliteRepositoryBase):
    def create_session(self, reviewer: str, reason: str) -> ReviewSessionId:
        cursor = self.conn.execute(
            "INSERT INTO review_sessions (reviewer, reason) VALUES (?, ?)",
            (reviewer, reason),
        )
        self.conn.commit()
        return ReviewSessionId(last_id(cursor))

    def close_session(self, session_id: ReviewSessionId, status: str) -> None:
        self.conn.execute(
            "UPDATE review_sessions SET status = ?, "
            "completed_at = STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (status, session_id),
        )
        self.conn.commit()

    def add_change(self, session_id: ReviewSessionId, item: ReviewItem) -> ReviewItemId:
        cursor = self.conn.execute(
            """
            INSERT INTO review_changes (review_session_id, target_table, target_id, field_name,
                                         old_value, new_value, change_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                item.target_table,
                item.target_id,
                item.field_name,
                item.old_value,
                item.new_value,
                item.change_reason,
            ),
        )
        self.conn.commit()
        return ReviewItemId(last_id(cursor))

    def list_changes(self, session_id: ReviewSessionId) -> tuple[ReviewItem, ...]:
        rows = self.conn.execute(
            f"{_SELECT_CHANGES_WITH_REVIEWER} WHERE c.review_session_id = ? ORDER BY c.id",
            (session_id,),
        ).fetchall()
        return tuple(_row_to_item(row) for row in rows)

    def list_open_sessions(self) -> tuple[ReviewSessionId, ...]:
        rows = self.conn.execute(
            "SELECT id FROM review_sessions WHERE status = 'in_progress' ORDER BY id"
        ).fetchall()
        return tuple(ReviewSessionId(row["id"]) for row in rows)
