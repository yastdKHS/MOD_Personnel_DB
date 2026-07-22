"""公開エクスポート記録モデル。docs/api/models.md#exportrecord に対応する。

`PersonnelRecord`/`Provenance`/`SourcePdf`はADR-0016（公開JSON形式）・
docs/database/json_schema.md が定める外部公開契約に対応する（Phase6
Task14-2）。`GoldRecord`（内部モデル）を外部の利用者へ直接渡さないための
境界であり、`export/mapper.py`が`GoldRecord`からの変換を担う。

現在の`RepositoryExportService`は`GoldRepository`のみに依存し、PDF・
ParserVersionを参照するRepositoryを持たないため、`docs/database/
json_schema.md`が要求する全項目のうち、現在のデータから実装可能な範囲
にとどめている（詳細は各フィールドのdocstring・`export/mapper.py`参照）。
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from mod_personnel_db.models.candidate import NormalizedValue
from mod_personnel_db.models.ids import ExportId
from mod_personnel_db.models.values import Confidence, ModelValidationError

ExportFormat = Literal["csv", "parquet", "json"]
ExportStatus = Literal["completed", "failed"]


@dataclass(frozen=True, slots=True)
class ExportRecord:
    id: ExportId | None
    format: ExportFormat
    destination: str
    as_of: datetime
    record_count: int
    checksum: str
    status: ExportStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if self.record_count < 0:
            raise ModelValidationError("record_count must be >= 0")
        if self.status == "completed" and self.checksum == "":
            raise ModelValidationError("checksum must not be empty when status='completed'")


@dataclass(frozen=True, slots=True)
class SourcePdf:
    """根拠となった発令PDFの情報（ADR-0006）。json_schema.md#sourcepdf に対応する。"""

    content_hash: str
    source_url: str
    published_date: date

    def __post_init__(self) -> None:
        if self.content_hash == "":
            raise ModelValidationError("content_hash must not be empty")
        if self.source_url == "":
            raise ModelValidationError("source_url must not be empty")


@dataclass(frozen=True, slots=True)
class Provenance:
    """公開レコードの来歴（ADR-0006, ADR-0016）。json_schema.md#provenance に対応する。

    `source_pdf`・`parser_version`はjson_schema.md上は必須項目だが、これらを
    導出するには`PDFRepository`・`JobRepository`（ParserVersion参照）への
    アクセスが必要であり、現在の`RepositoryExportService`は`GoldRepository`
    のみに依存する（Composition Root・Repository構成は本Taskの対象外）ため
    導出できない。実装可能な範囲として`None`を許容する。`layout_era_id`は
    `GoldRecord.fields.raw_record_ref.layout_id`から導出可能なため実装済み。
    """

    source_pdf: SourcePdf | None
    parser_version: str | None
    layout_era_id: str | None


@dataclass(frozen=True, slots=True)
class PersonnelRecord:
    """外部公開用の1発令レコード（ADR-0016）。json_schema.md#personnelrecord に対応する。

    `GoldRecord`（内部モデル）を外部の利用者へ直接渡さないための境界。
    `export/mapper.py`の`to_personnel_record()`が`GoldRecord`から変換する。

    `rank`/`organization`/`position`は、現在のNormalizer実装が意味的
    フィールド名へのリネームを行わない仕様（`models/normalization.py`の
    `NormalizedField`docstring参照）であるため、`GoldRecord`の正規化済み
    フィールドから確実に解決できるとは限らず、解決できない場合は`None`と
    なる（詳細は`export/mapper.py`参照）。
    """

    id: str
    person: NormalizedValue
    rank: NormalizedValue | None
    organization: NormalizedValue | None
    position: NormalizedValue | None
    appointment_type: str
    effective_date: date
    version: int
    is_current: bool
    superseded_by: str | None
    provenance: Provenance
    confidence: Confidence

    def __post_init__(self) -> None:
        if self.id == "":
            raise ModelValidationError("id must not be empty")
        if self.appointment_type == "":
            raise ModelValidationError("appointment_type must not be empty")
        if self.version < 1:
            raise ModelValidationError("version must be >= 1")


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    """公開エクスポート成果物の完全性・監査情報（ADR-0029、Phase6 Task14-4）。

    `exports`テーブル（`ExportRecord`、`ExportRepository`経由での永続化）とは
    独立した値オブジェクトであり、DBへの永続化は行わない。`ExportService`の
    `export_all_with_metadata()`等が、実際に出力したバイト列（JSON/CSV/
    Parquet）に対してその場でSHA-256を計算し返す（`export/integrity.py`
    参照）。フォーマットが異なればバイト表現も異なるため、`sha256`は
    フォーマットごとに異なる値になる（同一フォーマット・同一内容であれば
    同一の`sha256`になることを保証する）。
    """

    export_id: str
    exported_at: datetime
    format: ExportFormat
    record_count: int
    sha256: str

    def __post_init__(self) -> None:
        if self.export_id == "":
            raise ModelValidationError("export_id must not be empty")
        if self.exported_at.tzinfo is None or self.exported_at.utcoffset() != timedelta(0):
            raise ModelValidationError("exported_at must be UTC (timezone-aware, offset zero)")
        if self.record_count < 0:
            raise ModelValidationError("record_count must be >= 0")
        if self.sha256 == "":
            raise ModelValidationError("sha256 must not be empty")
