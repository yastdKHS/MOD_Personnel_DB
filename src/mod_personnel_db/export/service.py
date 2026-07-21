"""ExportServiceのGoldRepository委譲による具象実装。Phase4 Task12-1に対応する。

責務はGold Databaseからのエクスポート対象取得・呼び出し元への返却のみに
限定する。SQL・SQLite・Repository具象実装のいずれにも依存せず、
`GoldRepository`（抽象Protocol）のみへ委譲する。`RepositoryError`は
捕捉・変換せず、そのまま伝播させる。

`export_all()`/`export_since()`/`export_person()`（`GoldRecord`をそのまま
返す、Phase4 Task12-1由来）に加えて、`export_all_records()`/
`export_since_records()`/`export_person_records()`（ADR-0016の公開JSON
契約に対応する`PersonnelRecord`を返す、Phase6 Task14-2で追加）を提供する。
後者は`GoldRecord`を一切呼び出し元へ返さない、外部公開用の別APIである。
前者はCLI（`cli/commands.py`）が既に依存しているため、シグネチャ・戻り値
を変更していない。
"""

from datetime import datetime

from mod_personnel_db.export.mapper import to_personnel_record
from mod_personnel_db.models import GoldRecord, PersonnelRecord
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

    def export_all_records(self) -> tuple[PersonnelRecord, ...]:
        """現在有効なGold Record全件を、公開用`PersonnelRecord`として返す（ADR-0016）。"""
        return tuple(to_personnel_record(record) for record in self.export_all())

    def export_since_records(self, since: datetime) -> tuple[PersonnelRecord, ...]:
        """`since`時点で有効だったGold Recordを、公開用`PersonnelRecord`として返す。"""
        return tuple(to_personnel_record(record) for record in self.export_since(since))

    def export_person_records(self, person_id: str) -> tuple[PersonnelRecord, ...]:
        """指定した`person_key`の全バージョン履歴を、公開用`PersonnelRecord`として返す。"""
        return tuple(to_personnel_record(record) for record in self.export_person(person_id))


__all__ = ["RepositoryExportService"]
