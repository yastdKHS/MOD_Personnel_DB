"""GoldRepositoryのSQLite実装。gold_records（SCD Type 2）を担当する。"""

import sqlite3
from datetime import date, datetime

from mod_personnel_db.models import CandidateId, GoldRecord, GoldRecordId, NormalizedRecord
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import (
    date_to_str,
    json_to_normalized_record,
    last_id,
    normalized_record_to_json,
    require_row,
    str_to_date,
)


def _row_to_record(row: sqlite3.Row) -> GoldRecord:
    return GoldRecord(
        id=GoldRecordId(row["id"]),
        candidate_id=CandidateId(row["candidate_record_id"]),
        person_key=row["person_key"],
        effective_date=str_to_date(row["effective_date"]),
        appointment_type=row["appointment_type"],
        fields=json_to_normalized_record(row["fields"]),
        version=row["version"],
        is_current=bool(row["is_current"]),
        superseded_by=None if row["superseded_by"] is None else GoldRecordId(row["superseded_by"]),
    )


class SqliteGoldRepository(SqliteRepositoryBase):
    def add_version(
        self,
        candidate_id: CandidateId,
        record: NormalizedRecord,
        person_key: str,
        effective_date: date,
        appointment_type: str,
    ) -> GoldRecordId:
        max_version_row = self.conn.execute(
            "SELECT MAX(version) AS max_version FROM gold_records "
            "WHERE person_key = ? AND effective_date = ?",
            (person_key, date_to_str(effective_date)),
        ).fetchone()
        next_version = (max_version_row["max_version"] or 0) + 1

        cursor = self.conn.execute(
            """
            INSERT INTO gold_records
                (candidate_record_id, person_key, effective_date, appointment_type, fields, version)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                person_key,
                date_to_str(effective_date),
                appointment_type,
                normalized_record_to_json(record),
                next_version,
            ),
        )
        self.conn.commit()
        return GoldRecordId(last_id(cursor))

    def supersede(self, old_id: GoldRecordId, new_id: GoldRecordId) -> None:
        cursor = self.conn.execute(
            "UPDATE gold_records SET is_current = 0, superseded_by = ?, "
            "valid_to = STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (new_id, old_id),
        )
        require_row(cursor.rowcount or None, f"gold_records.id={old_id} not found")
        self.conn.commit()

    def get_current(self, person_key: str, effective_date: date) -> GoldRecord | None:
        row = self.conn.execute(
            "SELECT * FROM gold_records WHERE person_key = ? AND effective_date = ? "
            "AND is_current = 1",
            (person_key, date_to_str(effective_date)),
        ).fetchone()
        return None if row is None else _row_to_record(row)

    def get_history(self, person_key: str) -> tuple[GoldRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM gold_records WHERE person_key = ? ORDER BY effective_date, version",
            (person_key,),
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)

    def list_current(self, as_of: datetime | None = None) -> tuple[GoldRecord, ...]:
        if as_of is None:
            rows = self.conn.execute(
                "SELECT * FROM gold_records WHERE is_current = 1 "
                "ORDER BY person_key, effective_date"
            ).fetchall()
        else:
            as_of_str = as_of.strftime("%Y-%m-%dT%H:%M:%SZ")
            rows = self.conn.execute(
                "SELECT * FROM gold_records WHERE valid_from <= ? "
                "AND (valid_to IS NULL OR valid_to > ?) ORDER BY person_key, effective_date",
                (as_of_str, as_of_str),
            ).fetchall()
        return tuple(_row_to_record(row) for row in rows)
