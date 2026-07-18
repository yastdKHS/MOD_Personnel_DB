from pathlib import Path

from mod_personnel_db.repositories.sqlite._base import connect
from mod_personnel_db.repositories.sqlite._schema import apply_schema


def test_connect_returns_usable_connection(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"

    connection = connect(str(db_path))
    apply_schema(connection)
    row = connection.execute("PRAGMA foreign_keys").fetchone()

    assert row[0] == 1
    connection.close()
