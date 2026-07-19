"""可観測性のためのイベント記録。docs/api/pipeline.md#pipelineevent に対応する。

イベント通知（記録）のみを責務とし、ログ出力・集計自体は行わない
（ログ出力はlogging設計、集計はPipelineMetricsの責務）。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

PipelineEventType = Literal["started", "completed", "failed", "skipped"]


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    """stage_nameはPipelineStage実装クラスの正式名、またはRunner自身のいずれか。"""

    stage_name: str
    event_type: PipelineEventType
    timestamp: datetime
    detail: str | None
