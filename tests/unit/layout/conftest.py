from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    Document,
    DocumentAnalysisResult,
    DocumentId,
    DocumentMetadata,
    DocumentStatistics,
    JobId,
    ParserVersionId,
    PdfId,
)
from mod_personnel_db.pipeline.context import PipelineContext

_STARTED_AT = datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="corr-layout-0001",
        started_at=_STARTED_AT,
    )


@pytest.fixture
def write_pdf(tmp_path: Path) -> Callable[[str, bytes], Path]:
    def _write(filename: str, content: bytes) -> Path:
        path = tmp_path / filename
        path.write_bytes(content)
        return path

    return _write


@pytest.fixture
def make_document() -> Callable[[Path], Document]:
    def _make(path: Path) -> Document:
        metadata = DocumentMetadata(
            filename=path.name,
            sha256="0" * 64,
            file_size=1,
            created_at=_STARTED_AT,
            modified_at=_STARTED_AT,
            pdf_version="1.7",
            encrypted=False,
        )
        statistics = DocumentStatistics(
            page_count=1, text_length=1, image_count=0, rotation_count=0, analysis_time_ms=1.0
        )
        analysis = DocumentAnalysisResult(
            metadata=metadata,
            statistics=statistics,
            warnings=(),
            confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
        )
        return Document(
            id=DocumentId(1),
            source_pdf_id=PdfId(1),
            file_path=str(path),
            analysis=analysis,
            analyzed_at=_STARTED_AT,
            analyzer_version="v0.1.0",
        )

    return _make
