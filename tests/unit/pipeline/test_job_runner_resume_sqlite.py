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
from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.models import ParserVersion, ParserVersionId, PdfRecord
from mod_personnel_db.pipeline import job_runner as job_runner_module
from mod_personnel_db.pipeline.job_runner import JobRunner, JobRunnerRepositories
from mod_personnel_db.repositories.sqlite import apply_schema
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
