from mod_personnel_db.models import Job
from mod_personnel_db.pipeline.builder import PipelineBuilder
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.factory import PipelineFactory

from ._stubs import IdentityStubStage


def test_factory_creates_a_new_builder_instance() -> None:
    first = PipelineFactory.create_builder()
    second = PipelineFactory.create_builder()

    assert isinstance(first, PipelineBuilder)
    assert isinstance(second, PipelineBuilder)
    assert first is not second


def test_factory_created_builder_is_independent_and_usable(
    context: PipelineContext, running_job: Job
) -> None:
    builder = PipelineFactory.create_builder()
    builder.add_stage("only", IdentityStubStage())
    runner = builder.build()

    result = runner.run(context, running_job, initial_input="value")

    assert result.succeeded is True
