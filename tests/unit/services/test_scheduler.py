"""`DefaultScheduler`の単体テスト（Phase7 Task17-3）。

`Scheduler`Protocol（docs/api/interfaces.md#scheduler）の`trigger_now()`/
`list_upcoming()`契約に一致すること、`JobOrchestrator`のみに依存し
`JobRunner`/`ReviewService`/`ExportService`/`FetchClient`/`FTPClient`/
Repositoryのいずれにも直接依存しないこと、現在時刻の取得が注入された
`clock`経由のみで行われること（`datetime.now()`を直接呼び出さないこと）を
検証する。
"""

import ast
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

import mod_personnel_db.services.scheduler as scheduler_module
from mod_personnel_db.fetch import FetchRequest
from mod_personnel_db.models import (
    ExportArtifact,
    ExportFormat,
    Job,
    JobId,
    LearningRecord,
    ParserVersionId,
    PdfId,
    PdfRecord,
)
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineException
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.services import (
    RUN_PENDING_JOB_TYPE,
    DefaultScheduler,
    FetchWorkItem,
    JobSchedule,
    NoPendingJobError,
    Scheduler,
    SchedulerError,
    UnknownJobTypeError,
    WorkflowResult,
)


def _pipeline_result(job_id: int, *, succeeded: bool = True) -> PipelineResult:
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    finished_at = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
    job = Job(
        id=JobId(job_id),
        job_type="core_pipeline",
        pdf_id=PdfId(job_id),
        parser_version_id=ParserVersionId(1),
        status="succeeded" if succeeded else "failed",
        started_at=started_at,
        finished_at=finished_at,
        processed_count=1 if succeeded else 0,
        failed_count=0 if succeeded else 1,
        error_summary=None,
    )
    context = PipelineContext(
        job_id=JobId(job_id),
        parser_version_id=ParserVersionId(1),
        correlation_id=f"job-{job_id}",
        started_at=started_at,
    )
    metrics = PipelineMetrics(
        elapsed_ms=1000.0,
        started_at=started_at,
        finished_at=finished_at,
        succeeded=succeeded,
        warning_count=0,
        error_count=0 if succeeded else 1,
    )
    error = PipelineException("validator", context, "boom") if not succeeded else None
    return PipelineResult(context=context, job=job, events=(), metrics=metrics, error=error)


class _StubJobOrchestrator:
    """`JobOrchestrator`Protocolを満たすStub。`run_pending_pipeline()`の
    呼び出し回数・戻り値のみを制御する（他のメソッドは本テストで未使用のため
    `NotImplementedError`とする）。
    """

    def __init__(self, results: tuple[PipelineResult, ...] = ()) -> None:
        self._results = results
        self.run_pending_pipeline_call_count = 0

    def fetch_and_stage(
        self, request: FetchRequest, *, destination_path: str, published_date: date
    ) -> PdfId | None:
        raise NotImplementedError

    def run_job(self, pdf: PdfRecord) -> PipelineResult:
        raise NotImplementedError

    def run_pending_pipeline(self) -> tuple[PipelineResult, ...]:
        self.run_pending_pipeline_call_count += 1
        return self._results

    def list_pending_reviews(self) -> tuple[LearningRecord, ...]:
        raise NotImplementedError

    def export_and_publish(
        self,
        export_format: ExportFormat,
        destination: str | Path,
        *,
        remote_path: str | None = None,
    ) -> ExportArtifact:
        raise NotImplementedError

    def run_workflow(
        self,
        fetch_items: list[FetchWorkItem],
        export_format: ExportFormat,
        export_destination: str | Path,
        *,
        remote_path: str | None = None,
    ) -> WorkflowResult:
        raise NotImplementedError


def _fixed_clock(now: datetime) -> Callable[[], datetime]:
    return lambda: now


# --- Protocol整合 ---


def test_scheduler_satisfies_scheduler_protocol() -> None:
    scheduler: Scheduler = DefaultScheduler(
        _StubJobOrchestrator(), (), _fixed_clock(datetime(2026, 1, 1, tzinfo=UTC))
    )
    assert isinstance(scheduler, DefaultScheduler)


# --- trigger_now() ---


def test_trigger_now_calls_run_pending_pipeline_and_returns_first_job_id() -> None:
    orchestrator = _StubJobOrchestrator((_pipeline_result(1), _pipeline_result(2)))
    scheduler = DefaultScheduler(orchestrator, (), _fixed_clock(datetime(2026, 1, 1, tzinfo=UTC)))

    job_id = scheduler.trigger_now(RUN_PENDING_JOB_TYPE)

    assert job_id == JobId(1)
    assert orchestrator.run_pending_pipeline_call_count == 1


def test_trigger_now_raises_no_pending_job_error_when_nothing_to_process() -> None:
    orchestrator = _StubJobOrchestrator(())
    scheduler = DefaultScheduler(orchestrator, (), _fixed_clock(datetime(2026, 1, 1, tzinfo=UTC)))

    with pytest.raises(NoPendingJobError):
        scheduler.trigger_now(RUN_PENDING_JOB_TYPE)


def test_trigger_now_raises_unknown_job_type_error_for_unsupported_job_type() -> None:
    orchestrator = _StubJobOrchestrator((_pipeline_result(1),))
    scheduler = DefaultScheduler(orchestrator, (), _fixed_clock(datetime(2026, 1, 1, tzinfo=UTC)))

    with pytest.raises(UnknownJobTypeError):
        scheduler.trigger_now("nonexistent_job_type")
    assert orchestrator.run_pending_pipeline_call_count == 0


# --- list_upcoming() ---


