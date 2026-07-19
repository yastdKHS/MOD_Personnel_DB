from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.models import (
    CandidateId,
    ConfidenceBand,
    ExportRecord,
    Job,
    KnowledgeItem,
    KnowledgeItemId,
    KnowledgeSnapshot,
    Layout,
    LayoutId,
    NormalizedRecord,
    NormalizedValue,
    ParserVersion,
    PdfId,
    PersonnelSection,
    RawRecord,
    ReviewItem,
    ReviewSessionId,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


def test_confidence_rejects_out_of_range_score() -> None:
    with pytest.raises(ModelValidationError):
        Confidence(score=1.5, band=ConfidenceBand.HIGH)


def test_confidence_accepts_boundary_scores() -> None:
    assert Confidence(score=0.0, band=ConfidenceBand.LOW).score == 0.0
    assert Confidence(score=1.0, band=ConfidenceBand.VERIFIED).score == 1.0


def test_raw_record_rejects_empty_fields() -> None:
    with pytest.raises(ModelValidationError):
        RawRecord(
            section_ref=None,
            layout_id="format_a",
            record_index=0,
            raw_fields={},
            extracted_at=datetime.now(UTC),
        )


def test_raw_record_rejects_negative_index() -> None:
    with pytest.raises(ModelValidationError):
        RawRecord(
            section_ref=None,
            layout_id="format_a",
            record_index=-1,
            raw_fields={"rank": "陸将"},
            extracted_at=datetime.now(UTC),
        )


def test_raw_record_rejects_empty_layout_id() -> None:
    with pytest.raises(ModelValidationError):
        RawRecord(
            section_ref=None,
            layout_id="",
            record_index=0,
            raw_fields={"rank": "陸将"},
            extracted_at=datetime.now(UTC),
        )


def test_normalized_value_rejects_empty_value() -> None:
    with pytest.raises(ModelValidationError):
        NormalizedValue(value="", raw="陸将")


def test_normalized_record_requires_matching_field_keys() -> None:
    raw = RawRecord(
        section_ref=None,
        layout_id="format_a",
        record_index=0,
        raw_fields={"rank": "陸将"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(ModelValidationError):
        NormalizedRecord(
            raw_record_ref=raw,
            normalized_fields={"other_field": NormalizedValue(value="x", raw=None)},
            normalization_applied=(),
            normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_normalized_record_rejects_earlier_normalized_at() -> None:
    raw = RawRecord(
        section_ref=None,
        layout_id="format_a",
        record_index=0,
        raw_fields={"rank": "陸将"},
        extracted_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    with pytest.raises(ModelValidationError):
        NormalizedRecord(
            raw_record_ref=raw,
            normalized_fields={"rank": NormalizedValue(value="陸将", raw="陸将")},
            normalization_applied=(),
            normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    ("section_index", "page_range", "section_text"),
    [
        (-1, (1, 1), "x"),
        (0, (2, 1), "x"),
        (0, (1, 1), ""),
    ],
)
def test_personnel_section_rejects_invalid_values(
    section_index: int, page_range: tuple[int, int], section_text: str
) -> None:
    with pytest.raises(ModelValidationError):
        PersonnelSection(
            document_ref=PdfId(1),
            layout_id="format_a",
            section_index=section_index,
            section_label=None,
            page_range=page_range,
            section_text=section_text,
        )


def test_export_record_rejects_negative_count() -> None:
    with pytest.raises(ModelValidationError):
        ExportRecord(
            id=None,
            format="json",
            destination="ftp://x",
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
            record_count=-1,
            checksum="a",
            status="completed",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_export_record_rejects_empty_checksum_when_completed() -> None:
    with pytest.raises(ModelValidationError):
        ExportRecord(
            id=None,
            format="json",
            destination="ftp://x",
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
            record_count=1,
            checksum="",
            status="completed",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_job_rejects_running_with_finished_at() -> None:
    with pytest.raises(ModelValidationError):
        Job(
            id=None,
            job_type="fetch",
            pdf_id=None,
            parser_version_id=None,
            status="running",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=datetime(2026, 1, 2, tzinfo=UTC),
            processed_count=0,
            failed_count=0,
            error_summary=None,
        )


def test_job_rejects_finished_before_started() -> None:
    with pytest.raises(ModelValidationError):
        Job(
            id=None,
            job_type="fetch",
            pdf_id=None,
            parser_version_id=None,
            status="succeeded",
            started_at=datetime(2026, 1, 2, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, tzinfo=UTC),
            processed_count=0,
            failed_count=0,
            error_summary=None,
        )


def test_job_rejects_negative_counts() -> None:
    with pytest.raises(ModelValidationError):
        Job(
            id=None,
            job_type="fetch",
            pdf_id=None,
            parser_version_id=None,
            status="running",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=None,
            processed_count=-1,
            failed_count=0,
            error_summary=None,
        )


def test_parser_version_rejects_invalid_code_version() -> None:
    with pytest.raises(ModelValidationError):
        ParserVersion(
            id=None,
            code_version="1.0.0",
            knowledge_snapshot_checksum="a" * 64,
            released_at=datetime(2026, 1, 1, tzinfo=UTC),
            notes=None,
        )


def test_knowledge_item_rejects_effective_to_before_from() -> None:
    with pytest.raises(ModelValidationError):
        KnowledgeItem(
            id=KnowledgeItemId(1),
            category="rank",
            source_file="knowledge/ranks/x.yaml",
            item_key="x",
            canonical_value="x",
            effective_from=date(2026, 1, 2),
            effective_to=date(2026, 1, 1),
            provenance_source="src",
            version=1,
        )


def test_knowledge_snapshot_rejects_empty_checksum() -> None:
    with pytest.raises(ModelValidationError):
        KnowledgeSnapshot(items=(), snapshot_checksum="", as_of=date(2026, 1, 1))


def test_layout_rejects_valid_to_before_from() -> None:
    with pytest.raises(ModelValidationError):
        Layout(
            id=LayoutId(1),
            era_id="reiwa",
            version=1,
            manifest_path="layouts/reiwa/manifest.yaml",
            manifest_checksum="a" * 64,
            valid_from=date(2026, 1, 2),
            valid_to=date(2026, 1, 1),
            status="active",
        )


def test_review_item_rejects_unchanged_value() -> None:
    with pytest.raises(ModelValidationError):
        ReviewItem(
            session_id=ReviewSessionId(1),
            target_table="candidate_records",
            target_id=CandidateId(1),
            field_name="rank",
            old_value="陸将",
            new_value="陸将",
            change_reason=None,
            reviewer="alice",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_review_item_rejects_empty_reviewer() -> None:
    with pytest.raises(ModelValidationError):
        ReviewItem(
            session_id=ReviewSessionId(1),
            target_table="candidate_records",
            target_id=CandidateId(1),
            field_name="rank",
            old_value="陸将補",
            new_value="陸将",
            change_reason=None,
            reviewer="",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
