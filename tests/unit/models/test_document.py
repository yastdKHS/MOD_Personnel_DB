from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    ConfidenceBand,
    Document,
    DocumentAnalysisResult,
    DocumentId,
    DocumentMetadata,
    DocumentStatistics,
    DocumentV1,
    DocumentWarning,
    PageV1,
    PdfId,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError

_SHA256 = "a" * 64
_ANALYZED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _page(index: int, width: float = 210.0, height: float = 297.0) -> PageV1:
    return PageV1(index=index, text=f"page {index}", width=width, height=height)


def test_document_normal_construction() -> None:
    document = DocumentV1(
        source_pdf_id=PdfId(1),
        pages=(_page(0), _page(1)),
        analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert len(document.pages) == 2
    assert document.pages[0].index == 0


def test_page_allows_empty_text() -> None:
    page = PageV1(index=0, text="", width=1.0, height=1.0)
    assert page.text == ""


def test_document_rejects_empty_pages() -> None:
    with pytest.raises(ModelValidationError):
        DocumentV1(source_pdf_id=PdfId(1), pages=(), analyzed_at=datetime(2026, 1, 1, tzinfo=UTC))


def test_document_rejects_non_contiguous_indices() -> None:
    with pytest.raises(ModelValidationError):
        DocumentV1(
            source_pdf_id=PdfId(1),
            pages=(_page(0), _page(2)),
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_document_rejects_out_of_order_indices() -> None:
    with pytest.raises(ModelValidationError):
        DocumentV1(
            source_pdf_id=PdfId(1),
            pages=(_page(1), _page(0)),
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_document_rejects_duplicate_indices() -> None:
    with pytest.raises(ModelValidationError):
        DocumentV1(
            source_pdf_id=PdfId(1),
            pages=(_page(0), _page(0)),
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


@pytest.mark.parametrize(("width", "height"), [(0.0, 1.0), (1.0, 0.0), (-1.0, 1.0)])
def test_page_rejects_non_positive_dimensions(width: float, height: float) -> None:
    with pytest.raises(ModelValidationError):
        PageV1(index=0, text="x", width=width, height=height)


def test_page_rejects_negative_index() -> None:
    with pytest.raises(ModelValidationError):
        PageV1(index=-1, text="x", width=1.0, height=1.0)


def test_page_boundary_minimum_positive_dimensions() -> None:
    page = PageV1(index=0, text="x", width=0.0001, height=0.0001)
    assert page.width > 0


# --- Version 2.0 (ADR-0032, ADR-0033) ---


def _metadata(*, encrypted: bool = False, file_size: int = 1024) -> DocumentMetadata:
    return DocumentMetadata(
        filename="sample.pdf",
        sha256=_SHA256,
        file_size=file_size,
        created_at=_ANALYZED_AT,
        modified_at=_ANALYZED_AT,
        pdf_version="1.7",
        encrypted=encrypted,
    )


def _statistics(
    *,
    page_count: int = 3,
    text_length: int | None = 120,
    image_count: int = 0,
    rotation_count: int = 0,
    analysis_time_ms: float = 12.5,
) -> DocumentStatistics:
    return DocumentStatistics(
        page_count=page_count,
        text_length=text_length,
        image_count=image_count,
        rotation_count=rotation_count,
        analysis_time_ms=analysis_time_ms,
    )


def _confidence() -> Confidence:
    return Confidence(score=0.9, band=ConfidenceBand.HIGH)


def test_document_metadata_normal_construction() -> None:
    metadata = _metadata()
    assert metadata.filename == "sample.pdf"
    assert metadata.encrypted is False


def test_document_metadata_rejects_invalid_sha256_length() -> None:
    with pytest.raises(ModelValidationError):
        DocumentMetadata(
            filename="sample.pdf",
            sha256="too-short",
            file_size=1,
            created_at=None,
            modified_at=None,
            pdf_version="1.7",
            encrypted=False,
        )


def test_document_metadata_rejects_negative_file_size() -> None:
    with pytest.raises(ModelValidationError):
        _metadata(file_size=-1)


def test_document_metadata_allows_none_timestamps() -> None:
    metadata = DocumentMetadata(
        filename="sample.pdf",
        sha256=_SHA256,
        file_size=0,
        created_at=None,
        modified_at=None,
        pdf_version="1.7",
        encrypted=False,
    )
    assert metadata.created_at is None


def test_document_statistics_normal_construction() -> None:
    statistics = _statistics()
    assert statistics.page_count == 3
    assert statistics.text_length == 120


def test_document_statistics_allows_none_text_length() -> None:
    statistics = _statistics(text_length=None)
    assert statistics.text_length is None


def test_document_statistics_rejects_negative_page_count() -> None:
    with pytest.raises(ModelValidationError):
        _statistics(page_count=-1)


def test_document_statistics_rejects_negative_image_count() -> None:
    with pytest.raises(ModelValidationError):
        _statistics(image_count=-1)


def test_document_statistics_rejects_negative_rotation_count() -> None:
    with pytest.raises(ModelValidationError):
        _statistics(rotation_count=-1)


def test_document_statistics_rejects_negative_analysis_time_ms() -> None:
    with pytest.raises(ModelValidationError):
        _statistics(analysis_time_ms=-1.0)


def test_document_statistics_rejects_negative_text_length() -> None:
    with pytest.raises(ModelValidationError):
        _statistics(text_length=-1)


def test_document_statistics_boundary_zero_values() -> None:
    statistics = _statistics(page_count=0, image_count=0, rotation_count=0, analysis_time_ms=0.0)
    assert statistics.page_count == 0


def test_document_analysis_result_normal_construction() -> None:
    result = DocumentAnalysisResult(
        metadata=_metadata(),
        statistics=_statistics(),
        warnings=(),
        confidence=_confidence(),
    )
    assert result.warnings == ()


def test_document_analysis_result_requires_encrypted_warning_when_encrypted() -> None:
    with pytest.raises(ModelValidationError):
        DocumentAnalysisResult(
            metadata=_metadata(encrypted=True),
            statistics=_statistics(),
            warnings=(),
            confidence=_confidence(),
        )


def test_document_analysis_result_accepts_encrypted_with_warning() -> None:
    result = DocumentAnalysisResult(
        metadata=_metadata(encrypted=True),
        statistics=_statistics(),
        warnings=(DocumentWarning.ENCRYPTED,),
        confidence=_confidence(),
    )
    assert DocumentWarning.ENCRYPTED in result.warnings


def test_document_v2_normal_construction() -> None:
    document = Document(
        id=DocumentId(1),
        source_pdf_id=PdfId(1),
        file_path="/tmp/sample.pdf",
        analysis=DocumentAnalysisResult(
            metadata=_metadata(),
            statistics=_statistics(),
            warnings=(),
            confidence=_confidence(),
        ),
        analyzed_at=_ANALYZED_AT,
        analyzer_version="v1.0.0",
    )
    assert document.analysis.metadata.filename == "sample.pdf"
    assert document.analyzer_version == "v1.0.0"
    assert document.file_path == "/tmp/sample.pdf"


@pytest.mark.parametrize("warning", list(DocumentWarning))
def test_document_warning_enum_members(warning: DocumentWarning) -> None:
    assert isinstance(warning.value, str)
