from datetime import UTC, datetime

import pytest

from mod_personnel_db.pipeline.exceptions import PipelineFrameworkError
from mod_personnel_db.pipeline.metrics import PipelineMetrics

_STARTED = datetime(2026, 7, 19, 9, 0, 0, tzinfo=UTC)
_FINISHED = datetime(2026, 7, 19, 9, 0, 1, tzinfo=UTC)


def test_metrics_normal_success_case() -> None:
    metrics = PipelineMetrics(
        elapsed_ms=1000.0,
        started_at=_STARTED,
        finished_at=_FINISHED,
        succeeded=True,
        warning_count=0,
        error_count=0,
    )

    assert metrics.succeeded is True
    assert metrics.error_count == 0


def test_metrics_normal_failure_case() -> None:
    metrics = PipelineMetrics(
        elapsed_ms=500.0,
        started_at=_STARTED,
        finished_at=_FINISHED,
        succeeded=False,
        warning_count=2,
        error_count=1,
    )

    assert metrics.succeeded is False
    assert metrics.warning_count == 2


def test_metrics_rejects_finished_before_started() -> None:
    with pytest.raises(PipelineFrameworkError):
        PipelineMetrics(
            elapsed_ms=0.0,
            started_at=_FINISHED,
            finished_at=_STARTED,
            succeeded=True,
            warning_count=0,
            error_count=0,
        )


def test_metrics_rejects_negative_elapsed_ms() -> None:
    with pytest.raises(PipelineFrameworkError):
        PipelineMetrics(
            elapsed_ms=-1.0,
            started_at=_STARTED,
            finished_at=_FINISHED,
            succeeded=True,
            warning_count=0,
            error_count=0,
        )


def test_metrics_rejects_negative_warning_count() -> None:
    with pytest.raises(PipelineFrameworkError):
        PipelineMetrics(
            elapsed_ms=0.0,
            started_at=_STARTED,
            finished_at=_FINISHED,
            succeeded=True,
            warning_count=-1,
            error_count=0,
        )


def test_metrics_rejects_negative_error_count() -> None:
    with pytest.raises(PipelineFrameworkError):
        PipelineMetrics(
            elapsed_ms=0.0,
            started_at=_STARTED,
            finished_at=_FINISHED,
            succeeded=False,
            warning_count=0,
            error_count=-1,
        )


def test_metrics_rejects_succeeded_true_with_nonzero_error_count() -> None:
    with pytest.raises(PipelineFrameworkError):
        PipelineMetrics(
            elapsed_ms=0.0,
            started_at=_STARTED,
            finished_at=_FINISHED,
            succeeded=True,
            warning_count=0,
            error_count=1,
        )


def test_metrics_rejects_succeeded_false_with_zero_error_count() -> None:
    with pytest.raises(PipelineFrameworkError):
        PipelineMetrics(
            elapsed_ms=0.0,
            started_at=_STARTED,
            finished_at=_FINISHED,
            succeeded=False,
            warning_count=0,
            error_count=0,
        )


def test_metrics_boundary_zero_elapsed_ms_is_valid() -> None:
    metrics = PipelineMetrics(
        elapsed_ms=0.0,
        started_at=_STARTED,
        finished_at=_STARTED,
        succeeded=True,
        warning_count=0,
        error_count=0,
    )

    assert metrics.elapsed_ms == 0.0
