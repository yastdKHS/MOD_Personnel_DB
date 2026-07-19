from typing import cast

from mod_personnel_db.extractors import FieldExtractor
from mod_personnel_db.models import (
    FieldExtractionResult,
    Job,
    JobId,
    ParserVersionId,
    PdfId,
    PersonnelSection,
)
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage

from .conftest import make_section


def test_field_extractor_satisfies_pipeline_stage_protocol() -> None:
    stage: PipelineStage[PersonnelSection, FieldExtractionResult] = FieldExtractor()
    assert stage is not None


def test_field_extractor_public_api_is_run_only() -> None:
    public_names = [name for name in dir(FieldExtractor) if not name.startswith("_")]
    assert public_names == ["run"]


def test_field_extractor_runs_inside_pipeline_runner(context: PipelineContext) -> None:
    section = make_section("山田太郎  陸将補")

    builder = PipelineBuilder()
    # PipelineRunner/BuilderはPipelineStage[object, object]を要求する
    # （tests/unit/sections/test_pipeline_integration.pyと同じ非変性上の制約）。
    stage = cast("PipelineStage[object, object]", FieldExtractor())
    builder.add_stage("field_extractor", stage)
    runner = builder.build()

    job = Job(
        id=JobId(1),
        job_type="core_pipeline",
        pdf_id=PdfId(1),
        parser_version_id=ParserVersionId(1),
        status="running",
        started_at=context.started_at,
        finished_at=None,
        processed_count=0,
        failed_count=0,
        error_summary=None,
    )

    result = runner.run(context, job, initial_input=section)

    assert result.succeeded is True
    assert isinstance(result.events[0].stage_name, str)
