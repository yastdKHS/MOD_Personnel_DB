"""テスト専用のStub KnowledgeService実装。具象実装はsrc/には置かない（Phase3 Task10-0.2）。"""

from datetime import date

from mod_personnel_db.models import KnowledgeItem, KnowledgeSnapshot, ValidationRuleSet


class StubKnowledgeService:
    """KnowledgeService Protocolを満たす、固定値を返すだけの最小限のStub。"""

    def __init__(self, snapshot: KnowledgeSnapshot, rules: ValidationRuleSet) -> None:
        self._snapshot = snapshot
        self._rules = rules

    def load_snapshot(self, as_of: date | None = None) -> KnowledgeSnapshot:
        del as_of
        return self._snapshot

    def load_validation_rules(self, as_of: date | None = None) -> ValidationRuleSet:
        del as_of
        return self._rules

    def get_item(self, category: str, item_key: str) -> KnowledgeItem | None:
        for item in self._snapshot.items:
            if item.category == category and item.item_key == item_key:
                return item
        return None

    def reload(self) -> KnowledgeSnapshot:
        return self._snapshot
