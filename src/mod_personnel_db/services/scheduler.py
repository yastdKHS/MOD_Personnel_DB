"""Scheduler契約の標準実装。Phase7 Task17-3に対応する。

docs/api/interfaces.md#scheduler が定める`Scheduler`Protocol
（`trigger_now(job_type: str) -> JobId`／`list_upcoming() -> tuple[str, ...]`）を
実装する。Phase7 Task17-0（docs/phase7-integration-design.md「12. Scheduler導入
予定位置」）が整理した責務境界に従い、本モジュールは「いつ`JobOrchestrator`を
呼び出すか」の決定にのみ責務を持ち、`JobOrchestrator`（`services/__init__.py`が
定めるProtocol）にのみ依存する。`JobRunner`・`ReviewService`・`ExportService`・
`FetchClient`・`FTPClient`・Repositoryのいずれにも直接依存しない
（それらは`services/orchestrator.py`の`DefaultJobOrchestrator`が既に束ねており、
本モジュールはその向こう側を一切知らない）。

現在時刻の取得は、テスト容易性の確保と`datetime.now()`直接呼び出し禁止のため、
コンストラクタで注入される`clock: Callable[[], datetime]`経由でのみ行う。

cron式のパーサ等の外部ライブラリは用いない。`JobSchedule`は起点時刻
（`anchor`）からの固定間隔（`interval`）による単純な周期表現のみをサポートし、
標準ライブラリの`datetime`/`timedelta`のみで実装する。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from mod_personnel_db.models import JobId

if TYPE_CHECKING:
    from mod_personnel_db.services import JobOrchestrator

#: `trigger_now()`が受け付ける唯一の`job_type`。`JobOrchestrator`が公開する
#: メソッドのうち、追加の引数（PDF・URL・出力先等）なしに呼び出せ、かつ
#: `JobId`を持つ`Job`を生成しうるのは`run_pending_pipeline()`のみであるため、
#: 現時点ではこの1種類に限定する。
RUN_PENDING_JOB_TYPE = "run_pending_pipeline"


class SchedulerError(Exception):
    """`services.scheduler`の全カスタム例外の基底クラス。"""


class UnknownJobTypeError(SchedulerError):
    """`trigger_now()`に未対応の`job_type`が渡された場合。"""


class NoPendingJobError(SchedulerError):
    """`trigger_now()`実行時点で処理対象のPDFが1件も存在しなかった場合。

    `Scheduler.trigger_now()`の戻り値型は`JobId`（`JobId | None`ではない）
    であるため、返すべき`JobId`が存在しない場合は例外で表現する。
    """


@dataclass(frozen=True, slots=True)
class JobSchedule:
    """周期実行対象1件の定義。`job_type`は`trigger_now()`が受け付ける値と対応する。

    cron式は用いず、起点時刻`anchor`から`interval`ごとに実行される、という
    単純な固定間隔モデルのみを表現する。
    """

    job_type: str
    interval: timedelta
    anchor: datetime

    def __post_init__(self) -> None:
        if self.interval <= timedelta(0):
            raise SchedulerError("JobSchedule.interval must be positive")
        if self.anchor.tzinfo is None:
            raise SchedulerError("JobSchedule.anchor must be timezone-aware")

    def next_run_at(self, now: datetime) -> datetime:
        """`now`以降で最初にこのスケジュールが実行される時刻を返す。"""
        if now <= self.anchor:
            return self.anchor
        elapsed_intervals = (now - self.anchor) // self.interval
        candidate = self.anchor + elapsed_intervals * self.interval
        if candidate < now:
            candidate += self.interval
        return candidate


class DefaultScheduler:
    """`Scheduler`Protocolの標準実装。`JobOrchestrator`のみに依存する。

    コンストラクタは`orchestrator`（`JobOrchestrator`）・`schedules`
    （周期実行対象の一覧）・`clock`（現在時刻を返すCallable）をすべて
    引数として受け取り、内部で新たな具象実装を生成しない
    （Constructor Injectionのみで依存を解決する）。
    """

    def __init__(
        self,
        orchestrator: JobOrchestrator,
        schedules: tuple[JobSchedule, ...],
        clock: Callable[[], datetime],
    ) -> None:
        self._orchestrator = orchestrator
        self._schedules = schedules
        self._clock = clock

    def trigger_now(self, job_type: str) -> JobId:
        """`job_type`に対応する`JobOrchestrator`の処理を即座に実行する。

        現時点でサポートする`job_type`は`RUN_PENDING_JOB_TYPE`のみであり、
        `JobOrchestrator.run_pending_pipeline()`を呼び出す。未処理PDFが
        存在せず結果が空の場合は`NoPendingJobError`を送出する。複数件処理
        された場合は、先頭（最初に処理された）`PipelineResult`の`Job.id`を
        本トリガー呼び出しを代表する`JobId`として返す。
        """
        if job_type != RUN_PENDING_JOB_TYPE:
            raise UnknownJobTypeError(f"unknown job_type: {job_type!r}")
        results = self._orchestrator.run_pending_pipeline()
        if not results:
            raise NoPendingJobError("no pending pdf to process")
        job_id = results[0].job.id
        if job_id is None:
            raise SchedulerError("triggered job has no id")
        return job_id

    def list_upcoming(self) -> tuple[str, ...]:
        """登録済み`JobSchedule`それぞれの次回実行予定時刻を文字列化して返す。"""
        now = self._clock()
        return tuple(
            f"{schedule.job_type} at {schedule.next_run_at(now).isoformat()}"
            for schedule in self._schedules
        )


__all__ = [
    "RUN_PENDING_JOB_TYPE",
    "DefaultScheduler",
    "JobSchedule",
    "NoPendingJobError",
    "SchedulerError",
    "UnknownJobTypeError",
]
