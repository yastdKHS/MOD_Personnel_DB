"""Export成果物の完全性・監査情報（`ExportArtifact`）を計算する（ADR-0029、Phase6 Task14-4）。

JSON/CSV/Parquetいずれも、実際に`destination`へ書き出すバイト列そのものから
SHA-256を計算する（`export_id`はSHA-256計算のたびに新規採番するUUID、
`exported_at`は計算時点のUTC時刻）。フォーマットが異なれば同一内容でも
バイト表現（区切り文字・エンコード・バイナリ構造等）が異なるため、
`sha256`はフォーマットごとに異なる値になる（同一フォーマット・同一内容
であれば同一の`sha256`になることを保証する）。`GoldRecord`は一切参照しない。
"""

import hashlib
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

from mod_personnel_db.export.csv_writer import to_csv_bytes
from mod_personnel_db.export.json_writer import to_json_bytes
from mod_personnel_db.export.parquet_writer import to_parquet_bytes
from mod_personnel_db.models import ExportArtifact, ExportFormat, PersonnelRecord

_Encoder = Callable[[tuple[PersonnelRecord, ...]], bytes]

_ENCODERS: dict[ExportFormat, _Encoder] = {
    "csv": to_csv_bytes,
    "parquet": to_parquet_bytes,
    "json": to_json_bytes,
}


def build_artifact(data: bytes, export_format: ExportFormat, record_count: int) -> ExportArtifact:
    """出力バイト列`data`からSHA-256を計算し、完全性・監査情報`ExportArtifact`を作る。"""
    return ExportArtifact(
        export_id=str(uuid.uuid4()),
        exported_at=datetime.now(UTC),
        format=export_format,
        record_count=record_count,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def write_with_metadata(
    records: Iterable[PersonnelRecord], export_format: ExportFormat, destination: str | Path
) -> ExportArtifact:
    """`records`を`export_format`で`destination`へ書き出し、完全性・監査情報を返す。"""
    records_tuple = tuple(records)
    data = _ENCODERS[export_format](records_tuple)
    Path(destination).write_bytes(data)
    return build_artifact(data, export_format, len(records_tuple))


__all__ = ["build_artifact", "write_with_metadata"]
