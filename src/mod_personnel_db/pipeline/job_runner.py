"""PipelineRunnerの呼び出し元。docs/api/interfaces.md#jobrunner, ADR-0044, ADR-0045に対応する。

`PipelineContext`生成・Stage生成（`KnowledgeSnapshot`/`ValidationRuleSet`の
コンストラクタ注入）・`PipelineBuilder`経由での`PipelineRunner`登録・呼び出し・
`Job`/`Candidate`のRepository永続化・Learning記録への委譲を行う。`PipelineRunner`
自身が禁止されている`repositories/`・`knowledge/`・`learning/`への依存は、すべて
本クラスが引き受ける（ADR-0044、architecture-contract.md保証13）。

ADR-0045に従い、集約Artifact（`SectionParseResult`/`FieldExtractionResult`/
`NormalizationResult`）の展開（反復処理）もJobRunnerが担う。`PipelineRunner`は
文書レベル・Section単位・Record単位でそれぞれ必要な回数だけ構築・呼び出すのみで、
`PipelineRunner`自身のコードは変更しない（集約Artifactを展開しない、
architecture-contract.md保証14）。

`review/`・`export/`・`repositories/sqlite/`（具象）には依存しない
（dependency-rule.md）。
"""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import cast

from mod_personnel_db.document import DocumentAnalyzer
from mod_personnel_db.extractors import FieldExtractor
from mod_personnel_db.knowledge import KnowledgeService
from mod_personnel_db.layout import LayoutDetector
from mod_personnel_db.learning import LearningService
from mod_personnel_db.models import (
    CandidateId,
    ErrorCategory,
    FieldExtractionResult,
    Job,
    JobId,
    KnowledgeSnapshot,
    LayoutDefinition,
    LearningRecord,
    LearningStatus,
    NormalizationResult,
    ParserVersionId,
    PdfRecord,
    PersonnelSection,
    PipelineStageName,
    RawRecord,
    RegressionStatus,
    SectionParseResult,
    ValidationResult,
    ValidationRuleSet,
)
from mod_personnel_db.normalizers import Normalizer
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.events import PipelineEvent
from mod_personnel_db.pipeline.exceptions import PipelineException
from mod_personnel_db.pipeline.factory import PipelineFactory
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.pipeline.runner import NamedStage
from mod_personnel_db.pipeline.stage import PipelineStage
from mod_personnel_db.repositories import CandidateRepository, JobRepository, PDFRepository
from mod_personnel_db.sections import SectionParser
from mod_personnel_db.validators import Validator

_PENDING_PDF_STATUS = "fetched"

_STAGE_NAME_TO_PIPELINE_STAGE_NAME: dict[str, PipelineStageName] = {
    "layout_detector": PipelineStageName.LAYOUT_DETECTOR,
    "section_parser": PipelineStageName.SECTION_PARSER,
    "field_extractor": PipelineStageName.FIELD_EXTRACTOR,
    "normalizer": PipelineStageName.NORMALIZER,
    "validator": PipelineStageName.VALIDATOR,
}


def _as_stage(stage: object) -> PipelineStage[object, object]:
    """個々のStageは固有のTIn/TOutを持つため、Heteroな列に格納するにあたり
    `PipelineStage[object, object]`へ変換する（tests/unit/pipeline/の慣行と同様）。
    """
    return cast("PipelineStage[object, object]", stage)


class _CapturingStage:
    """内側のStageの出力を保持する薄いラッパー（ADR-0045）。

    `PipelineResult`は最終Artifactを保持しないため、`PipelineRunner`/
    `PipelineResult`のいずれにも変更を加えずに、JobRunnerが集約Artifact
    （`SectionParseResult`等）を読み取れるようにするための、job_runner.py内で
    完結する構成である。`PipelineRunner`からはこのラッパーも通常の
    `PipelineStage[object, object]`として扱われるのみで、集約Artifactを
    解釈するのは常にJobRunner側（本ラッパーの外側）である。
    """

    def __init__(self, inner: PipelineStage[object, object]) -> None:
        self._inner = inner
        self.output: object = None

    def run(self, context: PipelineContext, input: object) -> object:
        self.output = self._inner.run(context, input)
        return self.output


