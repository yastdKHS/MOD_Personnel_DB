import sqlite3
from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    CandidateId,
    ConfidenceBand,
    NormalizedRecord,
    NormalizedValue,
    ParserVersionId,
    PdfId,
    PersonnelSection,
    PersonnelSectionId,
    RawRecord,
    ValidationCandidate,
    ValidationError,
    ValidationEvidence,
    ValidationResult,
)
from mod_personnel_db.models.values import Confidence
from mod_personnel_db.repositories.sqlite.candidate import SqliteCandidateRepository
from mod_personnel_db.utils.exceptions import RepositoryError


def _make_section(pdf_id: PdfId, layout_era_id: str) -> PersonnelSection:
    return PersonnelSection(
        document_ref=pdf_id,
        layout_id=layout_era_id,
        section_index=0,
        section_label="発令一覧",
        page_range=(1, 3),
        section_text="令和8年1月1日付発令...",
    )


def test_add_and_get_section(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)

    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    fetched = repo.get_section(section_id)

    assert fetched is not None
    assert fetched.document_ref == pdf_id
    assert fetched.page_range == (1, 3)
    assert fetched.section_text.startswith("令和8年")


def test_get_section_missing_returns_none(
    conn: sqlite3.Connection, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    assert repo.get_section(PersonnelSectionId(999)) is None


def test_add_section_rejects_unknown_era_id(
    conn: sqlite3.Connection, pdf_id: PdfId, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section = _make_section(pdf_id, "no_such_era")

    with pytest.raises(RepositoryError):
        repo.add_section(section)


def test_add_raw_and_get(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_era_id,
        record_index=0,
        raw_fields={"name": "山田太郎", "rank": "陸将補"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    candidate_id = repo.add_raw(section_id, raw)
    fetched = repo.get(candidate_id)

    assert fetched is not None
    assert fetched.section_id == section_id
    assert fetched.raw.raw_fields == {"name": "山田太郎", "rank": "陸将補"}
    assert fetched.normalized is None
    assert fetched.validation_status == "pending"


def test_attach_normalized(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_era_id,
        record_index=0,
        raw_fields={"rank": "陸将補"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    candidate_id = repo.add_raw(section_id, raw)
    normalized = NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"rank": NormalizedValue(value="陸将補", raw="陸将補")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
    )

    repo.attach_normalized(candidate_id, normalized)
    fetched = repo.get(candidate_id)

    assert fetched is not None
    assert fetched.normalized is not None
    assert fetched.normalized.normalized_fields["rank"].value == "陸将補"


def test_update_validation(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_era_id,
        record_index=0,
        raw_fields={"rank": "陸将補"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    candidate_id = repo.add_raw(section_id, raw)
    candidate = ValidationCandidate(
        record_index=raw.record_index,
        score=0.9,
        errors=(),
        warnings=(),
        evidence=ValidationEvidence(
            record_index=raw.record_index, layout_id=raw.layout_id, rules_evaluated=1
        ),
    )
    result = ValidationResult(
        status="passed",
        candidates=(candidate,),
        confidence=Confidence(score=0.9, band=ConfidenceBand.HIGH),
        validated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    repo.update_validation(candidate_id, result)
    fetched = repo.get(candidate_id)

    assert fetched is not None
    assert fetched.validation_status == "passed"


def test_list_by_section_orders_by_record_index(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    for index in (1, 0):
        repo.add_raw(
            section_id,
            RawRecord(
                section_ref=None,
                layout_id=layout_era_id,
                record_index=index,
                raw_fields={"rank": "陸将補"},
                extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )

    records = repo.list_by_section(section_id)

    assert [r.raw.record_index for r in records] == [0, 1]


def test_list_pending_and_failed_validation(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_era_id,
        record_index=0,
        raw_fields={"rank": "陸将補"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    pending_id = repo.add_raw(section_id, raw)
    failed_id = repo.add_raw(
        section_id,
        RawRecord(
            section_ref=None,
            layout_id=layout_era_id,
            record_index=1,
            raw_fields={"rank": "不明"},
            extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    failed_candidate = ValidationCandidate(
        record_index=raw.record_index,
        score=0.0,
        errors=(ValidationError(rule_id="rank_known", message="未知の階級"),),
        warnings=(),
        evidence=ValidationEvidence(
            record_index=raw.record_index, layout_id=raw.layout_id, rules_evaluated=1
        ),
    )
    failed_result = ValidationResult(
        status="failed",
        candidates=(failed_candidate,),
        confidence=Confidence(score=0.2, band=ConfidenceBand.LOW),
        validated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    repo.update_validation(failed_id, failed_result)

    pending = repo.list_pending_validation()
    failed = repo.list_failed_validation()

    assert [r.id for r in pending] == [pending_id]
    assert [r.id for r in failed] == [failed_id]


def test_candidate_id_missing_returns_none(
    conn: sqlite3.Connection, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    assert repo.get(CandidateId(999)) is None
