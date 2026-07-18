import sqlite3
from datetime import UTC, date, datetime

from mod_personnel_db.models import (
    CandidateId,
    LayoutId,
    NormalizedRecord,
    NormalizedValue,
    ParserVersionId,
    PdfId,
    PersonnelSection,
    RawRecord,
)
from mod_personnel_db.repositories.sqlite.candidate import SqliteCandidateRepository
from mod_personnel_db.repositories.sqlite.gold import SqliteGoldRepository


def _make_candidate(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_id: LayoutId, parser_version_id: ParserVersionId
) -> tuple[CandidateId, NormalizedRecord]:
    candidate_repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = candidate_repo.add_section(
        PersonnelSection(
            document_ref=pdf_id,
            layout_id=layout_id,
            section_index=0,
            section_label=None,
            page_range=(1, 1),
            section_text="発令",
        )
    )
    raw = RawRecord(
        section_ref=None,
        record_index=0,
        raw_fields={"rank": "陸将補"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    candidate_id = candidate_repo.add_raw(section_id, raw)
    normalized = NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"rank": NormalizedValue(value="陸将補", raw="陸将補")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return candidate_id, normalized


def test_add_version_and_get_current(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_id: LayoutId, parser_version_id: ParserVersionId
) -> None:
    candidate_id, normalized = _make_candidate(conn, pdf_id, layout_id, parser_version_id)
    repo = SqliteGoldRepository(conn)

    gold_id = repo.add_version(
        candidate_id,
        normalized,
        person_key="yamada-taro",
        effective_date=date(2026, 4, 1),
        appointment_type="補職",
    )

    current = repo.get_current("yamada-taro", date(2026, 4, 1))

    assert current is not None
    assert current.id == gold_id
    assert current.version == 1
    assert current.is_current is True
    assert current.fields.normalized_fields["rank"].value == "陸将補"


def test_get_current_missing_returns_none(conn: sqlite3.Connection) -> None:
    repo = SqliteGoldRepository(conn)
    assert repo.get_current("nobody", date(2026, 1, 1)) is None


def test_supersede_creates_scd_type_2_history(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_id: LayoutId, parser_version_id: ParserVersionId
) -> None:
    candidate_id, normalized = _make_candidate(conn, pdf_id, layout_id, parser_version_id)
    repo = SqliteGoldRepository(conn)
    old_id = repo.add_version(candidate_id, normalized, "yamada-taro", date(2026, 4, 1), "補職")
    corrected = NormalizedRecord(
        raw_record_ref=normalized.raw_record_ref,
        normalized_fields={"rank": NormalizedValue(value="陸将", raw="陸将")},
        normalization_applied=(),
        normalized_at=datetime(2026, 4, 2, tzinfo=UTC),
    )
    new_id = repo.add_version(candidate_id, corrected, "yamada-taro", date(2026, 4, 1), "補職")

    repo.supersede(old_id, new_id)

    history = repo.get_history("yamada-taro")
    current = repo.get_current("yamada-taro", date(2026, 4, 1))

    assert [r.version for r in history] == [1, 2]
    old_record = next(r for r in history if r.id == old_id)
    assert old_record.is_current is False
    assert old_record.superseded_by == new_id
    assert current is not None
    assert current.id == new_id


def test_supersede_missing_old_id_raises(conn: sqlite3.Connection) -> None:
    from mod_personnel_db.models import GoldRecordId
    from mod_personnel_db.utils.exceptions import RepositoryError

    repo = SqliteGoldRepository(conn)
    try:
        repo.supersede(GoldRecordId(999), GoldRecordId(1000))
    except RepositoryError:
        return
    raise AssertionError("expected RepositoryError for missing old_id")


def test_list_current(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_id: LayoutId, parser_version_id: ParserVersionId
) -> None:
    candidate_id, normalized = _make_candidate(conn, pdf_id, layout_id, parser_version_id)
    repo = SqliteGoldRepository(conn)
    repo.add_version(candidate_id, normalized, "yamada-taro", date(2026, 4, 1), "補職")

    current = repo.list_current()

    assert len(current) == 1
    assert current[0].person_key == "yamada-taro"


def test_list_current_as_of_uses_valid_from_window(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_id: LayoutId, parser_version_id: ParserVersionId
) -> None:
    # valid_fromはINSERT時刻(実時刻)であり、effective_date(業務上の発令日)とは別物。
    candidate_id, normalized = _make_candidate(conn, pdf_id, layout_id, parser_version_id)
    repo = SqliteGoldRepository(conn)
    repo.add_version(candidate_id, normalized, "yamada-taro", date(2026, 4, 1), "補職")

    as_of_far_future = repo.list_current(as_of=datetime(2999, 1, 1, tzinfo=UTC))
    as_of_before_creation = repo.list_current(as_of=datetime(2000, 1, 1, tzinfo=UTC))

    assert len(as_of_far_future) == 1
    assert as_of_before_creation == ()
