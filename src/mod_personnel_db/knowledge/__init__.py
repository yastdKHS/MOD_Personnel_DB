"""KnowledgeService契約（Protocol）。docs/api/interfaces.md#knowledgeservice に対応する。

Phase3 Task10-0.2（契約整備のみ）の対象。Dependency Injection用の抽象型のみを
提供し、YAML読み込み・KnowledgeRepositoryへの反映を行う具象実装は含まない
（具象実装は将来のタスクでknowledge/配下に追加する、docs/api/package-design.md
のknowledge/節）。
"""

from datetime import date
from typing import Protocol

from mod_personnel_db.models import KnowledgeItem, KnowledgeSnapshot, ValidationRuleSet


class KnowledgeService(Protocol):
    """knowledge/ 配下のYAMLを読み込み、正規化・検証用のスナップショットを提供する（ADR-0005）。"""

    def load_snapshot(self, as_of: date | None = None) -> KnowledgeSnapshot: ...

    def load_validation_rules(self, as_of: date | None = None) -> ValidationRuleSet:
        """category="validation"のKnowledgeItem群を提供する（ADR-0041, ADR-0043）。"""
        ...

    def get_item(self, category: str, item_key: str) -> KnowledgeItem | None: ...

    def reload(self) -> KnowledgeSnapshot:
        """knowledge/ ディレクトリを再読み込みし、KnowledgeRepositoryへ反映する。"""
        ...


__all__ = ["KnowledgeService"]
