"""Composition Root（合成ルート）。docs/api/package-design.md#cli, ADR-0046に対応する。

`repositories/sqlite/`の各具象クラス・`KnowledgeService`・`LearningService`の
具象実装をimport・生成できる唯一のパッケージである
（architecture-contract.md 保証15）。依存は常にコンストラクタ注入
（Protocol型）で行い、`UnitOfWork`・Service Locator・Singleton・
グローバル可変状態・DIコンテナライブラリのいずれも用いない。

生成順序（ADR-0046）: Repository具象生成 → `KnowledgeService`生成 →
`LearningService`生成 → `JobRunnerRepositories`生成 → `JobRunner`生成。
"""

from mod_personnel_db.cli.bootstrap import CompositionSettings, build_job_runner
from mod_personnel_db.cli.commands import run_pending_command
from mod_personnel_db.cli.init import initialize_database

__all__ = [
    "CompositionSettings",
    "build_job_runner",
    "initialize_database",
    "run_pending_command",
]
