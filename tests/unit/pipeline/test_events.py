from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from mod_personnel_db.pipeline.events import PipelineEvent, PipelineEventType


@pytest.mark.parametrize("event_type", ["started", "completed", "failed", "skipped"])
def test_event_accepts_all_documented_event_types(event_type: PipelineEventType) -> None:
    event = PipelineEvent(
        stage_name="normalizer",
        event_type=event_type,
        timestamp=datetime(2026, 7, 19, tzinfo=UTC),
        detail=None,
    )

    assert event.event_type == event_type


def test_event_detail_is_optional() -> None:
    event = PipelineEvent(
        stage_name="validator",
        event_type="failed",
        timestamp=datetime(2026, 7, 19, tzinfo=UTC),
        detail="boundary violation",
    )

    assert event.detail == "boundary violation"


def test_event_is_frozen() -> None:
    event = PipelineEvent(
        stage_name="validator",
        event_type="started",
        timestamp=datetime(2026, 7, 19, tzinfo=UTC),
        detail=None,
    )

    with pytest.raises(FrozenInstanceError):
        # frozen dataclassへの代入不可を実行時に確認する意図的な違反のためignore。
        event.detail = "changed"  # type: ignore[misc]
