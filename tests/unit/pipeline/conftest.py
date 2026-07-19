from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import Job, JobId, ParserVersionId, PdfId
from mod_personnel_db.pipeline.context import PipelineContext

_STARTED_AT = datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="corr-0001",
        started_at=_STARTED_AT,
    )


@pytest.fixture
def running_job() -> Job:
    return Job(
        id=JobId(1),
        job_type="core_pipeline",
        pdf_id=PdfId(1),
        parser_version_id=ParserVersionId(1),
        status="running",
        started_at=_STARTED_AT,
        finished_at=None,
        processed_count=0,
        failed_count=0,
        error_summary=None,
    )
