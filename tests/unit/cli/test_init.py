import sqlite3
from pathlib import Path

from mod_personnel_db.cli.init import initialize_database


def test_initialize_database_creates_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "mod_personnel.sqlite3"

    initialize_database(str(db_path))

    connection = sqlite3.connect(str(db_path))
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    finally:
        connection.close()

    table_names = {row[0] for row in rows}
    assert {"pdfs", "jobs", "candidate_records", "learning_dataset", "knowledge_items"}.issubset(
        table_names
    )
