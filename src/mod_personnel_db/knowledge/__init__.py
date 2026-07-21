"""KnowledgeService契約（Protocol）と具象実装。docs/api/interfaces.md#knowledgeservice に対応する。

Dependency Injection用の抽象型（`KnowledgeService` Protocol）に加え、
`knowledge/`配下のYAMLを読み込むファイルベースの具象実装（`FileKnowledgeService`）
を提供する（docs/api/package-design.md のknowledge/節）。具象実装の生成は
Composition Root（`cli/`、ADR-0046）にのみ許可される。
"""

from datetime import date
from typing import Protocol

from mod_personnel_db.knowledge.service import FileKnowledgeService
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


__all__ = ["FileKnowledgeService", "KnowledgeService"]
