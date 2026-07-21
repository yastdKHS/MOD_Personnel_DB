"""`KnowledgeService`のファイルベース具象実装。docs/api/interfaces.md#knowledgeserviceに対応する。

責務は`knowledge/`配下のYAML読込・`KnowledgeSnapshot`/`ValidationRuleSet`生成の
みに限定する（ADR-0044〜ADR-0046）。PipelineRunner・JobRunner・Repository・
Learning・Review・Exportのいずれにも依存しない。
"""

import hashlib
from datetime import date
from pathlib import Path

from mod_personnel_db.knowledge.loader import load_knowledge_items
from mod_personnel_db.models import KnowledgeItem, KnowledgeSnapshot, ValidationRuleSet


class FileKnowledgeService:
    """`knowledge_root`配下のYAMLファイルを読み込む`KnowledgeService`実装。

    コンストラクタでYAMLルートパスを注入するDI前提の設計であり、Singleton・
    グローバル状態は持たない。読み込んだ`KnowledgeItem`群はインスタンス変数へ
    キャッシュし、`reload()`が呼ばれるまで再読込しない。
    """

    def __init__(self, knowledge_root: Path) -> None:
        self._knowledge_root = knowledge_root
        self._items: tuple[KnowledgeItem, ...] | None = None

    def load_snapshot(self, as_of: date | None = None) -> KnowledgeSnapshot:
        effective_as_of = as_of if as_of is not None else date.today()
        items = self._effective_items(effective_as_of)
        return KnowledgeSnapshot(
            items=items,
            snapshot_checksum=_checksum(items),
            as_of=effective_as_of,
        )

    def load_validation_rules(self, as_of: date | None = None) -> ValidationRuleSet:
        effective_as_of = as_of if as_of is not None else date.today()
        rules = tuple(
            item for item in self._effective_items(effective_as_of) if item.category == "validation"
        )
        return ValidationRuleSet(rules=rules, as_of=effective_as_of)

    def get_item(self, category: str, item_key: str) -> KnowledgeItem | None:
        for item in self._ensure_loaded():
            if item.category == category and item.item_key == item_key:
                return item
        return None

    def reload(self) -> KnowledgeSnapshot:
        self._items = load_knowledge_items(self._knowledge_root)
        return self.load_snapshot()

    def _ensure_loaded(self) -> tuple[KnowledgeItem, ...]:
        if self._items is None:
            self._items = load_knowledge_items(self._knowledge_root)
        return self._items

    def _effective_items(self, as_of: date) -> tuple[KnowledgeItem, ...]:
        return tuple(item for item in self._ensure_loaded() if _is_effective(item, as_of))


def _is_effective(item: KnowledgeItem, as_of: date) -> bool:
    if item.effective_from is not None and as_of < item.effective_from:
        return False
    return not (item.effective_to is not None and as_of >= item.effective_to)


def _checksum(items: tuple[KnowledgeItem, ...]) -> str:
    digest = hashlib.sha256()
    for item in items:
        digest.update(
            f"{item.source_file}\0{item.category}\0{item.item_key}\0"
            f"{item.canonical_value}\0{item.version}\0".encode()
        )
    return digest.hexdigest()


__all__ = ["FileKnowledgeService"]
