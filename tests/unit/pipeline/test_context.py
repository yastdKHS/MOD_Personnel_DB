from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import JobId, ParserVersionId
from mod_personnel_db.pipeline.context import PipelineContext


def test_context_holds_given_values() -> None:
    started_at = datetime(2026, 7, 19, tzinfo=UTC)

    context = PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(2),
        correlation_id="corr-abc",
        started_at=started_at,
    )

    assert context.job_id == JobId(1)
    assert context.parser_version_id == ParserVersionId(2)
    assert context.correlation_id == "corr-abc"
    assert context.started_at == started_at


def test_context_is_frozen(context: PipelineContext) -> None:
    with pytest.raises(FrozenInstanceError):
        # frozen dataclassへの代入不可を実行時に確認する意図的な違反のためignore。
        context.correlation_id = "changed"  # type: ignore[misc]
