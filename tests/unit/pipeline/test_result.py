from dataclasses import replace
from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import Job
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineException, PipelineFrameworkError
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult

_STARTED = datetime(2026, 7, 19, 9, 0, 0, tzinfo=UTC)
_FINISHED = datetime(2026, 7, 19, 9, 0, 1, tzinfo=UTC)


def _metrics(*, succeeded: bool) -> PipelineMetrics:
    return PipelineMetrics(
        elapsed_ms=100.0,
        started_at=_STARTED,
        finished_at=_FINISHED,
        succeeded=succeeded,
        warning_count=0,
        error_count=0 if succeeded else 1,
    )


def test_result_succeeded_true_when_no_error(context: PipelineContext, running_job: Job) -> None:
    succeeded_job = replace(running_job, status="succeeded", finished_at=_FINISHED)

    result = PipelineResult(
        context=context,
        job=succeeded_job,
        events=(),
        metrics=_metrics(succeeded=True),
        error=None,
    )

    assert result.succeeded is True


def test_result_succeeded_false_when_error_present(
    context: PipelineContext, running_job: Job
) -> None:
    error = PipelineException(stage_name="validator", context=context, message="invalid")
    failed_job = replace(
        running_job, status="failed", finished_at=_FINISHED, error_summary="invalid"
    )

    result = PipelineResult(
        context=context,
        job=failed_job,
        events=(),
        metrics=_metrics(succeeded=False),
        error=error,
    )

    assert result.succeeded is False
    assert result.error is error


def test_result_rejects_error_without_failed_job_status(
    context: PipelineContext, running_job: Job
) -> None:
    error = PipelineException(stage_name="validator", context=context, message="invalid")
    succeeded_job = replace(running_job, status="succeeded", finished_at=_FINISHED)

    with pytest.raises(PipelineFrameworkError):
        PipelineResult(
            context=context,
            job=succeeded_job,
            events=(),
            metrics=_metrics(succeeded=False),
            error=error,
        )


def test_result_rejects_failed_job_status_without_error(
    context: PipelineContext, running_job: Job
) -> None:
    failed_job = replace(running_job, status="failed", finished_at=_FINISHED)

    with pytest.raises(PipelineFrameworkError):
        PipelineResult(
            context=context,
            job=failed_job,
            events=(),
            metrics=_metrics(succeeded=True),
            error=None,
        )
