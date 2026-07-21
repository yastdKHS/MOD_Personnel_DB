from pathlib import Path

import pytest

from mod_personnel_db.cli.bootstrap import CompositionSettings
from mod_personnel_db.cli.init import initialize_database


@pytest.fixture
def settings(tmp_path: Path) -> CompositionSettings:
    db_path = tmp_path / "mod_personnel.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    layouts_root = tmp_path / "layouts"
    knowledge_root.mkdir()
    layouts_root.mkdir()

    initialize_database(str(db_path))

    return CompositionSettings(
        db_path=str(db_path),
        knowledge_root=knowledge_root,
        layouts_root=layouts_root,
        parser_code_version="v1.0.0",
    )
