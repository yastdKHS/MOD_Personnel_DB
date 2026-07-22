"""`PersonnelRecord`をParquet（標準的なカラム構造）として書き出す（ADR-0022、Phase6 Task14-3）。

入力は`PersonnelRecord`のみを扱う。`GoldRecord`は一切参照・import しない。
`pyarrow`（Phase6 Task14-3で追加した依存、`pyproject.toml`参照）を用いる。
`to_parquet_bytes()`は`export/integrity.py`（Phase6 Task14-4、ADR-0029）が
SHA-256を計算する際の出力バイト列としても共用する。
"""

from collections.abc import Iterable
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from mod_personnel_db.export.tabular import TABULAR_COLUMNS, to_row
from mod_personnel_db.models import PersonnelRecord

#: 列ごとの型を明示し、レコード0件時にも安定した型のテーブルを生成する。
_SCHEMA = pa.schema(
    [
        ("id", pa.string()),
        ("person_value", pa.string()),
        ("person_raw", pa.string()),
        ("rank_value", pa.string()),
        ("rank_raw", pa.string()),
        ("organization_value", pa.string()),
        ("organization_raw", pa.string()),
        ("position_value", pa.string()),
        ("position_raw", pa.string()),
        ("appointment_type", pa.string()),
        ("effective_date", pa.string()),
        ("version", pa.int64()),
        ("is_current", pa.bool_()),
        ("superseded_by", pa.string()),
        ("source_pdf_content_hash", pa.string()),
        ("source_pdf_source_url", pa.string()),
        ("source_pdf_published_date", pa.string()),
        ("parser_version", pa.string()),
        ("layout_era_id", pa.string()),
        ("confidence_score", pa.float64()),
        ("confidence_band", pa.string()),
    ]
)


def to_parquet_bytes(records: Iterable[PersonnelRecord]) -> bytes:
    """`records`を標準的なカラム構造のParquetバイト列へ変換する（`write_parquet`と共通の出力）。"""
    table = _to_table(records)
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return sink.getvalue().to_pybytes()  # type: ignore[no-any-return]


def write_parquet(records: Iterable[PersonnelRecord], destination: str | Path) -> None:
    """`records`を標準的なカラム構造のParquetとして`destination`へ書き出す。

    列順・列名は`export.tabular.TABULAR_COLUMNS`に従う（`write_csv`と共通）。
    """
    Path(destination).write_bytes(to_parquet_bytes(records))


def _to_table(records: Iterable[PersonnelRecord]) -> pa.Table:
    columns: dict[str, list[object]] = {name: [] for name in TABULAR_COLUMNS}
    for record in records:
        row = to_row(record)
        for name in TABULAR_COLUMNS:
            columns[name].append(row[name])
    return pa.table(columns, schema=_SCHEMA)


__all__ = ["to_parquet_bytes", "write_parquet"]
