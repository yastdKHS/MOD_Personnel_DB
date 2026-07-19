from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    BoundingBoxStatistics,
    ConfidenceBand,
    JobId,
    LayoutArtifact,
    LayoutArtifactPage,
    LayoutConfidence,
    LayoutDetectionResult,
    LayoutEvidence,
    LayoutWarning,
    PageStatistics,
    ParserVersionId,
    PdfId,
    RotationStatistics,
)
from mod_personnel_db.pipeline.context import PipelineContext

_STARTED_AT = datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="corr-sections-0001",
        started_at=_STARTED_AT,
    )


def make_artifact(
    page_texts: tuple[str, ...],
    *,
    layout_id: str | None = "format_a",
    layout_version: int | None = 1,
) -> LayoutArtifact:
    warnings = () if layout_id is not None else (LayoutWarning.NO_MATCH,)
    detection = LayoutDetectionResult(
        layout_id=layout_id,
        layout_version=layout_version,
        confidence=LayoutConfidence(score=1.0 if layout_id else 0.0, band=ConfidenceBand.VERIFIED),
        candidate_layouts=(),
        evidence=_dummy_evidence(),
        warnings=warnings,
    )
    pages = tuple(
        LayoutArtifactPage(index=index, text=text) for index, text in enumerate(page_texts)
    )
    return LayoutArtifact(source_pdf_id=PdfId(1), detection=detection, pages=pages)


def _dummy_evidence() -> LayoutEvidence:
    return LayoutEvidence(
        font_statistics=(),
        page_statistics=PageStatistics(page_count=0, average_char_count=0.0),
        bbox_statistics=BoundingBoxStatistics(average_width=0.0, average_height=0.0),
        rotation_statistics=RotationStatistics(rotated_page_count=0, dominant_rotation=0),
        header_signature=None,
        footer_signature=None,
        line_statistics=0.0,
        block_statistics=0.0,
    )
