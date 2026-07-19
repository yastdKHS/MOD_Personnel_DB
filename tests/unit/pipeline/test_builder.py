import pytest

from mod_personnel_db.models import Job
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineFrameworkError
from mod_personnel_db.pipeline.runner import PipelineRunner

from ._stubs import IdentityStubStage


def test_builder_add_stage_returns_self_for_chaining() -> None:
    builder = PipelineBuilder()

    returned = builder.add_stage("stage_a", IdentityStubStage())

    assert returned is builder


def test_builder_build_produces_runner_with_stages_in_added_order(
    context: PipelineContext, running_job: Job
) -> None:
    builder = PipelineBuilder()
    builder.add_stage("stage_a", IdentityStubStage())
    builder.add_stage("stage_b", IdentityStubStage())

    runner = builder.build()

    assert isinstance(runner, PipelineRunner)
    assert [name for name, _ in runner.stages] == ["stage_a", "stage_b"]


def test_builder_build_with_no_stages_raises() -> None:
    builder = PipelineBuilder()

    with pytest.raises(PipelineFrameworkError):
        builder.build()


def test_builder_rejects_duplicate_stage_names() -> None:
    builder = PipelineBuilder()
    builder.add_stage("stage_a", IdentityStubStage())

    with pytest.raises(PipelineFrameworkError):
        builder.add_stage("stage_a", IdentityStubStage())


def test_builder_built_runner_executes_successfully(
    context: PipelineContext, running_job: Job
) -> None:
    builder = PipelineBuilder()
    builder.add_stage("only", IdentityStubStage())
    runner = builder.build()

    result = runner.run(context, running_job, initial_input="value")

    assert result.succeeded is True
