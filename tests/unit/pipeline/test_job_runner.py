from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.models import Job, ParserVersionId, PdfId, PdfRecord, PipelineStageName
from mod_personnel_db.pipeline import job_runner as job_runner_module
from mod_personnel_db.pipeline.job_runner import JobRunner, JobRunnerRepositories
from mod_personnel_db.pipeline.runner import PipelineRunner

from ._job_runner_stubs import (
    StubJobRepository,
    StubKnowledgeService,
    StubLearningService,
    StubPDFRepository,
    make_stub_stage_class,
)

_STAGE_NAMES = (
    "document_analyzer",
    "layout_detector",
    "section_parser",
    "field_extractor",
    "normalizer",
    "validator",
)


def _make_pdf(pdf_id: int = 1, *, status: str = "fetched") -> PdfRecord:
    return PdfRecord(
        id=PdfId(pdf_id),
        content_hash="a" * 64,
        source_url="https://example.mod.go.jp/appointment.pdf",
        published_date=date(2026, 1, 1),
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        file_path="aa/aa/" + "a" * 64 + ".pdf",
        file_size_bytes=1024,
        status=status,  # type: ignore[arg-type]
    )


def _patch_all_stages_as_recording_stubs(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    for name in _STAGE_NAMES:
        class_name = "".join(part.title() for part in name.split("_"))
        monkeypatch.setattr(job_runner_module, class_name, make_stub_stage_class(name, calls))


def _patch_failing_stage(monkeypatch: pytest.MonkeyPatch, calls: list[str], name: str) -> None:
    """`name`のStageだけPipelineExceptionを送出するStubに差し替える。"""
    from mod_personnel_db.pipeline.exceptions import PipelineException

    class _FailingStub:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            del input
            calls.append(name)
            raise PipelineException(stage_name=name, context=context, message=f"{name} failed")  # type: ignore[arg-type]

    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    class_name = "".join(part.title() for part in name.split("_"))
    monkeypatch.setattr(job_runner_module, class_name, _FailingStub)


_JobRunnerFixture = tuple[
    JobRunner, StubJobRepository, StubPDFRepository, StubKnowledgeService, StubLearningService
]


def _make_job_runner(
    *,
    jobs: StubJobRepository | None = None,
    pdfs: StubPDFRepository | None = None,
    knowledge: StubKnowledgeService | None = None,
    learning: StubLearningService | None = None,
) -> _JobRunnerFixture:
    jobs = jobs if jobs is not None else StubJobRepository()
    pdfs = pdfs if pdfs is not None else StubPDFRepository()
    knowledge = knowledge if knowledge is not None else StubKnowledgeService()
    learning = learning if learning is not None else StubLearningService()
    runner = JobRunner(
        repositories=JobRunnerRepositories(pdfs=pdfs, jobs=jobs),
        knowledge=knowledge,
        learning=learning,
        parser_version_id=ParserVersionId(1),
    )
    return runner, jobs, pdfs, knowledge, learning


def test_stages_registered_and_run_in_correct_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    runner, *_ = _make_job_runner()

    runner.run_for_pdf(_make_pdf())

    assert calls == list(_STAGE_NAMES)


def test_knowledge_service_snapshot_and_rules_fetched(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    runner, _, _, knowledge, _ = _make_job_runner()

    runner.run_for_pdf(_make_pdf())

    assert knowledge.load_snapshot_calls == 1
    assert knowledge.load_validation_rules_calls == 1


def test_pipeline_runner_run_called_exactly_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    runner, *_ = _make_job_runner()

    original_run = PipelineRunner.run
    run_call_count = 0

    def counting_run(
        self: PipelineRunner, context: object, job: object, initial_input: object
    ) -> object:
        nonlocal run_call_count
        run_call_count += 1
        return original_run(self, context, job, initial_input)  # type: ignore[arg-type]

    monkeypatch.setattr(PipelineRunner, "run", counting_run)

    runner.run_for_pdf(_make_pdf())

    assert run_call_count == 1


def test_repository_receives_pipeline_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    runner, jobs, *_ = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert len(jobs.jobs) == 1
    assert len(jobs.updates) == 1
    job_id, status, processed_count, failed_count = jobs.updates[0]
    assert status == result.job.status == "succeeded"
    assert (processed_count, failed_count) == (
        result.job.processed_count,
        result.job.failed_count,
    )
    assert jobs.jobs[int(job_id)].status == "succeeded"


def test_learning_service_delegated_on_stage_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_failing_stage(monkeypatch, calls, "validator")
    runner, jobs, _, _, learning = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert len(learning.recorded) == 1
    assert learning.recorded[0].pipeline_stage == PipelineStageName.VALIDATOR
    assert jobs.updates[0][1] == "failed"


def test_learning_service_not_called_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    runner, _, _, _, learning = _make_job_runner()

    runner.run_for_pdf(_make_pdf())

    assert learning.recorded == []


def test_pipeline_exception_does_not_propagate_out_of_run_for_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PipelineExceptionはPipelineRunner内部で捕捉されPipelineResult.errorへ格納される
    （docs/api/pipeline.md#pipelineexception）。JobRunnerErrorへの変換は行わず、
    run_for_pdf()から例外として送出されることもない。"""
    calls: list[str] = []
    _patch_failing_stage(monkeypatch, calls, "normalizer")
    runner, *_ = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.error is not None
    assert result.succeeded is False


def test_run_pending_processes_all_pending_pdfs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    pending = (_make_pdf(1), _make_pdf(2), _make_pdf(3))
    pdfs = StubPDFRepository(pending=pending)
    runner, jobs, *_ = _make_job_runner(pdfs=pdfs)

    results = runner.run_pending()

    assert len(results) == 3
    assert len(jobs.jobs) == 3


def test_get_job_delegates_to_job_repository() -> None:
    jobs = StubJobRepository()
    runner, *_ = _make_job_runner(jobs=jobs)

    assert runner.get_job(jobs.add(_running_job_for_lookup())) is not None


def _running_job_for_lookup() -> Job:
    return Job(
        id=None,
        job_type="core_pipeline",
        pdf_id=PdfId(1),
        parser_version_id=ParserVersionId(1),
        status="running",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at=None,
        processed_count=0,
        failed_count=0,
        error_summary=None,
    )


def test_knowledge_service_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    knowledge = StubKnowledgeService(fail=True)
    runner, jobs, *_ = _make_job_runner(knowledge=knowledge)

    with pytest.raises(RuntimeError, match="KnowledgeService.load_snapshot failed"):
        runner.run_for_pdf(_make_pdf())

    # Jobは生成済み（永続化された）が、失敗によりstatus更新には至らない。
    assert len(jobs.jobs) == 1
    assert jobs.updates == []
    assert calls == []


def test_job_repository_add_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_all_stages_as_recording_stubs(monkeypatch, calls)
    jobs = StubJobRepository(add_should_fail=True)
    runner, *_ = _make_job_runner(jobs=jobs)

    with pytest.raises(RuntimeError, match="JobRepository.add failed"):
        runner.run_for_pdf(_make_pdf())

    assert calls == []


def test_learning_service_not_called_for_unmapped_stage_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`document_analyzer`は`PipelineStageName`に対応する値を持たないため
    （models/enums.py）、失敗してもLearning記録は行わない。"""
    calls: list[str] = []
    _patch_failing_stage(monkeypatch, calls, "document_analyzer")
    runner, jobs, _, _, learning = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert learning.recorded == []
    assert jobs.updates[0][1] == "failed"


def test_job_runner_public_api_matches_protocol() -> None:
    public_names = {name for name in dir(JobRunner) if not name.startswith("_")}

    assert public_names == {"run_for_pdf", "run_pending", "get_job"}
