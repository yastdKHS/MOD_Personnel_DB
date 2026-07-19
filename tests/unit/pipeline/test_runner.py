import pytest

from mod_personnel_db.models import Job
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.runner import PipelineRunner

from ._stubs import CrashingStubStage, FailingStubStage, IdentityStubStage, RecordingStubStage


def test_runner_executes_stages_in_given_order(context: PipelineContext, running_job: Job) -> None:
    first = RecordingStubStage(label="first")
    second = RecordingStubStage(label="second")
    third = RecordingStubStage(label="third")
    runner = PipelineRunner([("first", first), ("second", second), ("third", third)])

    result = runner.run(context, running_job, initial_input="input")

    assert first.calls == ["first"]
    assert second.calls == ["second"]
    assert third.calls == ["third"]
    assert [event.stage_name for event in result.events if event.event_type == "started"] == [
        "first",
        "second",
        "third",
    ]


def test_runner_passes_output_of_each_stage_to_the_next(
    context: PipelineContext, running_job: Job
) -> None:
    class AppendStage:
        def __init__(self, suffix: str) -> None:
            self._suffix = suffix

        def run(self, context: PipelineContext, input: object) -> object:
            return f"{input}-{self._suffix}"

    runner = PipelineRunner([("a", AppendStage("a")), ("b", AppendStage("b"))])

    result = runner.run(context, running_job, initial_input="start")

    assert result.succeeded is True
    assert result.job.status == "succeeded"


def test_runner_succeeds_with_empty_stage_list(context: PipelineContext, running_job: Job) -> None:
    runner = PipelineRunner([])

    result = runner.run(context, running_job, initial_input="input")

    assert result.succeeded is True
    assert result.events == ()


def test_runner_records_pipeline_exception_as_result_error(
    context: PipelineContext, running_job: Job
) -> None:
    runner = PipelineRunner([("failing", FailingStubStage(message="bad value"))])

    result = runner.run(context, running_job, initial_input="input")

    assert result.succeeded is False
    assert result.error is not None
    assert result.error.stage_name == "failing_stub"
    assert result.job.status == "failed"
    assert result.job.error_summary == "bad value"


def test_runner_stops_and_skips_remaining_stages_after_failure(
    context: PipelineContext, running_job: Job
) -> None:
    after = RecordingStubStage(label="after")
    runner = PipelineRunner(
        [
            ("failing", FailingStubStage()),
            ("after", after),
        ]
    )

    result = runner.run(context, running_job, initial_input="input")

    assert after.calls == []
    skipped = [event for event in result.events if event.event_type == "skipped"]
    assert [event.stage_name for event in skipped] == ["after"]


def test_runner_propagates_unclassified_exceptions(
    context: PipelineContext, running_job: Job
) -> None:
    runner = PipelineRunner([("crashing", CrashingStubStage())])

    with pytest.raises(RuntimeError):
        runner.run(context, running_job, initial_input="input")


def test_runner_exposes_stages_property_in_construction_order() -> None:
    stages = [
        ("identity_1", IdentityStubStage()),
        ("identity_2", IdentityStubStage()),
        ("identity_3", IdentityStubStage()),
    ]
    runner = PipelineRunner(stages)

    assert [name for name, _ in runner.stages] == ["identity_1", "identity_2", "identity_3"]
