from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import JobId, ParserVersionId, PdfId, PersonnelSection
from mod_personnel_db.pipeline.context import PipelineContext

_STARTED_AT = datetime(2020, 1, 1, tzinfo=UTC)


@pytest.fixture
def context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="corr-extractors-0001",
        started_at=_STARTED_AT,
    )


def make_section(section_text: str, *, layout_id: str = "format_a") -> PersonnelSection:
    return PersonnelSection(
        document_ref=PdfId(1),
        layout_id=layout_id,
        section_index=0,
        section_label="発令一覧",
        page_range=(0, 0),
        section_text=section_text,
    )
