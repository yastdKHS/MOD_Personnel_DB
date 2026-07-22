"""ExportService契約（Protocol）。Phase4 Task12-1に対応する。

Reviewで確定したGold Database（`gold_records`）のデータを外部へ出力する
ための、最小限のExport機能の契約を定める。`export_all()`/`export_since()`/
`export_person()`は`GoldRepository`から取得した`GoldRecord`をそのまま
返却する（Phase4 Task12-1由来、CLIが依存するため変更しない）。

`export_all_records()`/`export_since_records()`/`export_person_records()`
（Phase6 Task14-2で追加）は、ADR-0016（公開JSON形式）が定める外部公開
契約に対応する`PersonnelRecord`を返す。`GoldRecord`（内部モデル）を一切
呼び出し元へ返さない、外部公開用の別APIである（`export/mapper.py`の
`to_personnel_record()`が変換を担う）。出力形式（JSON文字列化・ファイル
生成・FTP転送）自体は行わない（`export/serialization.py`がJSON
シリアライズ可能な`dict`への変換のみを提供する）。

`export_all_csv()`/`export_all_parquet()`（Phase6 Task14-3で追加）は、
ADR-0022が定めるCSV/Parquetファイルとして`export_all_records()`の結果を
書き出す。両者とも入力・出力先の変換は`export/csv_writer.py`/
`export/parquet_writer.py`（`export/tabular.py`を共通利用）が担い、
`GoldRecord`を一切参照しない。

`export_all_with_metadata()`/`export_since_with_metadata()`/
`export_person_with_metadata()`（Phase6 Task14-4で追加）は、ADR-0029が
定める完全性保証・監査情報を伴うエクスポートAPIである。`format`
（`"json"`/`"csv"`/`"parquet"`）を指定して`destination`へ書き出しつつ、
実際に書き出したバイト列から計算したSHA-256等を含む`ExportArtifact`
（`export_id`/`exported_at`（UTC）/`format`/`record_count`/`sha256`）を
返す。完全性情報の計算自体は`export/integrity.py`が担い、`GoldRecord`を
一切参照しない。既存の`export_all_csv()`等・`export_all_records()`等の
シグネチャ・戻り値は変更していない。

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
from pathlib import Path
from typing import Protocol

from mod_personnel_db.models import ExportArtifact, ExportFormat, GoldRecord, PersonnelRecord


class ExportService(Protocol):
    """Gold Databaseのデータを外部出力向けに取得する。

    Phase4 Task12-1、Phase6 Task14-2/14-3/14-4に対応する。
    """

    def export_all(self) -> tuple[GoldRecord, ...]:
        """現在有効な（`is_current=True`）Gold Record全件を返す。"""
        ...

    def export_since(self, since: datetime) -> tuple[GoldRecord, ...]:
        """`since`時点で有効だったGold Recordを返す。"""
        ...

    def export_person(self, person_id: str) -> tuple[GoldRecord, ...]:
        """指定した`person_key`の全バージョン履歴を返す。"""
        ...

    def export_all_records(self) -> tuple[PersonnelRecord, ...]:
        """現在有効なGold Record全件を、公開用`PersonnelRecord`として返す（ADR-0016）。"""
        ...

    def export_since_records(self, since: datetime) -> tuple[PersonnelRecord, ...]:
        """`since`時点で有効だったGold Recordを、公開用`PersonnelRecord`として返す。"""
        ...

    def export_person_records(self, person_id: str) -> tuple[PersonnelRecord, ...]:
        """指定した`person_key`の全バージョン履歴を、公開用`PersonnelRecord`として返す。"""
        ...

    def export_all_csv(self, destination: str | Path) -> None:
        """現在有効なGold Record全件を、`PersonnelRecord`としてCSVへ書き出す（ADR-0022）。"""
        ...

    def export_all_parquet(self, destination: str | Path) -> None:
        """現在有効なGold Record全件を、`PersonnelRecord`としてParquetへ書き出す（ADR-0022）。"""
        ...

    def export_all_with_metadata(
        self, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        """現在有効なGold Record全件を`export_format`で書き出し、完全性・監査情報を返す。

        ADR-0029が定めるSHA-256等の完全性・監査情報（`ExportArtifact`）を返す。
        """
        ...

    def export_since_with_metadata(
        self, since: datetime, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        """`since`時点で有効だったGold Recordを`export_format`で書き出し、監査情報を返す。"""
        ...

    def export_person_with_metadata(
        self, person_id: str, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        """指定した`person_key`の全バージョン履歴を`export_format`で書き出し、完全性・監査情報を返す。"""
        ...


__all__ = ["ExportService"]
