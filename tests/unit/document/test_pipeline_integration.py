from collections.abc import Callable
from pathlib import Path
from typing import cast

from mod_personnel_db.document import DocumentAnalyzer
from mod_personnel_db.models import Document, Job, JobId, ParserVersionId, PdfId, PdfRecord
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage

from ._pdf_fixtures import normal_pdf_bytes


def test_document_analyzer_satisfies_pipeline_stage_protocol() -> None:
    stage: PipelineStage[PdfRecord, Document] = DocumentAnalyzer()
    assert stage is not None


def test_document_analyzer_public_api_is_run_only() -> None:
    public_names = [name for name in dir(DocumentAnalyzer) if not name.startswith("_")]
    assert public_names == ["run"]


def test_document_analyzer_runs_inside_pipeline_runner(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes())
    record = make_pdf_record(path)

    builder = PipelineBuilder()
    # PipelineRunner/Builderは異種Stageを保持するためPipelineStage[object, object]を
    # 要求する（pipeline/runner.pyの設計、Phase2 Task3完了報告のTODO参照）。
    # DocumentAnalyzerは具体的な型(PdfRecord/Document)を持つためProtocolの非変性上
    # 直接は適合しないが、run()の実引数はPdfRecordであるため実行時は安全にキャスト可能。
    stage = cast("PipelineStage[object, object]", DocumentAnalyzer())
    builder.add_stage("document_analyzer", stage)
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

    result = runner.run(context, job, initial_input=record)

    assert result.succeeded is True
    assert isinstance(result.events[0].stage_name, str)
