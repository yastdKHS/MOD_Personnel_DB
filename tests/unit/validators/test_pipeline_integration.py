from typing import cast

from mod_personnel_db.models import (
    Job,
    JobId,
    NormalizedRecord,
    ParserVersionId,
    PdfId,
    ValidationResult,
)
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.stage import PipelineStage
from mod_personnel_db.validators import Validator

from .conftest import make_knowledge, make_record, make_rule_set


def test_validator_satisfies_pipeline_stage_protocol() -> None:
    stage: PipelineStage[NormalizedRecord, ValidationResult] = Validator(
        make_rule_set(), make_knowledge()
    )
    assert stage is not None


def test_validator_public_api_is_run_only() -> None:
    public_names = [name for name in dir(Validator) if not name.startswith("_")]
    assert public_names == ["run"]


def test_validator_runs_inside_pipeline_runner(context: PipelineContext) -> None:
    record = make_record({"column_1": "陸将補"})

    builder = PipelineBuilder()
    # PipelineRunner/Builderはstage.run(context, current)という単一入力呼び出ししか
    # 行わないため、ValidationRuleSet/KnowledgeSnapshotはコンストラクタ注入とする
    # （ADR-0041/ADR-0043）。
    stage = cast("PipelineStage[object, object]", Validator(make_rule_set(), make_knowledge()))
    builder.add_stage("validator", stage)
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
