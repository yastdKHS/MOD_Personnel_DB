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

from mod_personnel_db.document import DocumentAnalyzer, DocumentAnalyzerError
from mod_personnel_db.extractors import FieldExtractor, FieldExtractorError
from mod_personnel_db.knowledge import KnowledgeService
from mod_personnel_db.layout import LayoutDetector, LayoutDetectorError
from mod_personnel_db.learning import LearningService
from mod_personnel_db.models import (
    CandidateId,
    CandidateRecord,
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
    PersonnelSectionId,
    PipelineStageName,
    RawRecord,
    RegressionStatus,
    SectionParseResult,
    ValidationResult,
    ValidationRuleSet,
)
from mod_personnel_db.normalizers import Normalizer, NormalizerError
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.events import PipelineEvent
from mod_personnel_db.pipeline.exceptions import PipelineException
from mod_personnel_db.pipeline.factory import PipelineFactory
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.pipeline.runner import NamedStage
from mod_personnel_db.pipeline.stage import PipelineStage
from mod_personnel_db.repositories import CandidateRepository, JobRepository, PDFRepository
from mod_personnel_db.sections import SectionParser, SectionParserError
from mod_personnel_db.utils.exceptions import MODPersonnelDBError, RepositoryError
from mod_personnel_db.validators import Validator, ValidatorError

_PENDING_PDF_STATUS = "fetched"

_STAGE_NAME_TO_PIPELINE_STAGE_NAME: dict[str, PipelineStageName] = {
    "layout_detector": PipelineStageName.LAYOUT_DETECTOR,
    "section_parser": PipelineStageName.SECTION_PARSER,
    "field_extractor": PipelineStageName.FIELD_EXTRACTOR,
    "normalizer": PipelineStageName.NORMALIZER,
    "validator": PipelineStageName.VALIDATOR,
}

