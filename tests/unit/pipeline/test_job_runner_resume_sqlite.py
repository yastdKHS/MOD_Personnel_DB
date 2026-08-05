"""Task32 Step3: JobRunnerのCase C（Supersede）を実SQLiteで検証する。

`tests/unit/repositories/test_candidate.py`がRepository単体のSQL挙動を、
`tests/unit/pipeline/test_job_runner.py`がStub Repositoryを用いた
`JobRunner`の呼び出し順序を、それぞれ独立に検証しているのに対し、本テストは
両者を実際に組み合わせ、`(pdf_id, section_index)`ごとに`status='parsed'`の
`personnel_sections`が高々1件であるというADR-0047の設計前提が、実際の
`JobRunner`実行（異なる2つのparser_versionでの連続処理）を通じて維持される
ことを確認する（Task32 Step3レビュー項目「`status='parsed'`が高々1件という
設計前提を破る経路が存在しないか」に対応）。
"""

import sqlite3
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mod_personnel_db.models import ParserVersion, ParserVersionId, PdfId, PdfRecord
from mod_personnel_db.pipeline import job_runner as job_runner_module
from mod_personnel_db.pipeline.job_runner import JobRunner, JobRunnerRepositories
from mod_personnel_db.repositories.sqlite import apply_schema
from mod_personnel_db.repositories.sqlite._base import connect as sqlite_connect
from mod_personnel_db.repositories.sqlite.candidate import SqliteCandidateRepository
from mod_personnel_db.repositories.sqlite.job import SqliteJobRepository
from mod_personnel_db.repositories.sqlite.pdf import SqlitePdfRepository

from ._job_runner_stubs import (
    StubKnowledgeService,
    StubLearningService,
    make_field_extractor_stub_class,
    make_normalizer_stub_class,
    make_section_parser_stub_class,
    make_stub_stage_class,
    make_validator_stub_class,
)


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_schema(connection)
    return connection


