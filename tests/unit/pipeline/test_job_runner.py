from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.models import Job, ParserVersionId, PdfId, PdfRecord, PipelineStageName
from mod_personnel_db.pipeline import job_runner as job_runner_module
from mod_personnel_db.pipeline.job_runner import JobRunner, JobRunnerRepositories
from mod_personnel_db.pipeline.runner import PipelineRunner

from ._job_runner_stubs import (
    StubCandidateRepository,
    StubJobRepository,
    StubKnowledgeService,
    StubLearningService,
    StubPDFRepository,
    make_field_extractor_stub_class,
    make_normalizer_stub_class,
    make_section_parser_stub_class,
    make_stub_stage_class,
    make_validator_stub_class,
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


@dataclass(frozen=True)
class _FailureConfig:
    """`_patch_stages`の失敗シナリオ指定（引数個数削減のための集約）。"""

    sections: frozenset[int] = frozenset()
    normalizer_records: frozenset[int] = frozenset()
    validator_records: frozenset[int] = frozenset()


def _patch_stages(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
    *,
    section_count: int = 1,
    records_per_section: dict[int, int] | None = None,
    failures: _FailureConfig | None = None,
) -> None:
    failures = failures if failures is not None else _FailureConfig()
    monkeypatch.setattr(
        job_runner_module, "DocumentAnalyzer", make_stub_stage_class("document_analyzer", calls)
    )
    monkeypatch.setattr(
        job_runner_module, "LayoutDetector", make_stub_stage_class("layout_detector", calls)
    )
    monkeypatch.setattr(
        job_runner_module,
        "SectionParser",
        make_section_parser_stub_class(calls, section_count),
    )
    monkeypatch.setattr(
        job_runner_module,
        "FieldExtractor",
        make_field_extractor_stub_class(calls, records_per_section, failures.sections),
    )
    monkeypatch.setattr(
        job_runner_module,
        "Normalizer",
        make_normalizer_stub_class(calls, failures.normalizer_records),
    )
    monkeypatch.setattr(
        job_runner_module, "Validator", make_validator_stub_class(calls, failures.validator_records)
    )


_JobRunnerFixture = tuple[
    JobRunner,
    StubJobRepository,
    StubPDFRepository,
    StubCandidateRepository,
    StubKnowledgeService,
    StubLearningService,
]


def _make_job_runner(
    *,
    jobs: StubJobRepository | None = None,
    pdfs: StubPDFRepository | None = None,
    candidates: StubCandidateRepository | None = None,
    knowledge: StubKnowledgeService | None = None,
    learning: StubLearningService | None = None,
) -> _JobRunnerFixture:
    jobs = jobs if jobs is not None else StubJobRepository()
    pdfs = pdfs if pdfs is not None else StubPDFRepository()
    candidates = candidates if candidates is not None else StubCandidateRepository()
    knowledge = knowledge if knowledge is not None else StubKnowledgeService()
    learning = learning if learning is not None else StubLearningService()
    runner = JobRunner(
        repositories=JobRunnerRepositories(pdfs=pdfs, jobs=jobs, candidates=candidates),
        knowledge=knowledge,
        learning=learning,
        parser_version_id=ParserVersionId(1),
    )
    return runner, jobs, pdfs, candidates, knowledge, learning


def test_stages_run_in_correct_order_for_single_section_single_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=1, records_per_section={0: 1})
    runner, *_ = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert calls == [
        "document_analyzer",
        "layout_detector",
        "section_parser",
        "field_extractor",
        "normalizer",
        "validator",
    ]
    assert result.succeeded is True
    assert result.job.processed_count == 1
    assert result.job.failed_count == 0


def test_knowledge_service_snapshot_and_rules_fetched(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls)
    runner, _, _, _, knowledge, _ = _make_job_runner()

    runner.run_for_pdf(_make_pdf())

    assert knowledge.load_snapshot_calls == 1
    assert knowledge.load_validation_rules_calls == 1


def test_multiple_sections_call_field_extractor_once_per_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=3, records_per_section={0: 1, 1: 1, 2: 1})
    runner, *_ = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert calls.count("section_parser") == 1
    assert calls.count("field_extractor") == 3
    assert result.job.processed_count == 3


def test_multiple_records_call_normalizer_and_validator_once_per_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=1, records_per_section={0: 4})
    runner, *_ = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert calls.count("field_extractor") == 1
    assert calls.count("normalizer") == 4
    assert calls.count("validator") == 4
    assert result.job.processed_count == 4


def test_candidate_repository_call_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=2, records_per_section={0: 2, 1: 1})
    candidates = StubCandidateRepository()
    runner, *_ = _make_job_runner(candidates=candidates)

    runner.run_for_pdf(_make_pdf())

    assert len(candidates.add_section_calls) == 2
    assert len(candidates.add_raw_calls) == 3
    assert len(candidates.attach_normalized_calls) == 3
    assert len(candidates.update_validation_calls) == 3


def test_pipeline_runner_call_count_matches_coordinator_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """文書レベル1回 + Section単位2回 + Record単位(Normalizer/Validator)6回 = 9回。"""
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=2, records_per_section={0: 2, 1: 1})
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

    # 1 (document-level) + 2 (field_extractor, per section) + 3*2 (normalizer+validator, per record)
    assert run_call_count == 1 + 2 + 3 * 2


