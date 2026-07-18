from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import Document, Page, PdfId
from mod_personnel_db.models.values import ModelValidationError


def _page(index: int, width: float = 210.0, height: float = 297.0) -> Page:
    return Page(index=index, text=f"page {index}", width=width, height=height)


def test_document_normal_construction() -> None:
    document = Document(
        source_pdf_id=PdfId(1),
        pages=(_page(0), _page(1)),
        analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert len(document.pages) == 2
    assert document.pages[0].index == 0


def test_page_allows_empty_text() -> None:
    page = Page(index=0, text="", width=1.0, height=1.0)
    assert page.text == ""


def test_document_rejects_empty_pages() -> None:
    with pytest.raises(ModelValidationError):
        Document(source_pdf_id=PdfId(1), pages=(), analyzed_at=datetime(2026, 1, 1, tzinfo=UTC))


def test_document_rejects_non_contiguous_indices() -> None:
    with pytest.raises(ModelValidationError):
        Document(
            source_pdf_id=PdfId(1),
            pages=(_page(0), _page(2)),
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_document_rejects_out_of_order_indices() -> None:
    with pytest.raises(ModelValidationError):
        Document(
            source_pdf_id=PdfId(1),
            pages=(_page(1), _page(0)),
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_document_rejects_duplicate_indices() -> None:
    with pytest.raises(ModelValidationError):
        Document(
            source_pdf_id=PdfId(1),
            pages=(_page(0), _page(0)),
            analyzed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


@pytest.mark.parametrize(("width", "height"), [(0.0, 1.0), (1.0, 0.0), (-1.0, 1.0)])
def test_page_rejects_non_positive_dimensions(width: float, height: float) -> None:
    with pytest.raises(ModelValidationError):
        Page(index=0, text="x", width=width, height=height)


def test_page_rejects_negative_index() -> None:
    with pytest.raises(ModelValidationError):
        Page(index=-1, text="x", width=1.0, height=1.0)


def test_page_boundary_minimum_positive_dimensions() -> None:
    page = Page(index=0, text="x", width=0.0001, height=0.0001)
    assert page.width > 0
