"""`PersonnelRecord`をJSON（UTF-8）として書き出す（ADR-0022/ADR-0029、Phase6 Task14-4）。

入力は`PersonnelRecord`のみを扱う。`GoldRecord`は一切参照・import しない。
1レコードのJSON変換自体は`export/serialization.py`の`to_json_dict()`
（Phase6 Task14-2、変更なし）へ委譲し、本モジュールは複数レコードを
JSON配列としてまとめてバイト列化する責務のみを持つ。`to_json_bytes()`は
`export/integrity.py`（Phase6 Task14-4、ADR-0029）がSHA-256を計算する
際の出力バイト列としても共用する。
"""

import json
from collections.abc import Iterable
from pathlib import Path

from mod_personnel_db.export.serialization import to_json_dict
from mod_personnel_db.models import PersonnelRecord


def to_json_bytes(records: Iterable[PersonnelRecord]) -> bytes:
    """`records`をUTF-8のJSON配列バイト列へ変換する（`write_csv`/`write_parquet`と対になる出力）。"""
    payload = [to_json_dict(record) for record in records]
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def write_json(records: Iterable[PersonnelRecord], destination: str | Path) -> None:
    """`records`をUTF-8のJSONとして`destination`へ書き出す。"""
    Path(destination).write_bytes(to_json_bytes(records))


__all__ = ["to_json_bytes", "write_json"]
