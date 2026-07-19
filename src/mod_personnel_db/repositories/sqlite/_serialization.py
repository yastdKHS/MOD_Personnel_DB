"""モデル⇔SQLite永続化表現の変換。repositories/sqlite/ 内部専用の実装詳細。"""

import json
import sqlite3
from collections.abc import Mapping
from datetime import date, datetime

from mod_personnel_db.models import KnowledgeItemId, NormalizedRecord, NormalizedValue, RawRecord
from mod_personnel_db.utils.exceptions import RepositoryError

_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def last_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RepositoryError("INSERT did not produce a rowid")
    return cursor.lastrowid


def dt_to_str(value: datetime) -> str:
    return value.strftime(_DATETIME_FORMAT)


def str_to_dt(value: str) -> datetime:
    return datetime.strptime(value, _DATETIME_FORMAT)


def date_to_str(value: date) -> str:
    return value.isoformat()


def str_to_date(value: str) -> date:
    return date.fromisoformat(value)


def raw_fields_to_json(fields: Mapping[str, str]) -> str:
    return json.dumps(dict(fields), ensure_ascii=False)


def json_to_raw_fields(text: str) -> dict[str, str]:
    return dict(json.loads(text))


def normalized_fields_to_json(fields: Mapping[str, NormalizedValue]) -> str:
    payload = {k: {"value": v.value, "raw": v.raw} for k, v in fields.items()}
    return json.dumps(payload, ensure_ascii=False)


def json_to_normalized_fields(text: str) -> dict[str, NormalizedValue]:
    payload = json.loads(text)
    return {k: NormalizedValue(value=v["value"], raw=v["raw"]) for k, v in payload.items()}


def applied_to_json(applied: tuple[KnowledgeItemId, ...]) -> str:
    return json.dumps(list(applied))


def json_to_applied(text: str) -> tuple[KnowledgeItemId, ...]:
    return tuple(KnowledgeItemId(v) for v in json.loads(text))


def normalized_record_to_json(record: NormalizedRecord) -> str:
    raw = record.raw_record_ref
    payload = {
        "raw_record_ref": {
            "section_ref": int(raw.section_ref) if raw.section_ref is not None else None,
            "layout_id": raw.layout_id,
            "record_index": raw.record_index,
            "raw_fields": dict(raw.raw_fields),
            "extracted_at": dt_to_str(raw.extracted_at),
        },
        "normalized_fields": {
            k: {"value": v.value, "raw": v.raw} for k, v in record.normalized_fields.items()
        },
        "normalization_applied": list(record.normalization_applied),
        "normalized_at": dt_to_str(record.normalized_at),
    }
    return json.dumps(payload, ensure_ascii=False)


def json_to_normalized_record(text: str) -> NormalizedRecord:
    payload = json.loads(text)
    raw_payload = payload["raw_record_ref"]
    section_ref = raw_payload["section_ref"]
    raw = RawRecord(
        section_ref=None if section_ref is None else section_ref,
        layout_id=raw_payload["layout_id"],
        record_index=raw_payload["record_index"],
        raw_fields=raw_payload["raw_fields"],
        extracted_at=str_to_dt(raw_payload["extracted_at"]),
    )
    normalized_fields = {
        k: NormalizedValue(value=v["value"], raw=v["raw"])
        for k, v in payload["normalized_fields"].items()
    }
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields=normalized_fields,
        normalization_applied=tuple(KnowledgeItemId(v) for v in payload["normalization_applied"]),
        normalized_at=str_to_dt(payload["normalized_at"]),
    )


def require_row(row: object, message: str) -> None:
    if row is None:
        raise RepositoryError(message)
