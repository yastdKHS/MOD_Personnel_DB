"""CandidateRepositoryのSQLite実装。personnel_sections と candidate_records を担当する。

PersonnelSection.add_section()呼び出し時に必要なparser_version_idは、
docs/api/repositories.mdの設計メモが「呼び出し文脈から付与される」とする
値であり、Protocolの引数には現れない。pipeline/（PipelineContext）が
未実装の現時点では、Repositoryインスタンスの生成時に束縛する。

PersonnelSection.layout_id（str、era_id）とpersonnel_sections.layout_id
（INTEGER、layouts.idへのFK）の解決はADR-0037により本Repositoryが担う
（Section ParserはRepositoryにアクセスしないため、era_idのみを保持する）。
"""

import json
import sqlite3

from mod_personnel_db.models import (
    CandidateId,
    CandidateRecord,
    KnowledgeItemId,
    NormalizedRecord,
    ParserVersionId,
    PdfId,
    PersonnelSection,
    PersonnelSectionId,
    RawRecord,
    ValidationResult,
)
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import (
    json_to_normalized_fields,
    last_id,
    normalized_fields_to_json,
    raw_fields_to_json,
    str_to_dt,
)
from mod_personnel_db.utils.exceptions import RepositoryError


def _row_to_section(row: sqlite3.Row) -> PersonnelSection:
    start, end = json.loads(row["page_range"])
    return PersonnelSection(
        document_ref=PdfId(row["pdf_id"]),
        layout_id=row["era_id"],
        section_index=row["section_index"],
        section_label=row["section_label"],
        page_range=(start, end),
        section_text=row["section_text"],
    )


def _resolve_layout_id(conn: sqlite3.Connection, era_id: str) -> int:
    row = conn.execute(
        """
        SELECT id FROM layouts
        WHERE era_id = ? AND status = 'active'
        ORDER BY version DESC LIMIT 1
        """,
        (era_id,),
    ).fetchone()
    if row is None:
        raise RepositoryError(f"no active layout found for era_id={era_id!r}")
    return int(row["id"])


def _row_to_candidate(row: sqlite3.Row) -> CandidateRecord:
    raw = RawRecord(
        section_ref=PersonnelSectionId(row["personnel_section_id"]),
        record_index=row["record_index"],
        raw_fields=json.loads(row["raw_fields"]),
        extracted_at=str_to_dt(row["created_at"]),
    )
    normalized: NormalizedRecord | None = None
    if row["normalized_fields"] is not None:
        applied_ids = tuple(
            KnowledgeItemId(v) for v in json.loads(row["normalization_applied"] or "[]")
        )
        normalized = NormalizedRecord(
            raw_record_ref=raw,
            normalized_fields=json_to_normalized_fields(row["normalized_fields"]),
            normalization_applied=applied_ids,
            normalized_at=str_to_dt(row["created_at"]),
        )
    return CandidateRecord(
        id=CandidateId(row["id"]),
        section_id=PersonnelSectionId(row["personnel_section_id"]),
        raw=raw,
        normalized=normalized,
        validation_status=row["validation_status"],
    )


class SqliteCandidateRepository(SqliteRepositoryBase):
    def __init__(self, connection: sqlite3.Connection, parser_version_id: ParserVersionId) -> None:
        super().__init__(connection)
        self._parser_version_id = parser_version_id

    def add_section(self, section: PersonnelSection) -> PersonnelSectionId:
        layout_id = _resolve_layout_id(self.conn, section.layout_id)
        cursor = self.conn.execute(
            """
            INSERT INTO personnel_sections
                (pdf_id, layout_id, parser_version_id, section_index, section_label,
                 page_range, section_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                section.document_ref,
                layout_id,
                self._parser_version_id,
                section.section_index,
                section.section_label,
                json.dumps(list(section.page_range)),
                section.section_text,
            ),
        )
        self.conn.commit()
        return PersonnelSectionId(last_id(cursor))

    def get_section(self, section_id: PersonnelSectionId) -> PersonnelSection | None:
        row = self.conn.execute(
            """
            SELECT ps.*, l.era_id AS era_id
            FROM personnel_sections ps
            JOIN layouts l ON l.id = ps.layout_id
            WHERE ps.id = ?
            """,
            (section_id,),
        ).fetchone()
        return None if row is None else _row_to_section(row)

    def add_raw(self, section_id: PersonnelSectionId, record: RawRecord) -> CandidateId:
        cursor = self.conn.execute(
            """
            INSERT INTO candidate_records
                (personnel_section_id, parser_version_id, record_index, raw_fields)
            VALUES (?, ?, ?, ?)
            """,
            (
                section_id,
                self._parser_version_id,
                record.record_index,
                raw_fields_to_json(record.raw_fields),
            ),
        )
        self.conn.commit()
        return CandidateId(last_id(cursor))

    def attach_normalized(self, candidate_id: CandidateId, normalized: NormalizedRecord) -> None:
        self.conn.execute(
            "UPDATE candidate_records SET normalized_fields = ?, normalization_applied = ? "
            "WHERE id = ?",
            (
                normalized_fields_to_json(normalized.normalized_fields),
                json.dumps([int(i) for i in normalized.normalization_applied]),
                candidate_id,
            ),
        )
        self.conn.commit()

    def update_validation(self, candidate_id: CandidateId, result: ValidationResult) -> None:
        self.conn.execute(
            "UPDATE candidate_records SET validation_status = ? WHERE id = ?",
            (result.status, candidate_id),
        )
        self.conn.commit()

    def get(self, candidate_id: CandidateId) -> CandidateRecord | None:
        row = self.conn.execute(
            "SELECT * FROM candidate_records WHERE id = ?", (candidate_id,)
        ).fetchone()
        return None if row is None else _row_to_candidate(row)

    def list_by_section(self, section_id: PersonnelSectionId) -> tuple[CandidateRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM candidate_records WHERE personnel_section_id = ? ORDER BY record_index",
            (section_id,),
        ).fetchall()
        return tuple(_row_to_candidate(row) for row in rows)

    def list_pending_validation(self) -> tuple[CandidateRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM candidate_records WHERE validation_status = 'pending' ORDER BY id"
        ).fetchall()
        return tuple(_row_to_candidate(row) for row in rows)

    def list_failed_validation(self) -> tuple[CandidateRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM candidate_records WHERE validation_status = 'failed' ORDER BY id"
        ).fetchall()
        return tuple(_row_to_candidate(row) for row in rows)
