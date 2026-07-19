from typing import cast

from mod_personnel_db.models import (
    Job,
    JobId,
    LayoutArtifact,
    ParserVersionId,
    PdfId,
    SectionParseResult,
)
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage
from mod_personnel_db.sections import SectionParser

from .conftest import make_artifact


def test_section_parser_satisfies_pipeline_stage_protocol() -> None:
    stage: PipelineStage[LayoutArtifact, SectionParseResult] = SectionParser()
    assert stage is not None


def test_section_parser_public_api_is_run_only() -> None:
    public_names = [name for name in dir(SectionParser) if not name.startswith("_")]
    assert public_names == ["run"]


def test_section_parser_runs_inside_pipeline_runner(context: PipelineContext) -> None:
    artifact = make_artifact(("見出し\n本文\n以上",))

    builder = PipelineBuilder()
    # PipelineRunner/BuilderはPipelineStage[object, object]を要求する
    # （tests/unit/layout/test_pipeline_integration.pyと同じ非変性上の制約）。
    stage = cast("PipelineStage[object, object]", SectionParser())
    builder.add_stage("section_parser", stage)
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

    result = runner.run(context, job, initial_input=artifact)

    assert result.succeeded is True
    assert isinstance(result.events[0].stage_name, str)
