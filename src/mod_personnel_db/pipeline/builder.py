"""Stageの登録によるPipelineRunnerの構築のみを責務とする（Stage実行は行わない）。"""

from __future__ import annotations

from mod_personnel_db.pipeline.exceptions import PipelineFrameworkError
from mod_personnel_db.pipeline.runner import NamedStage, PipelineRunner
from mod_personnel_db.pipeline.stage import PipelineStage


class PipelineBuilder:
    """`.add_stage(...)`を連鎖させてStage列を組み立て、`.build()`でRunnerを得る。"""

    def __init__(self) -> None:
        self._stages: list[NamedStage] = []

    def add_stage(self, name: str, stage: PipelineStage[object, object]) -> PipelineBuilder:
        if any(existing_name == name for existing_name, _ in self._stages):
            raise PipelineFrameworkError(f"duplicate stage name: {name}")
        self._stages.append((name, stage))
        return self

    def build(self) -> PipelineRunner:
        if not self._stages:
            raise PipelineFrameworkError("cannot build PipelineRunner with zero stages")
        return PipelineRunner(self._stages)
