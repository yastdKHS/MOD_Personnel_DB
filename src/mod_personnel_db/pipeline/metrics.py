"""実行の定量的なサマリのみを保持する（集計・記録以外の責務を持たない）。

docs/api/pipeline.mdのPipelineMetrics（stage_durations_ms/processed_count/
failed_count/skipped_count）とは異なるフィールド構成である。Phase2 Task3の実装指示
（経過時間・開始時刻・終了時刻・成功フラグ・警告件数・エラー件数の6項目）を優先して
採用し、乖離をPhase2 Task3完了報告のTODOとして明記する（docs/api/pipeline.mdとの
同期は本Taskの承認範囲外であるため未反映）。
"""

from dataclasses import dataclass
from datetime import datetime

from mod_personnel_db.pipeline.exceptions import PipelineFrameworkError


@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    elapsed_ms: float
    started_at: datetime
    finished_at: datetime
    succeeded: bool
    warning_count: int
    error_count: int

    def __post_init__(self) -> None:
        if self.finished_at < self.started_at:
            raise PipelineFrameworkError("finished_at must be >= started_at")
        if self.elapsed_ms < 0:
            raise PipelineFrameworkError("elapsed_ms must be >= 0")
        if self.warning_count < 0 or self.error_count < 0:
            raise PipelineFrameworkError("warning_count/error_count must be >= 0")
        if self.succeeded != (self.error_count == 0):
            raise PipelineFrameworkError("succeeded must equal (error_count == 0)")
