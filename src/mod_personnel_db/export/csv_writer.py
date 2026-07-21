"""`PersonnelRecord`をCSV（UTF-8、BOMなし）として書き出す（ADR-0022、Phase6 Task14-3）。

入力は`PersonnelRecord`のみを扱う。`GoldRecord`は一切参照・import しない。
"""

import csv
from collections.abc import Iterable
from pathlib import Path

from mod_personnel_db.export.tabular import TABULAR_COLUMNS, to_row
from mod_personnel_db.models import PersonnelRecord


def write_csv(records: Iterable[PersonnelRecord], destination: str | Path) -> None:
    """`records`をUTF-8（BOMなし）のCSVとして`destination`へ書き出す。

    列順は`export.tabular.TABULAR_COLUMNS`に従う（`write_parquet`と共通）。
    """
    with open(destination, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TABULAR_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(to_row(record))


__all__ = ["write_csv"]
