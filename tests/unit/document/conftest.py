import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mod_personnel_db.models import JobId, ParserVersionId, PdfId, PdfRecord
from mod_personnel_db.pipeline.context import PipelineContext

_STARTED_AT = datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="corr-doc-0001",
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
def make_pdf_record() -> Callable[[Path], PdfRecord]:
    def _make(path: Path) -> PdfRecord:
        return PdfRecord(
            id=PdfId(1),
            content_hash="0" * 64,
            source_url="https://example.com/sample.pdf",
            published_date=_STARTED_AT.date(),
            fetched_at=_STARTED_AT,
            file_path=str(path),
            file_size_bytes=os.path.getsize(path) if path.exists() else 0,
            status="fetched",
        )

    return _make
