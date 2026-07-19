from collections.abc import Callable
from pathlib import Path
from typing import cast

from mod_personnel_db.layout import LayoutDetector
from mod_personnel_db.models import (
    Document,
    Job,
    JobId,
    LayoutArtifact,
    ParserVersionId,
    PdfId,
)
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage

from ._layout_fixtures import format_a_definition
from ._pdf_fixtures import text_pdf_bytes


def test_layout_detector_satisfies_pipeline_stage_protocol() -> None:
    stage: PipelineStage[Document, LayoutArtifact] = LayoutDetector(layout_definitions=())
    assert stage is not None


def test_layout_detector_public_api_is_run_only() -> None:
    public_names = [name for name in dir(LayoutDetector) if not name.startswith("_")]
    assert public_names == ["run"]


def test_layout_detector_runs_inside_pipeline_runner(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)

    builder = PipelineBuilder()
    # PipelineRunner/BuilderはPipelineStage[object, object]を要求する
    # （tests/unit/document/test_pipeline_integration.pyと同じ非変性上の制約）。
    stage = cast(
        "PipelineStage[object, object]",
        LayoutDetector(layout_definitions=(format_a_definition(),)),
    )
    builder.add_stage("layout_detector", stage)
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

    result = runner.run(context, job, initial_input=document)

    assert result.succeeded is True
    assert isinstance(result.events[0].stage_name, str)