#: 各Stage固有例外（PipelineExceptionを継承しない、Task28調査で判明）から
#: stage_nameへの対応。PipelineRunner自体は変更せず（ADR-0044）、JobRunner側の
#: _run_stages()境界でこれらを吸収するために使う（Task29）。
_STAGE_EXCEPTION_TO_STAGE_NAME: dict[type[Exception], str] = {
    DocumentAnalyzerError: "document_analyzer",
    LayoutDetectorError: "layout_detector",
    SectionParserError: "section_parser",
    FieldExtractorError: "field_extractor",
    NormalizerError: "normalizer",
    ValidatorError: "validator",
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

    `PipelineRunner.run()`は`PipelineException`のみを捕捉するため（ADR-0044、
    無変更）、各Stage固有例外（`DocumentAnalyzerError`等、`PipelineException`を
    継承しない、Task28調査で判明）はここまで未捕捉のまま伝播する。JobRunner側の
    本関数境界でそれらを吸収し、`PipelineException`捕捉時と同じ`PipelineResult`
    形状へ変換する（Task29）。
    """
    last_name, last_stage = named_stages[-1]
    capture = _CapturingStage(last_stage)
    stages = (*named_stages[:-1], (last_name, _as_stage(capture)))

    builder = PipelineFactory.create_builder()
    for stage_name, stage in stages:
        builder.add_stage(stage_name, stage)
    runner = builder.build()

    try:
        result = runner.run(context, job, initial_input)
    except MODPersonnelDBError as exc:
        result = _wrap_stage_exception(context, job, exc, last_name)
    output = capture.output if result.error is None else None
    return result, output


def _wrap_stage_exception(
    context: PipelineContext, job: Job, exc: MODPersonnelDBError, fallback_stage_name: str
) -> PipelineResult:
    """`PipelineRunner`が捕捉しない`MODPersonnelDBError`系統（Stage固有例外）を、
    `PipelineException`捕捉時と同じ`PipelineResult`形状へ変換する（Task29）。
    """
    stage_name = _STAGE_EXCEPTION_TO_STAGE_NAME.get(type(exc), fallback_stage_name)
    wrapped = PipelineException(stage_name=stage_name, context=context, message=str(exc))
    finished_at = datetime.now(UTC)
    metrics = PipelineMetrics(
        elapsed_ms=(finished_at - context.started_at).total_seconds() * 1000,
        started_at=context.started_at,
        finished_at=finished_at,
        succeeded=False,
        warning_count=0,
        error_count=1,
    )
    failed_job = replace(job, status="failed", finished_at=finished_at, error_summary=str(wrapped))
    return PipelineResult(
        context=context, job=failed_job, events=(), metrics=metrics, error=wrapped
    )


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
        if result.job.status == "succeeded" and pdf.id is not None:
            # docs/database/schema.md「fetched→analyzed→parsed→validated」の終端状態。
            # 正常終了PDFを`run_pending()`の対象（status='fetched'）から外し、
            # 再実行時に`personnel_sections`のUNIQUE制約へ抵触するのを防ぐ。
            self._pdfs.update_status(pdf.id, "validated")
        elif result.job.status == "failed" and pdf.id is not None:
            # docs/database/schema.md「失敗時はfailed」の終端状態（Task27、Task25-8
            # レビューMinor指摘への対応）。失敗PDFも`run_pending()`の対象（status=
            # 'fetched'）から外し、同一PDFが無限に再選定され続けるのを防ぐ
            # （既にcommit済みのpersonnel_sections/candidate_recordsを安全に
            # 再処理する仕組み自体は本変更のスコープ外）。
            self._pdfs.update_status(pdf.id, "failed")
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
        """Section単位のResume判定（Task31 Case A、Step5/Step7の7段階手順）。

        1. `find_section()`で既存Sectionの有無を確認する。
        2. 存在しなければ、Case C（`find_active_section()`→`add_section()`→
           条件付き`supersede_section()`、Task32 Step2、ADR-0047）を経て新規処理する。
        3-4. 存在し`candidate_records`が0件なら、Section再利用のみ行い
             FieldExtractorへ進む。
        5-6. 存在し全Candidateが`passed`/`failed`ならSection全体をskipする
             （`_Outcome`は未計上、processed/failed共に0）。
        7. `pending`が1件でもあれば、既存Candidate一覧からRecord単位で
           再開する（Case B、FieldExtractorは再実行しない）。
        """
        existing_section_id = self._candidates.find_section(
            section.document_ref, section.section_index
        )
        if existing_section_id is None:
            return self._add_section_and_process(context, job, section, knowledge)

        candidates = self._candidates.list_by_section(existing_section_id)
        if not candidates:
            return self._extract_and_process_records(
                context, job, section, existing_section_id, knowledge
            )

        if all(c.validation_status in ("passed", "failed") for c in candidates):
            return _Outcome((), 0, 0, None)

        return self._resume_pending_candidates(
            context, job, existing_section_id, candidates, knowledge
        )

    def _add_section_and_process(
        self,
        context: PipelineContext,
        job: Job,
        section: PersonnelSection,
        knowledge: _KnowledgeInputs,
    ) -> _Outcome:
        """Case C: parser_version更新後の再解析（Task32 Step2、ADR-0047）。

        `find_active_section()`は必ず`add_section()`より前に呼ぶ——追加後に
        呼ぶと新旧2行が両方`status='parsed'`になり、どちらが旧versionかを
        区別できなくなるため（ADR-0047「add_section前にfind_active_sectionを
        呼ぶ理由」）。取得した旧Section IDが存在し、かつ新Section IDと異なる
        場合のみ`supersede_section()`を呼ぶ（初回処理・旧Sectionなしの場合は
        呼ばない）。

        Task33: 上記3呼び出し（読み取りを含む）全体を`transaction()`で囲み、
        異なるparser_version間の並行実行でも`status='parsed'`が高々1件という
        設計前提（ADR-0047）が崩れないようにする（TOCTOU対応）。呼び出しの
        意味・順序自体はTask32から変更しない。
        """
        try:
            with self._candidates.transaction():
                old_section_id = self._candidates.find_active_section(
                    section.document_ref, section.section_index
                )
                section_id = self._candidates.add_section(section)
                if old_section_id is not None and old_section_id != section_id:
                    self._candidates.supersede_section(old_section_id)
        except RepositoryError as exc:
            return self._repository_failure_outcome(context, "section_parser", exc)

        return self._extract_and_process_records(context, job, section, section_id, knowledge)

    def _extract_and_process_records(
        self,
        context: PipelineContext,
        job: Job,
        section: PersonnelSection,
        section_id: PersonnelSectionId,
        knowledge: _KnowledgeInputs,
    ) -> _Outcome:
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
            record_outcome = self._process_record(context, job, section_id, record, knowledge)
            events.extend(record_outcome.events)
            processed_count += record_outcome.processed_count
            failed_count += record_outcome.failed_count
            first_error = first_error or record_outcome.first_error
        return _Outcome(tuple(events), processed_count, failed_count, first_error)

    def _resume_pending_candidates(
        self,
        context: PipelineContext,
        job: Job,
        section_id: PersonnelSectionId,
        candidates: tuple[CandidateRecord, ...],
        knowledge: _KnowledgeInputs,
    ) -> _Outcome:
        """Case B: 既存Candidateのうち`pending`のみをNormalizerから再開する。
        `passed`/`failed`はskip（未計上）。FieldExtractorは呼び出さない。"""
        events: list[PipelineEvent] = []
        processed_count = 0
        failed_count = 0
        first_error: PipelineException | None = None
        for candidate in candidates:
            if candidate.validation_status != "pending":
                continue
            record_outcome = self._process_record(
                context, job, section_id, candidate.raw, knowledge
            )
            events.extend(record_outcome.events)
            processed_count += record_outcome.processed_count
            failed_count += record_outcome.failed_count
            first_error = first_error or record_outcome.first_error
        return _Outcome(tuple(events), processed_count, failed_count, first_error)

    def _process_record(
        self,
        context: PipelineContext,
        job: Job,
        section_id: PersonnelSectionId,
        record: RawRecord,
        knowledge: _KnowledgeInputs,
    ) -> _Outcome:
        """Record単位のResume判定（Task31 Case B）。`find_candidate()`で既存
        Candidateの有無を確認し、未存在なら従来処理（`add_raw()`から開始）、
        存在し`pending`ならRepositoryから取得した`CandidateRecord.raw`を使い
        Normalizerから再開する（`add_raw()`は呼ばない）。存在し`passed`/
        `failed`なら完全skip（未計上）とする。"""
        candidate_id = self._candidates.find_candidate(section_id, record.record_index)
        if candidate_id is None:
            try:
                candidate_id = self._candidates.add_raw(section_id, record)
            except RepositoryError as exc:
                return self._repository_failure_outcome(context, "field_extractor", exc)
        else:
            existing = self._candidates.get(candidate_id)
            if existing is None or existing.validation_status != "pending":
                return _Outcome((), 0, 0, None)
            record = existing.raw

        return self._run_normalizer_and_validator(context, job, record, candidate_id, knowledge)

    def _run_normalizer_and_validator(
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

        normalization_result = cast("NormalizationResult", norm_output)
        if not normalization_result.records:
            # 正規化信頼度が閾値未満の場合、Normalizerは空のrecordsを返す
            # （PipelineExceptionではない正常な結果。tests/integration/golden/
            # test_golden.py::_serialize_recordの`if not norm_result.records`と
            # 同じ判定）。candidate_recordsは`add_raw`済みでvalidation_status=
            # 'pending'のまま残り、レビュー対象として扱われる。
            return _Outcome(norm_result.events, 1, 0, None)

        normalized_record = normalization_result.records[0]
        try:
            self._candidates.attach_normalized(candidate_id, normalized_record)
        except RepositoryError as exc:
            return self._repository_failure_outcome(context, "normalizer", exc)

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

        try:
            self._candidates.update_validation(candidate_id, cast("ValidationResult", val_output))
        except RepositoryError as exc:
            return self._repository_failure_outcome(context, "validator", exc)
        return _Outcome(events, 1, 0, None)

    def _repository_failure_outcome(
        self, context: PipelineContext, stage_name: str, exc: RepositoryError
    ) -> _Outcome:
        """`CandidateRepository`の永続化呼び出し（`_run_stages()`の外側）が送出する
        `RepositoryError`（`sqlite3.IntegrityError`等をラップ済み、Task29で
        `repositories/sqlite/candidate.py`側に追加）を、Stage例外と同じ
        `_Outcome`形状へ変換する。"""
        wrapped = PipelineException(stage_name=stage_name, context=context, message=str(exc))
        self._record_learning_failure(wrapped)
        return _Outcome((), 0, 1, wrapped)

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
