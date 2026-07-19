from typing import cast

from mod_personnel_db.models import (
    Job,
    JobId,
    NormalizationResult,
    ParserVersionId,
    PdfId,
    RawRecord,
)
from mod_personnel_db.normalizers import Normalizer
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage

from .conftest import make_knowledge, make_record


def test_normalizer_satisfies_pipeline_stage_protocol() -> None:
    stage: PipelineStage[RawRecord, NormalizationResult] = Normalizer(make_knowledge())
    assert stage is not None


def test_normalizer_public_api_is_run_only() -> None:
    public_names = [name for name in dir(Normalizer) if not name.startswith("_")]
    assert public_names == ["run"]


def test_normalizer_runs_inside_pipeline_runner(context: PipelineContext) -> None:
    record = make_record({"column_1": "山田太郎"})

    builder = PipelineBuilder()
    # PipelineRunner/Builderはstage.run(context, current)という単一入力呼び出ししか
    # 行わないため、KnowledgeSnapshotはコンストラクタ注入とする（ADR-0040）。
    stage = cast("PipelineStage[object, object]", Normalizer(make_knowledge()))
    builder.add_stage("normalizer", stage)
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