def test_list_upcoming_uses_injected_clock_not_wall_clock() -> None:
    anchor = datetime(2020, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(
        job_type=RUN_PENDING_JOB_TYPE, interval=timedelta(hours=1), anchor=anchor
    )
    fixed_now = datetime(2020, 1, 1, 2, 30, tzinfo=UTC)
    scheduler = DefaultScheduler(_StubJobOrchestrator(), (schedule,), _fixed_clock(fixed_now))

    upcoming = scheduler.list_upcoming()

    assert upcoming == (f"{RUN_PENDING_JOB_TYPE} at 2020-01-01T03:00:00+00:00",)


def test_list_upcoming_returns_one_entry_per_schedule_in_order() -> None:
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule_a = JobSchedule(job_type="a", interval=timedelta(hours=1), anchor=anchor)
    schedule_b = JobSchedule(job_type="b", interval=timedelta(minutes=30), anchor=anchor)
    scheduler = DefaultScheduler(
        _StubJobOrchestrator(), (schedule_a, schedule_b), _fixed_clock(anchor)
    )

    upcoming = scheduler.list_upcoming()

    assert len(upcoming) == 2
    assert upcoming[0].startswith("a at ")
    assert upcoming[1].startswith("b at ")


def test_list_upcoming_with_no_schedules_returns_empty_tuple() -> None:
    scheduler = DefaultScheduler(
        _StubJobOrchestrator(), (), _fixed_clock(datetime(2026, 1, 1, tzinfo=UTC))
    )

    assert scheduler.list_upcoming() == ()


# --- JobSchedule.next_run_at() ---


def test_job_schedule_next_run_at_returns_anchor_when_now_before_anchor() -> None:
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(job_type="x", interval=timedelta(hours=1), anchor=anchor)

    assert schedule.next_run_at(anchor - timedelta(days=1)) == anchor


def test_job_schedule_next_run_at_returns_anchor_when_now_equals_anchor() -> None:
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(job_type="x", interval=timedelta(hours=1), anchor=anchor)

    assert schedule.next_run_at(anchor) == anchor


def test_job_schedule_next_run_at_advances_by_whole_intervals() -> None:
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(job_type="x", interval=timedelta(hours=1), anchor=anchor)

    # anchorから2時間15分後 -> 直近の実行時刻(anchor+2h)は過去なので、次はanchor+3h
    now = anchor + timedelta(hours=2, minutes=15)
    assert schedule.next_run_at(now) == anchor + timedelta(hours=3)


def test_job_schedule_next_run_at_exactly_on_interval_boundary() -> None:
    anchor = datetime(2026, 1, 1, tzinfo=UTC)
    schedule = JobSchedule(job_type="x", interval=timedelta(hours=1), anchor=anchor)

    now = anchor + timedelta(hours=2)
    assert schedule.next_run_at(now) == now


def test_job_schedule_rejects_non_positive_interval() -> None:
    with pytest.raises(SchedulerError):
        JobSchedule(job_type="x", interval=timedelta(0), anchor=datetime(2026, 1, 1, tzinfo=UTC))


def test_job_schedule_rejects_naive_anchor() -> None:
    with pytest.raises(SchedulerError):
        JobSchedule(job_type="x", interval=timedelta(hours=1), anchor=datetime(2026, 1, 1))


# --- 依存境界: JobOrchestratorのみに依存する ---

_FORBIDDEN_TOP_LEVEL_PACKAGES = {
    "cli",
    "config",
    "export",
    "features",
    "fetch",
    "ftp",
    "knowledge",
    "learning",
    "pipeline",
    "repositories",
    "review",
}


def _imported_top_level_packages(source_path: Path, *, runtime_only: bool) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if runtime_only and _is_under_type_checking_guard(tree, node):
            continue
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("mod_personnel_db.")
        ):
            imported.add(node.module.split(".")[1])
    return imported


def _is_under_type_checking_guard(tree: ast.Module, node: ast.AST) -> bool:
    for parent in ast.walk(tree):
        if (
            isinstance(parent, ast.If)
            and isinstance(parent.test, ast.Name)
            and parent.test.id == "TYPE_CHECKING"
            and node in ast.walk(parent)
        ):
            return True
    return False


def test_scheduler_module_does_not_import_forbidden_packages_at_runtime() -> None:
    """`services/scheduler.py`が実行時に`JobRunner`・`ReviewService`・`ExportService`・
    `FetchClient`・`FTPClient`・Repository等（`JobOrchestrator`が既に束ねる相手）を
    直接importしないことを確認する（`TYPE_CHECKING`配下の型チェック専用importは
    循環import回避のためのものであり対象外とする）。
    """
    source_path = Path(scheduler_module.__file__)

    imported = _imported_top_level_packages(source_path, runtime_only=True)

    violations = imported & _FORBIDDEN_TOP_LEVEL_PACKAGES
    assert not violations, f"scheduler.py imports forbidden packages at runtime: {violations}"


def test_scheduler_module_does_not_call_datetime_now_directly() -> None:
    """`datetime.now()`の直接呼び出しが存在しないことをASTで確認する
    （現在時刻取得はコンストラクタ注入された`clock`経由のみとする）。
    """
    source_path = Path(scheduler_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    violations = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "now"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "datetime"
    ]
    assert not violations, "scheduler.py calls datetime.now() directly"


def test_default_scheduler_constructor_only_assigns_injected_dependencies() -> None:
    """`DefaultScheduler.__init__`が引数の属性代入のみを行い、新規オブジェクトを
    生成しないことをASTで確認する（Constructor Injectionのみで依存を解決する）。
    """
    source_path = Path(scheduler_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "DefaultScheduler"
    )
    init_node = next(
        node
        for node in ast.walk(class_node)
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    calls_in_init = [n for n in ast.walk(init_node) if isinstance(n, ast.Call)]
    assert calls_in_init == []
