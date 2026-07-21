"""ExportService契約（Protocol）。Phase4 Task12-1に対応する。

Reviewで確定したGold Database（`gold_records`）のデータを外部へ出力する
ための、最小限のExport機能の契約を定める。`GoldRepository`から取得した
`GoldRecord`をそのまま返却するのみであり、出力形式（JSON/CSV/Parquet等）
への変換・ファイル生成・FTP転送は行わない。

`docs/api/interfaces.md#exportservice`が定める`ExportService`（`generate()`/
`get()`/`list_recent()`、`ExportRepository`が管理する`ExportRecord`＝
エクスポート実行記録を対象とする）とは異なる、Gold Database読み出しに
特化した別の契約である。両者の統合・命名の整理は将来のADRに委ねる
（詳細はPhase4 Task12-1 Review Reportを参照。Task12-0の`ReviewService`と
`docs/api/review.md`の関係も同様の整理を行っている）。

具象実装（`RepositoryExportService`）は`mod_personnel_db.export.service`
から直接importする。本ファイルからは再エクスポートしない
（`review/__init__.py`と同じ、`service.py`との循環参照回避のため）。
"""

from datetime import datetime
from typing import Protocol

from mod_personnel_db.models import GoldRecord


class ExportService(Protocol):
    """Gold Databaseのデータを外部出力向けに取得する（Phase4 Task12-1）。"""

    def export_all(self) -> tuple[GoldRecord, ...]:
        """現在有効な（`is_current=True`）Gold Record全件を返す。"""
        ...

    def export_since(self, since: datetime) -> tuple[GoldRecord, ...]:
        """`since`時点で有効だったGold Recordを返す。"""
        ...

    def export_person(self, person_id: str) -> tuple[GoldRecord, ...]:
        """指定した`person_key`の全バージョン履歴を返す。"""
        ...


__all__ = ["ExportService"]