def test_candidate_repository_order_matches_artifact_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    _patch_stages(monkeypatch, order, section_count=1, records_per_section={0: 1})
    candidates = StubCandidateRepository(order_log=order)
    runner, *_ = _make_job_runner(candidates=candidates)

    runner.run_for_pdf(_make_pdf())

    assert order == [
        "document_analyzer",
        "layout_detector",
        "section_parser",
        "add_section",
        "field_extractor",
        "add_raw",
        "normalizer",
        "attach_normalized",
        "validator",
        "update_validation",
    ]


def test_repository_receives_pipeline_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=1, records_per_section={0: 1})
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


def test_learning_service_delegated_on_section_failure_isolates_other_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_stages(
        monkeypatch,
        calls,
        section_count=2,
        records_per_section={1: 1},
        failures=_FailureConfig(sections=frozenset({0})),
    )
    runner, jobs, _, candidates, _, learning = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert len(learning.recorded) == 1
    assert learning.recorded[0].pipeline_stage == PipelineStageName.FIELD_EXTRACTOR
    # section 0は失敗、section 1は処理が継続される（ADR-0045: 失敗の非波及）
    assert len(candidates.add_section_calls) == 2
    assert len(candidates.add_raw_calls) == 1
    assert result.job.processed_count == 1
    assert result.job.failed_count == 1
    assert jobs.updates[0][1] == "failed"


def test_learning_service_delegated_on_record_failure_isolates_other_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _patch_stages(
        monkeypatch,
        calls,
        section_count=1,
        records_per_section={0: 2},
        failures=_FailureConfig(normalizer_records=frozenset({0})),
    )
    runner, _, _, candidates, _, learning = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert len(learning.recorded) == 1
    assert learning.recorded[0].pipeline_stage == PipelineStageName.NORMALIZER
    # record 0は失敗、record 1は処理が継続される
    assert len(candidates.add_raw_calls) == 2
    assert len(candidates.attach_normalized_calls) == 1
    assert len(candidates.update_validation_calls) == 1
    assert result.job.processed_count == 1
    assert result.job.failed_count == 1


def test_learning_service_delegated_on_validator_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(
        monkeypatch,
        calls,
        section_count=1,
        records_per_section={0: 1},
        failures=_FailureConfig(validator_records=frozenset({0})),
    )
    runner, _, _, candidates, _, learning = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert len(learning.recorded) == 1
    assert learning.recorded[0].pipeline_stage == PipelineStageName.VALIDATOR
    assert len(candidates.attach_normalized_calls) == 1
    assert len(candidates.update_validation_calls) == 0


def test_learning_service_not_called_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=1, records_per_section={0: 1})
    runner, _, _, _, _, learning = _make_job_runner()

    runner.run_for_pdf(_make_pdf())

    assert learning.recorded == []


def test_document_level_failure_stops_all_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=2, records_per_section={0: 1, 1: 1})

    from mod_personnel_db.pipeline.exceptions import PipelineException

    class _FailingSectionParser:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            del input
            calls.append("section_parser")
            raise PipelineException(
                stage_name="section_parser",
                context=context,  # type: ignore[arg-type]
                message="section_parser failed",
            )

    monkeypatch.setattr(job_runner_module, "SectionParser", _FailingSectionParser)
    candidates = StubCandidateRepository()
    runner, jobs, _, _, _, learning = _make_job_runner(candidates=candidates)

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert "field_extractor" not in calls
    assert "normalizer" not in calls
    assert "validator" not in calls
    assert candidates.add_section_calls == []
    assert len(learning.recorded) == 1
    assert learning.recorded[0].pipeline_stage.value == "section_parser"
    assert result.job.processed_count == 0
    assert result.job.failed_count == 1
    assert jobs.updates[0][1] == "failed"


def test_pipeline_exception_does_not_propagate_out_of_run_for_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PipelineExceptionは各PipelineRunner呼び出し内で捕捉されPipelineResult.errorへ
    格納される（docs/api/pipeline.md#pipelineexception）。JobRunnerErrorへの変換は
    行わず、run_for_pdf()から例外として送出されることもない。"""
    calls: list[str] = []
    _patch_stages(
        monkeypatch,
        calls,
        section_count=1,
        records_per_section={0: 1},
        failures=_FailureConfig(normalizer_records=frozenset({0})),
    )
    runner, *_ = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.error is not None
    assert result.succeeded is False


def test_run_pending_processes_all_pending_pdfs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _patch_stages(monkeypatch, calls, section_count=1, records_per_section={0: 1})
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
    _patch_stages(monkeypatch, calls)
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
    _patch_stages(monkeypatch, calls)
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
    _patch_stages(monkeypatch, calls)

    from mod_personnel_db.pipeline.exceptions import PipelineException

    class _FailingDocumentAnalyzer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs

        def run(self, context: object, input: object) -> object:
            del input
            calls.append("document_analyzer")
            raise PipelineException(
                stage_name="document_analyzer",
                context=context,  # type: ignore[arg-type]
                message="document_analyzer failed",
            )

    monkeypatch.setattr(job_runner_module, "DocumentAnalyzer", _FailingDocumentAnalyzer)
    runner, jobs, _, _, _, learning = _make_job_runner()

    result = runner.run_for_pdf(_make_pdf())

    assert result.succeeded is False
    assert learning.recorded == []
    assert jobs.updates[0][1] == "failed"


def test_job_runner_public_api_matches_protocol() -> None:
    public_names = {name for name in dir(JobRunner) if not name.startswith("_")}

    assert public_names == {"run_for_pdf", "run_pending", "get_job"}
