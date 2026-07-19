import sqlite3
from datetime import UTC, datetime

from mod_personnel_db.models import CandidateId, ReviewItem
from mod_personnel_db.repositories.sqlite.review import SqliteReviewRepository


def test_create_and_close_session(conn: sqlite3.Connection) -> None:
    repo = SqliteReviewRepository(conn)

    session_id = repo.create_session(reviewer="alice", reason="検証NGキューの確認")
    open_sessions = repo.list_open_sessions()

    assert session_id in open_sessions

    repo.close_session(session_id, "completed")

    assert session_id not in repo.list_open_sessions()


def test_add_change_and_list_changes(conn: sqlite3.Connection) -> None:
    repo = SqliteReviewRepository(conn)
    session_id = repo.create_session(reviewer="bob", reason="表記ゆれ修正")
    item = ReviewItem(
        session_id=session_id,
        target_table="candidate_records",
        target_id=CandidateId(1),
        field_name="rank",
        old_value="陸将補",
        new_value="陸将",
        change_reason="OCR誤読の訂正",
        reviewer="bob",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    repo.add_change(session_id, item)
    changes = repo.list_changes(session_id)

    assert len(changes) == 1
    assert changes[0].new_value == "陸将"
    assert changes[0].reviewer == "bob"


def test_list_changes_empty_for_unknown_session(conn: sqlite3.Connection) -> None:
    repo = SqliteReviewRepository(conn)
    session_id = repo.create_session(reviewer="carol", reason="test")

    assert repo.list_changes(session_id) == ()
