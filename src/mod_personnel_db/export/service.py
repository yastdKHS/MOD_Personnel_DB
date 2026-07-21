"""ExportServiceのGoldRepository委譲による具象実装。Phase4 Task12-1に対応する。

責務はGold Databaseからのエクスポート対象取得・呼び出し元への返却のみに
限定する。SQL・SQLite・Repository具象実装のいずれにも依存せず、
`GoldRepository`（抽象Protocol）のみへ委譲する。`RepositoryError`は
捕捉・変換せず、そのまま伝播させる。
"""

from datetime import datetime

from mod_personnel_db.models import GoldRecord
from mod_personnel_db.repositories import GoldRepository


class RepositoryExportService:
    """`GoldRepository`へ委譲する`ExportService`実装。"""

    def __init__(self, gold_repository: GoldRepository) -> None:
        self._gold_repository = gold_repository

    def export_all(self) -> tuple[GoldRecord, ...]:
        return self._gold_repository.list_current()

    def export_since(self, since: datetime) -> tuple[GoldRecord, ...]:
        return self._gold_repository.list_current(as_of=since)

    def export_person(self, person_id: str) -> tuple[GoldRecord, ...]:
        return self._gold_repository.get_history(person_id)


__all__ = ["RepositoryExportService"]
