"""`PersonnelRecord`をCSV（UTF-8、BOMなし）として書き出す（ADR-0022、Phase6 Task14-3）。

入力は`PersonnelRecord`のみを扱う。`GoldRecord`は一切参照・import しない。
`to_csv_bytes()`は`export/integrity.py`（Phase6 Task14-4、ADR-0029）が
SHA-256を計算する際の出力バイト列としても共用する。
"""

import csv
import io
from collections.abc import Iterable
from pathlib import Path

from mod_personnel_db.export.tabular import TABULAR_COLUMNS, to_row
from mod_personnel_db.models import PersonnelRecord


def to_csv_bytes(records: Iterable[PersonnelRecord]) -> bytes:
    """`records`をUTF-8（BOMなし）のCSVバイト列へ変換する（`write_csv`と共通の出力）。"""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=TABULAR_COLUMNS)
    writer.writeheader()
    for record in records:
        writer.writerow(to_row(record))
    return buffer.getvalue().encode("utf-8")


def write_csv(records: Iterable[PersonnelRecord], destination: str | Path) -> None:
    """`records`をUTF-8（BOMなし）のCSVとして`destination`へ書き出す。

    列順は`export.tabular.TABULAR_COLUMNS`に従う（`write_parquet`と共通）。
    """
    Path(destination).write_bytes(to_csv_bytes(records))


__all__ = ["to_csv_bytes", "write_csv"]
