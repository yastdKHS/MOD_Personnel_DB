"""ExportServiceのGoldRepository委譲による具象実装。Phase4 Task12-1に対応する。

責務はGold Databaseからのエクスポート対象取得・呼び出し元への返却のみに
限定する。SQL・SQLite・Repository具象実装のいずれにも依存せず、
`GoldRepository`（抽象Protocol）のみへ委譲する。`RepositoryError`は
捕捉・変換せず、そのまま伝播させる。

`export_all()`/`export_since()`/`export_person()`（`GoldRecord`をそのまま
返す、Phase4 Task12-1由来）に加えて、`export_all_records()`/
`export_since_records()`/`export_person_records()`（ADR-0016の公開JSON
契約に対応する`PersonnelRecord`を返す、Phase6 Task14-2で追加）、
`export_all_csv()`/`export_all_parquet()`（ADR-0022のCSV/Parquet出力、
Phase6 Task14-3で追加）、`export_all_with_metadata()`/
`export_since_with_metadata()`/`export_person_with_metadata()`（ADR-0029の
完全性保証・監査情報付きエクスポート、Phase6 Task14-4で追加）を提供する。
最初の3者以外はいずれも`GoldRecord`を一切呼び出し元・出力先へ渡さない、
外部公開用の別APIである（`export_all_csv`/`export_all_parquet`/
`*_with_metadata`は内部で`export_all_records()`等が返す`PersonnelRecord`
のみを`csv_writer.py`/`parquet_writer.py`/`integrity.py`へ渡す）。
最初の3者はCLI（`cli/commands.py`）が既に依存しているため、シグネチャ・
戻り値を変更していない。
"""

from datetime import datetime
from pathlib import Path

from mod_personnel_db.export.csv_writer import write_csv
from mod_personnel_db.export.integrity import write_with_metadata
from mod_personnel_db.export.mapper import to_personnel_record
from mod_personnel_db.export.parquet_writer import write_parquet
from mod_personnel_db.models import ExportArtifact, ExportFormat, GoldRecord, PersonnelRecord
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

    def export_all_csv(self, destination: str | Path) -> None:
        """現在有効なGold Record全件を、`PersonnelRecord`としてCSVへ書き出す（ADR-0022）。"""
        write_csv(self.export_all_records(), destination)

    def export_all_parquet(self, destination: str | Path) -> None:
        """現在有効なGold Record全件を、`PersonnelRecord`としてParquetへ書き出す（ADR-0022）。"""
        write_parquet(self.export_all_records(), destination)

    def export_all_with_metadata(
        self, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        """現在有効なGold Record全件を書き出し、完全性・監査情報を返す（ADR-0029）。"""
        return write_with_metadata(self.export_all_records(), export_format, destination)

    def export_since_with_metadata(
        self, since: datetime, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        """`since`時点で有効だったGold Recordを書き出し、完全性・監査情報を返す（ADR-0029）。"""
        return write_with_metadata(self.export_since_records(since), export_format, destination)

    def export_person_with_metadata(
        self, person_id: str, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        """指定した`person_key`の全バージョン履歴を書き出し、完全性・監査情報を返す（ADR-0029）。"""
        return write_with_metadata(
            self.export_person_records(person_id), export_format, destination
        )


__all__ = ["RepositoryExportService"]
