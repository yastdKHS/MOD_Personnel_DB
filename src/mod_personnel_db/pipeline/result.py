"""1件のPDF処理（またはその一部）の結果を保持する。docs/api/pipeline.md#pipelineresult に対応する。

Stage実行結果を保持するのみが責務であり、Stage実行そのものはPipelineRunnerが行う。
"""

from dataclasses import dataclass

from mod_personnel_db.models import Job
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.events import PipelineEvent
from mod_personnel_db.pipeline.exceptions import PipelineException, PipelineFrameworkError
from mod_personnel_db.pipeline.metrics import PipelineMetrics


@dataclass(frozen=True, slots=True)
class PipelineResult:
    context: PipelineContext
    job: Job
    events: tuple[PipelineEvent, ...]
    metrics: PipelineMetrics
    error: PipelineException | None

    def __post_init__(self) -> None:
        has_error = self.error is not None
        is_failed_job = self.job.status == "failed"
        if has_error != is_failed_job:
            raise PipelineFrameworkError("error is not None must equal job.status == 'failed'")

    @property
    def succeeded(self) -> bool:
        return self.error is None