def _run_stages(
    context: PipelineContext,
    job: Job,
    initial_input: object,
    named_stages: tuple[NamedStage, ...],
) -> tuple[PipelineResult, object | None]:
    """`named_stages`を1つの`PipelineRunner`に登録し1回実行する。

    戻り値は`(PipelineResult, 最後のStageの出力)`。`PipelineRunner`へは常に
    単一Artifact（`initial_input`）のみを渡し、`PipelineRunner`自体は最後の
    Stageの出力を集約Artifactとして解釈も展開もしない（ADR-0045）。
    """
    last_name, last_stage = named_stages[-1]
    capture = _CapturingStage(last_stage)
    stages = (*named_stages[:-1], (last_name, _as_stage(capture)))

    builder = PipelineFactory.create_builder()
    for stage_name, stage in stages:
        builder.add_stage(stage_name, stage)
    runner = builder.build()

    result = runner.run(context, job, initial_input)
    output = capture.output if result.error is None else None
    return result, output


@dataclass(frozen=True, slots=True)
class JobRunnerRepositories:
    """`JobRunner`が永続化に用いるRepository（抽象）の束（引数個数削減のための集約）。"""

    pdfs: PDFRepository
    jobs: JobRepository
    candidates: CandidateRepository


@dataclass(frozen=True, slots=True)
class _KnowledgeInputs:
    """Record単位の処理へ渡す`KnowledgeSnapshot`/`ValidationRuleSet`の束（引数個数削減）。"""

    snapshot: KnowledgeSnapshot
    rules: ValidationRuleSet


@dataclass(frozen=True, slots=True)
class _Outcome:
    """Coordinator処理（文書/Section/Record単位）の集計結果。"""

    events: tuple[PipelineEvent, ...]
    processed_count: int
    failed_count: int
    first_error: PipelineException | None


