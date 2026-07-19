"""Stageリストを受け取り、順序通りに実行するだけの責務を持つ。

docs/api/pipeline.md#jobrunnerとの関係で説明される調整ロジック（Context生成・
Stage呼び出し・Event記録・Result返却）のうち、Repository永続化を伴わない部分の
骨格をPhase2 Task3で実装する。Repository永続化（Job/Candidateの保存等）は
本Taskの対象外（禁止事項: Repository参照）であり、将来Task（JobRunner本実装）で
本クラスをラップする形になる想定（完了報告の「次Taskへ影響する事項」参照）。

Genericな`PipelineStage[TIn, TOut]`をヘテロな型のStage列として保持する必要が
あるため、`Any`ではなく具体的な型`object`を用いた`PipelineStage[object, object]`
として扱う（docs/api/python-contract.mdの「Anyはmodels/・repositories/・pipeline/の
公開APIに登場させない」を満たすための設計判断。詳細は完了報告参照）。
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from mod_personnel_db.models import Job
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.events import PipelineEvent, PipelineEventType
from mod_personnel_db.pipeline.exceptions import PipelineException
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.pipeline.stage import PipelineStage

NamedStage = tuple[str, PipelineStage[object, object]]


class PipelineRunner:
    """構築時に受け取ったStage列を、常にその順序のまま実行する。"""

    def __init__(self, stages: Sequence[NamedStage]) -> None:
        self._stages: tuple[NamedStage, ...] = tuple(stages)

    @property
    def stages(self) -> tuple[NamedStage, ...]:
        return self._stages

    def run(self, context: PipelineContext, job: Job, initial_input: object) -> PipelineResult:
        events: list[PipelineEvent] = []
        current: object = initial_input
        error: PipelineException | None = None

        for name, stage in self._stages:
            if error is not None:
                events.append(_event(name, "skipped", None))
                continue
            events.append(_event(name, "started", None))
            try:
                current = stage.run(context, current)
            except PipelineException as exc:
                events.append(_event(name, "failed", str(exc)))
                error = exc
            else:
                events.append(_event(name, "completed", None))

        return _build_result(context, job, tuple(events), error)


def _event(stage_name: str, event_type: PipelineEventType, detail: str | None) -> PipelineEvent:
    return PipelineEvent(
        stage_name=stage_name,
        event_type=event_type,
        timestamp=datetime.now(UTC),
        detail=detail,
    )


def _build_result(
    context: PipelineContext,
    job: Job,
    events: tuple[PipelineEvent, ...],
    error: PipelineException | None,
) -> PipelineResult:
    succeeded = error is None
    finished_at = datetime.now(UTC)
    elapsed_ms = (finished_at - context.started_at).total_seconds() * 1000
    metrics = PipelineMetrics(
        elapsed_ms=elapsed_ms,
        started_at=context.started_at,
        finished_at=finished_at,
        succeeded=succeeded,
        warning_count=0,
        error_count=0 if succeeded else 1,
    )
    final_job = replace(
        job,
        status="succeeded" if succeeded else "failed",
        finished_at=finished_at,
        error_summary=None if succeeded else str(error),
    )
    return PipelineResult(
        context=context, job=final_job, events=events, metrics=metrics, error=error
    )
