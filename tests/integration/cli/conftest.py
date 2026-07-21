"""CLI E2E統合テスト用のfixture。

`app.main()`（CLIの公開エントリポイント）のみを経由してDBを初期化する
点が`tests/unit/cli/conftest.py`との違いである（`cli.init.initialize_database()`
を直接呼ばない）。
"""

from pathlib import Path

import pytest

from mod_personnel_db.cli import app
from mod_personnel_db.cli.bootstrap import CompositionSettings


@pytest.fixture
def settings(tmp_path: Path) -> CompositionSettings:
    db_path = tmp_path / "mod_personnel.sqlite3"
    knowledge_root = tmp_path / "knowledge"
    layouts_root = tmp_path / "layouts"
    knowledge_root.mkdir()
    layouts_root.mkdir()

    return CompositionSettings(
        db_path=str(db_path),
        knowledge_root=knowledge_root,
        layouts_root=layouts_root,
        parser_code_version="v1.0.0",
    )


def base_argv(settings: CompositionSettings) -> list[str]:
    return [
        "--db-path",
        settings.db_path,
        "--knowledge-root",
        str(settings.knowledge_root),
        "--layouts-root",
        str(settings.layouts_root),
        "--parser-code-version",
        settings.parser_code_version,
    ]


@pytest.fixture
def initialized_settings(settings: CompositionSettings) -> CompositionSettings:
    """`app.main([..., "init-db"])`（CLI公開API）経由でDBスキーマを適用済みにする。"""
    exit_code = app.main([*base_argv(settings), "init-db"])
    assert exit_code == 0
    return settings