class JobRunner:
    """`PipelineRunner`の呼び出し元（`pipeline/`パッケージの公開窓口）。

    ADR-0045に従い、集約Artifactを展開するCoordinatorとして、文書レベル・
    Section単位・Record単位でそれぞれ`PipelineRunner`を必要な回数構築・
    呼び出す。
    """

    def __init__(
        self,
        *,
        repositories: JobRunnerRepositories,
        knowledge: KnowledgeService,
        learning: LearningService,
        parser_version_id: ParserVersionId,
        layout_definitions: tuple[LayoutDefinition, ...] = (),
    ) -> None:
        self._pdfs = repositories.pdfs
        self._jobs = repositories.jobs
        self._candidates = repositories.candidates
        self._knowledge = knowledge
        self._learning = learning
        self._parser_version_id = parser_version_id
        self._layout_definitions = layout_definitions

    def run_for_pdf(self, pdf: PdfRecord) -> PipelineResult:
        started_at = datetime.now(UTC)
        initial_job = _initial_job(pdf, self._parser_version_id, started_at)
        job_id = self._jobs.add(initial_job)
        job = replace(initial_job, id=job_id)
        context = PipelineContext(
            job_id=job_id,
            parser_version_id=self._parser_version_id,
            correlation_id=f"job-{int(job_id)}",
            started_at=started_at,
        )

        knowledge = _KnowledgeInputs(
            snapshot=self._knowledge.load_snapshot(), rules=self._knowledge.load_validation_rules()
        )
        outcome = self._coordinate(context, job, pdf, knowledge)
        result = self._finalize(context, job, started_at, outcome)

        self._jobs.update_status(
            job_id, result.job.status, result.job.processed_count, result.job.failed_count
        )
        return result

    def run_pending(self) -> tuple[PipelineResult, ...]:
        pending = self._pdfs.list_by_status(_PENDING_PDF_STATUS)
        return tuple(self.run_for_pdf(pdf) for pdf in pending)

    def get_job(self, job_id: JobId) -> Job | None:
        return self._jobs.get(job_id)

    def _coordinate(
        self, context: PipelineContext, job: Job, pdf: PdfRecord, knowledge: _KnowledgeInputs
    ) -> _Outcome:
        doc_result, output = _run_stages(context, job, pdf, self._build_document_stages())
        if doc_result.error is not None:
            self._record_learning_failure(doc_result.error)
            return _Outcome(doc_result.events, 0, 1, doc_result.error)

        section_parse_result = cast("SectionParseResult", output)
        events = list(doc_result.events)
        processed_count = 0
        failed_count = 0
        first_error: PipelineException | None = None
        for section in section_parse_result.sections:
            section_outcome = self._process_section(context, job, section, knowledge)
            events.extend(section_outcome.events)
            processed_count += section_outcome.processed_count
            failed_count += section_outcome.failed_count
            first_error = first_error or section_outcome.first_error
        return _Outcome(tuple(events), processed_count, failed_count, first_error)

    def _process_section(
        self,
        context: PipelineContext,
        job: Job,
        section: PersonnelSection,
        knowledge: _KnowledgeInputs,
    ) -> _Outcome:
        section_id = self._candidates.add_section(section)
        fe_result, output = _run_stages(
            context, job, section, (("field_extractor", _as_stage(FieldExtractor())),)
        )
        if fe_result.error is not None:
            self._record_learning_failure(fe_result.error)
            return _Outcome(fe_result.events, 0, 1, fe_result.error)

        field_extraction_result = cast("FieldExtractionResult", output)
        events = list(fe_result.events)
        processed_count = 0
        failed_count = 0
        first_error: PipelineException | None = None
        for record in field_extraction_result.records:
            candidate_id = self._candidates.add_raw(section_id, record)
            record_outcome = self._process_record(context, job, record, candidate_id, knowledge)
            events.extend(record_outcome.events)
            processed_count += record_outcome.processed_count
            failed_count += record_outcome.failed_count
            first_error = first_error or record_outcome.first_error
        return _Outcome(tuple(events), processed_count, failed_count, first_error)

    def _process_record(
        self,
        context: PipelineContext,
        job: Job,
        record: RawRecord,
        candidate_id: CandidateId,
        knowledge: _KnowledgeInputs,
    ) -> _Outcome:
        norm_result, norm_output = _run_stages(
            context, job, record, (("normalizer", _as_stage(Normalizer(knowledge.snapshot))),)
        )
        if norm_result.error is not None:
            self._record_learning_failure(norm_result.error)
            return _Outcome(norm_result.events, 0, 1, norm_result.error)

        normalized_record = cast("NormalizationResult", norm_output).records[0]
        self._candidates.attach_normalized(candidate_id, normalized_record)

        val_result, val_output = _run_stages(
            context,
            job,
            normalized_record,
            (("validator", _as_stage(Validator(knowledge.rules, knowledge.snapshot))),),
        )
        events = norm_result.events + val_result.events
        if val_result.error is not None:
            self._record_learning_failure(val_result.error)
            return _Outcome(events, 0, 1, val_result.error)

        self._candidates.update_validation(candidate_id, cast("ValidationResult", val_output))
        return _Outcome(events, 1, 0, None)

    def _finalize(
        self, context: PipelineContext, job: Job, started_at: datetime, outcome: _Outcome
    ) -> PipelineResult:
        finished_at = datetime.now(UTC)
        succeeded = outcome.failed_count == 0
        metrics = PipelineMetrics(
            elapsed_ms=(finished_at - started_at).total_seconds() * 1000,
            started_at=started_at,
            finished_at=finished_at,
            succeeded=succeeded,
            warning_count=0,
            error_count=outcome.failed_count,
        )
        final_job = replace(
            job,
            status="succeeded" if succeeded else "failed",
            finished_at=finished_at,
            processed_count=outcome.processed_count,
            failed_count=outcome.failed_count,
            error_summary=None if succeeded else f"{outcome.failed_count}件が失敗しました",
        )
        return PipelineResult(
            context=context,
            job=final_job,
            events=outcome.events,
            metrics=metrics,
            error=outcome.first_error,
        )

    def _build_document_stages(self) -> tuple[NamedStage, ...]:
        return (
            ("document_analyzer", _as_stage(DocumentAnalyzer())),
            (
                "layout_detector",
                _as_stage(LayoutDetector(layout_definitions=self._layout_definitions)),
            ),
            ("section_parser", _as_stage(SectionParser())),
        )

    def _record_learning_failure(self, error: PipelineException) -> None:
        pipeline_stage = _STAGE_NAME_TO_PIPELINE_STAGE_NAME.get(error.stage_name)
        if pipeline_stage is None:
            return
        self._learning.record_error(
            LearningRecord(
                id=None,
                source_candidate_id=None,
                source_review_item_id=None,
                pipeline_stage=pipeline_stage,
                error_category=ErrorCategory.TRUE_EXCEPTION,
                field_name=None,
                wrong_value=str(error),
                correct_value=None,
                correction_summary=None,
                reviewer_comment=None,
                parser_version_id=self._parser_version_id,
                layout_id=None,
                confidence=None,
                status=LearningStatus.OPEN,
                reflected_in_knowledge_item_id=None,
                reflected_in_layout_id=None,
                git_commit_hash=None,
                pull_request_url=None,
                regression_status=RegressionStatus.NOT_RUN,
                regression_run_at=None,
                regression_details=None,
                improvement_candidate=None,
                created_at=datetime.now(UTC),
                resolved_at=None,
            )
        )


def _initial_job(pdf: PdfRecord, parser_version_id: ParserVersionId, started_at: datetime) -> Job:
    return Job(
        id=None,
        job_type="core_pipeline",
        pdf_id=pdf.id,
        parser_version_id=parser_version_id,
        status="running",
        started_at=started_at,
        finished_at=None,
        processed_count=0,
        failed_count=0,
        error_summary=None,
    )