def _insert_active_layout(conn: sqlite3.Connection) -> None:
    # make_section_parser_stub_classが生成するPersonnelSection.layout_id
    # （era_id、Task31 Case A/Bのstub群と同じ"reiwa"）に対応する行。
    conn.execute(
        """
        INSERT INTO layouts (era_id, version, manifest_path, manifest_checksum, valid_from, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("reiwa", 1, "layouts/reiwa/manifest.yaml", "c" * 64, "2019-05-01", "active"),
    )
    conn.commit()


def _make_pdf_record() -> PdfRecord:
    return PdfRecord(
        id=None,
        content_hash="e" * 64,
        source_url="https://example.mod.go.jp/appointment.pdf",
        published_date=date(2026, 1, 1),
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        file_path="ee/ee/" + "e" * 64 + ".pdf",
        file_size_bytes=1024,
        status="fetched",
    )


def _patch_single_section_stages(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    monkeypatch.setattr(
        job_runner_module, "DocumentAnalyzer", make_stub_stage_class("document_analyzer", calls)
    )
    monkeypatch.setattr(
        job_runner_module, "LayoutDetector", make_stub_stage_class("layout_detector", calls)
    )
    monkeypatch.setattr(
        job_runner_module, "SectionParser", make_section_parser_stub_class(calls, section_count=1)
    )
    monkeypatch.setattr(
        job_runner_module,
        "FieldExtractor",
        make_field_extractor_stub_class(calls, {0: 1}, frozenset()),
    )
    monkeypatch.setattr(
        job_runner_module,
        "Normalizer",
        make_normalizer_stub_class(calls, frozenset(), frozenset()),
    )
    monkeypatch.setattr(
        job_runner_module, "Validator", make_validator_stub_class(calls, frozenset())
    )


def _make_runner(conn: sqlite3.Connection, parser_version_id: ParserVersionId) -> JobRunner:
    return JobRunner(
        repositories=JobRunnerRepositories(
            pdfs=SqlitePdfRepository(conn),
            jobs=SqliteJobRepository(conn),
            candidates=SqliteCandidateRepository(conn, parser_version_id),
        ),
        knowledge=StubKnowledgeService(),
        learning=StubLearningService(),
        parser_version_id=parser_version_id,
    )


def test_case_c_maintains_single_active_section_across_real_sqlite(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _insert_active_layout(conn)
    jobs_repo = SqliteJobRepository(conn)
    v1 = jobs_repo.record_parser_version(
        ParserVersion(
            id=None,
            code_version="v1.0.0",
            knowledge_snapshot_checksum="a" * 64,
            released_at=datetime(2026, 1, 1, tzinfo=UTC),
            notes=None,
        )
    )
    v2 = jobs_repo.record_parser_version(
        ParserVersion(
            id=None,
            code_version="v2.0.0",
            knowledge_snapshot_checksum="b" * 64,
            released_at=datetime(2026, 2, 1, tzinfo=UTC),
            notes=None,
        )
    )

    pdf_repo = SqlitePdfRepository(conn)
    pdf_id = pdf_repo.add(_make_pdf_record())
    pdf = pdf_repo.get(pdf_id)
    assert pdf is not None

    calls_v1: list[str] = []
    _patch_single_section_stages(monkeypatch, calls_v1)
    result_v1 = _make_runner(conn, v1).run_for_pdf(pdf)
    assert result_v1.succeeded is True

    pdf_after_v1 = pdf_repo.get(pdf_id)
    assert pdf_after_v1 is not None

    calls_v2: list[str] = []
    _patch_single_section_stages(monkeypatch, calls_v2)
    result_v2 = _make_runner(conn, v2).run_for_pdf(pdf_after_v1)
    assert result_v2.succeeded is True

    rows = conn.execute(
        "SELECT parser_version_id, status FROM personnel_sections "
        "WHERE pdf_id = ? AND section_index = 0",
        (int(pdf_id),),
    ).fetchall()
    assert len(rows) == 2
    parsed = [row for row in rows if row["status"] == "parsed"]
    superseded = [row for row in rows if row["status"] == "superseded"]
    assert len(parsed) == 1
    assert len(superseded) == 1
    assert parsed[0]["parser_version_id"] == int(v2)
    assert superseded[0]["parser_version_id"] == int(v1)


def test_case_c_second_run_same_version_resumes_without_superseding(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同一versionでの2回目の実行はCase A（Resume/Skip）であり、Supersedeは
    発生しない（既存Sectionが全件`passed`/`failed`であるためSection全体を
    skipし、`personnel_sections`は1行のまま`status='parsed'`を維持する）。"""
    _insert_active_layout(conn)
    jobs_repo = SqliteJobRepository(conn)
    v1 = jobs_repo.record_parser_version(
        ParserVersion(
            id=None,
            code_version="v1.0.0",
            knowledge_snapshot_checksum="a" * 64,
            released_at=datetime(2026, 1, 1, tzinfo=UTC),
            notes=None,
        )
    )
    pdf_repo = SqlitePdfRepository(conn)
    pdf_id = pdf_repo.add(_make_pdf_record())
    pdf = pdf_repo.get(pdf_id)
    assert pdf is not None

    calls_first: list[str] = []
    _patch_single_section_stages(monkeypatch, calls_first)
    result_first = _make_runner(conn, v1).run_for_pdf(pdf)
    assert result_first.succeeded is True

    pdf_after_first = pdf_repo.get(pdf_id)
    assert pdf_after_first is not None

    calls_second: list[str] = []
    _patch_single_section_stages(monkeypatch, calls_second)
    result_second = _make_runner(conn, v1).run_for_pdf(pdf_after_first)
    assert result_second.succeeded is True
    # Task31 Case A: 全Candidateが完了済みのためSection全体skip
    # （FieldExtractor以降が呼ばれない）。
    assert "field_extractor" not in calls_second

    rows = conn.execute(
        "SELECT parser_version_id, status FROM personnel_sections "
        "WHERE pdf_id = ? AND section_index = 0",
        (int(pdf_id),),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "parsed"
    assert rows[0]["parser_version_id"] == int(v1)


def _record_parser_version(conn: sqlite3.Connection, code_version: str) -> ParserVersionId:
    return SqliteJobRepository(conn).record_parser_version(
        ParserVersion(
            id=None,
            code_version=code_version,
            knowledge_snapshot_checksum="f" * 64,
            released_at=datetime(2026, 1, 1, tzinfo=UTC),
            notes=None,
        )
    )


def _seed_concurrent_case_c_db(
    monkeypatch: pytest.MonkeyPatch, db_path: str
) -> tuple[PdfId, ParserVersionId, ParserVersionId]:
    """スキーマ・レイアウト・parser_version（v1〜v3）・PDFを用意し、v1で1回
    処理して「旧アクティブSection」を作っておく。v2・v3が同じ旧Sectionを
    supersede対象として競合する状況を再現するための下準備。"""
    setup_conn = sqlite_connect(db_path)
    apply_schema(setup_conn)
    _insert_active_layout(setup_conn)
    v1 = _record_parser_version(setup_conn, "v1.0.0")
    v2 = _record_parser_version(setup_conn, "v2.0.0")
    v3 = _record_parser_version(setup_conn, "v3.0.0")
    pdf_id = SqlitePdfRepository(setup_conn).add(_make_pdf_record())
    setup_conn.close()

    seed_conn = sqlite_connect(db_path)
    _patch_single_section_stages(monkeypatch, [])
    pdf_for_seed = SqlitePdfRepository(seed_conn).get(pdf_id)
    assert pdf_for_seed is not None
    result_seed = _make_runner(seed_conn, v1).run_for_pdf(pdf_for_seed)
    assert result_seed.succeeded is True
    seed_conn.close()

    return pdf_id, v2, v3


def _run_concurrent_case_c(
    monkeypatch: pytest.MonkeyPatch,
    db_path: str,
    pdf_id: PdfId,
    v2: ParserVersionId,
    v3: ParserVersionId,
) -> list[BaseException]:
    """v2・v3をそれぞれ別スレッド・別接続で並行実行し、両スレッドが
    `BEGIN IMMEDIATE`直前で足並みを揃えるよう`transaction()`をBarrierで
    ラップする（sleepによるタイミング頼みの再現を避けるため）。パッチは
    スレッド開始前に1回だけ適用する（`SqliteCandidateRepository`クラス自体への
    書き換えのため、スレッドごとに個別適用するとスレッドセーフでない）。"""
    barrier = threading.Barrier(2)
    original_transaction = SqliteCandidateRepository.transaction

    @contextmanager
    def synced_transaction(self: SqliteCandidateRepository) -> Iterator[None]:
        barrier.wait(timeout=5)
        with original_transaction(self):
            yield

    monkeypatch.setattr(SqliteCandidateRepository, "transaction", synced_transaction)

    errors: list[BaseException] = []

    def _run(version_id: ParserVersionId) -> None:
        try:
            thread_conn = sqlite_connect(db_path)
            pdf = SqlitePdfRepository(thread_conn).get(pdf_id)
            assert pdf is not None
            _make_runner(thread_conn, version_id).run_for_pdf(pdf)
            thread_conn.close()
        except BaseException as exc:  # noqa: BLE001 -- テストスレッドの例外を捕捉して後で失敗させる
            errors.append(exc)

    thread_v2 = threading.Thread(target=_run, args=(v2,))
    thread_v3 = threading.Thread(target=_run, args=(v3,))
    thread_v2.start()
    thread_v3.start()
    thread_v2.join(timeout=10)
    thread_v3.join(timeout=10)
    return errors


def test_case_c_concurrent_versions_produce_single_active_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task33: 異なるparser_versionによる並行Case C実行でも、`transaction()`
    （`BEGIN IMMEDIATE`+`busy_timeout`）により最終的に`status='parsed'`が1件
    のみとなることを、実ファイルDB・2つの独立した接続・2スレッドで検証する
    （ADR-0047 TOCTOU対応、Task33 Step1シナリオ2-2の再現）。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "concurrent_case_c.db")
        pdf_id, v2, v3 = _seed_concurrent_case_c_db(monkeypatch, db_path)

        errors = _run_concurrent_case_c(monkeypatch, db_path, pdf_id, v2, v3)
        assert not errors, f"並行実行中に例外が発生した: {errors}"

        verify_conn = sqlite_connect(db_path)
        rows = verify_conn.execute(
            "SELECT parser_version_id, status FROM personnel_sections "
            "WHERE pdf_id = ? AND section_index = 0",
            (int(pdf_id),),
        ).fetchall()
        verify_conn.close()

        assert len(rows) == 3
        parsed = [row for row in rows if row["status"] == "parsed"]
        superseded = [row for row in rows if row["status"] == "superseded"]
        # ADR-0047の設計前提: (pdf_id, section_index)ごとにstatus='parsed'は高々1件。
        assert len(parsed) == 1
        assert len(superseded) == 2
        assert parsed[0]["parser_version_id"] in (int(v2), int(v3))
