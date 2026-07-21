"""Composition Root（合成ルート）とCLIエントリポイント。
docs/api/package-design.md#cli, ADR-0046, ADR-0021に対応する。

`repositories/sqlite/`の各具象クラス・`KnowledgeService`・`LearningService`の
具象実装をimport・生成できる唯一のパッケージである
（architecture-contract.md 保証15）。依存は常にコンストラクタ注入
（Protocol型）で行い、`UnitOfWork`・Service Locator・Singleton・
グローバル可変状態・DIコンテナライブラリのいずれも用いない。

生成順序（ADR-0046、Task12-2でReview/Export生成を追加）: Repository具象生成
→ `KnowledgeService`生成 → `LearningService`生成 → `ReviewService`生成 →
`ExportService`生成 → `JobRunnerRepositories`生成 → `JobRunner`生成。

`app.py`（Task11-6）はargparseベースのCLIエントリポイントであり、
`CLI → Composition Root（bootstrap.py） → JobRunner → Pipeline`という
呼び出し方向のみを守る。CLIコマンド層（`app.py`・`commands.py`）自体は
`repositories/sqlite/`・`knowledge/`・`learning/`・`review/`・`export/`の
いずれも直接importしない。
"""

from mod_personnel_db.cli.app import main
from mod_personnel_db.cli.bootstrap import (
    Application,
    CompositionSettings,
    build_export_service,
    build_job_runner,
    build_review_service,
)
from mod_personnel_db.cli.commands import (
    VersionInfo,
    init_db_command,
    run_job_command,
    run_pending_command,
    version_command,
)
from mod_personnel_db.cli.init import initialize_database

__all__ = [
    "Application",
    "CompositionSettings",
    "VersionInfo",
    "build_export_service",
    "build_job_runner",
    "build_review_service",
    "init_db_command",
    "initialize_database",
    "main",
    "run_job_command",
    "run_pending_command",
    "version_command",
]
