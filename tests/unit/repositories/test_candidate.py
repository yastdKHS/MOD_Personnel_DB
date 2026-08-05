import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mod_personnel_db.models import (
    CandidateId,
    ConfidenceBand,
    NormalizedRecord,
    NormalizedValue,
    ParserVersion,
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
from mod_personnel_db.repositories.sqlite import apply_schema
from mod_personnel_db.repositories.sqlite.candidate import SqliteCandidateRepository
from mod_personnel_db.repositories.sqlite.job import SqliteJobRepository
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


def test_add_section_wraps_integrity_error_as_repository_error(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task29: `personnel_sections`のUNIQUE制約違反（`sqlite3.IntegrityError`）が
    `RepositoryError`へラップされ、JobRunnerが吸収できる形になることを検証する
    （architecture-contract.md保証7「RepositoryはSQLiteを隠蔽する」）。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section = _make_section(pdf_id, layout_era_id)
    repo.add_section(section)

    with pytest.raises(RepositoryError) as excinfo:
        repo.add_section(section)
    assert not isinstance(excinfo.value, sqlite3.IntegrityError)


def test_add_raw_wraps_integrity_error_as_repository_error(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task29: `candidate_records`のUNIQUE制約違反も同様に`RepositoryError`へラップする。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_era_id,
        record_index=0,
        raw_fields={"rank": "陸将補"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    repo.add_raw(section_id, raw)

    with pytest.raises(RepositoryError) as excinfo:
        repo.add_raw(section_id, raw)
    assert not isinstance(excinfo.value, sqlite3.IntegrityError)


def test_transaction_commits_on_success(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task33: `transaction()`ブロックが正常終了すれば、内部の`add_section()`/
    `supersede_section()`の変更がまとめてcommitされる（ADR-0047 TOCTOU対応）。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section = _make_section(pdf_id, layout_era_id)

    with repo.transaction():
        section_id = repo.add_section(section)

    fetched = repo.get_section(section_id)
    assert fetched is not None


def test_transaction_rolls_back_on_exception(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task33: ブロック内で例外が送出された場合、`add_section()`の変更は
    ロールバックされ永続化されない。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section = _make_section(pdf_id, layout_era_id)

    with pytest.raises(ValueError, match="boom"), repo.transaction():
        repo.add_section(section)
        raise ValueError("boom")

    row = conn.execute("SELECT COUNT(*) AS cnt FROM personnel_sections").fetchone()
    assert row["cnt"] == 0


def test_transaction_does_not_rewrap_repository_error(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task33 Step3': `transaction()`ブロック内で`add_section()`が送出する
    `RepositoryError`（Task29のIntegrityErrorラップ）は再ラップされず、元の
    メッセージ・`__cause__`（`sqlite3.IntegrityError`）がそのまま伝播する。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section = _make_section(pdf_id, layout_era_id)
    repo.add_section(section)

    with pytest.raises(RepositoryError) as excinfo, repo.transaction():
        repo.add_section(section)  # UNIQUE制約違反でRepositoryErrorを送出

    assert "failed to add personnel_section" in str(excinfo.value)
    assert "transaction failed" not in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, sqlite3.IntegrityError)


def test_transaction_rejects_nested_use(
    conn: sqlite3.Connection, parser_version_id: ParserVersionId
) -> None:
    """Task33: `transaction()`のネスト利用は`RepositoryError`で拒否する。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)

    with pytest.raises(RepositoryError, match="nested transaction"), repo.transaction():  # noqa: SIM117 -- ネスト自体を検証するため意図的に入れ子にする
        with repo.transaction():
            pass


def test_transaction_wraps_lock_contention_as_repository_error(
    tmp_path: Path, parser_version_id: ParserVersionId
) -> None:
    """Task33: `BEGIN IMMEDIATE`実行時に他接続が書き込みロックを保持している
    場合、生の`sqlite3.OperationalError`ではなく`RepositoryError`へ変換される
    （保証7、ADR-0047 TOCTOU対応）。"""
    db_path = str(tmp_path / "lock_contention.db")
    blocking_conn = sqlite3.connect(db_path)
    apply_schema(blocking_conn)
    blocking_conn.execute("BEGIN IMMEDIATE")  # 書き込みロックを保持したまま維持する

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 100")  # テスト高速化のため本番既定値より短縮
    repo = SqliteCandidateRepository(conn, parser_version_id)

    try:
        with pytest.raises(RepositoryError) as excinfo, repo.transaction():
            pass
        assert not isinstance(excinfo.value, sqlite3.OperationalError)
    finally:
        blocking_conn.rollback()
        blocking_conn.close()
        conn.close()


def test_add_section_commits_immediately_outside_transaction(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task33回帰確認: `transaction()`を使わない単体呼び出しでは、従来どおり
    `add_section()`が即commitする（Task28/29確立済みの挙動を変えない）。
    `_in_transaction`フラグがFalseのままであることも確認する。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)

    assert repo._in_transaction is False
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))
    assert repo._in_transaction is False

    row = conn.execute("SELECT id FROM personnel_sections WHERE id = ?", (section_id,)).fetchone()
    assert row is not None


def test_find_section_returns_id_when_exists(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))

    assert repo.find_section(pdf_id, section_index=0) == section_id


def test_find_section_returns_none_when_not_exists(
    conn: sqlite3.Connection, pdf_id: PdfId, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)

    assert repo.find_section(pdf_id, section_index=0) is None


def test_find_candidate_returns_id_when_exists(
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

    assert repo.find_candidate(section_id, record_index=0) == candidate_id


def test_find_candidate_returns_none_when_not_exists(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))

    assert repo.find_candidate(section_id, record_index=0) is None


def test_find_active_section_returns_old_version_id(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task31 Step5/Step6: Case C（parser_version更新後の再解析）向け。
    `find_active_section`はparser_version_idを条件に含めないため、新versionの
    Repositoryインスタンスからでも旧version（status='parsed'のまま）のSectionを
    発見できることを検証する。"""
    old_repo = SqliteCandidateRepository(conn, parser_version_id)
    old_section_id = old_repo.add_section(_make_section(pdf_id, layout_era_id))

    jobs = SqliteJobRepository(conn)
    new_version_id = jobs.record_parser_version(
        ParserVersion(
            id=None,
            code_version="v2.0.0",
            knowledge_snapshot_checksum="d" * 64,
            released_at=datetime(2026, 2, 1, tzinfo=UTC),
            notes=None,
        )
    )
    new_repo = SqliteCandidateRepository(conn, new_version_id)

    assert new_repo.find_active_section(pdf_id, section_index=0) == old_section_id


def test_find_active_section_returns_none_when_not_exists(
    conn: sqlite3.Connection, pdf_id: PdfId, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)

    assert repo.find_active_section(pdf_id, section_index=0) is None


def test_supersede_section_parsed_to_superseded(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))

    repo.supersede_section(section_id)

    row = conn.execute(
        "SELECT status FROM personnel_sections WHERE id = ?", (section_id,)
    ).fetchone()
    assert row["status"] == "superseded"
    assert repo.find_active_section(pdf_id, section_index=0) is None


def test_supersede_section_is_idempotent_when_already_superseded(
    conn: sqlite3.Connection, pdf_id: PdfId, layout_era_id: str, parser_version_id: ParserVersionId
) -> None:
    """Task31 Step5/Step6: `WHERE status='parsed'`により2回目の呼び出しは0件更新に
    なるが、これは正常系であり例外を送出しない（冪等性の確認）。"""
    repo = SqliteCandidateRepository(conn, parser_version_id)
    section_id = repo.add_section(_make_section(pdf_id, layout_era_id))

    repo.supersede_section(section_id)
    repo.supersede_section(section_id)

    row = conn.execute(
        "SELECT status FROM personnel_sections WHERE id = ?", (section_id,)
    ).fetchone()
    assert row["status"] == "superseded"
