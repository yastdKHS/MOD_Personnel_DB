"""PipelineRunnerの呼び出し元。docs/api/interfaces.md#jobrunner, ADR-0044に対応する。

`PipelineContext`生成・Stage生成（`KnowledgeSnapshot`/`ValidationRuleSet`の
コンストラクタ注入）・`PipelineBuilder`経由での`PipelineRunner`登録・呼び出し・
`Job`のRepository永続化・Learning記録への委譲を行う。`PipelineRunner`自身が
禁止されている`repositories/`・`knowledge/`・`learning/`への依存は、すべて
本クラスが引き受ける（ADR-0044、architecture-contract.md保証13）。

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
    ErrorCategory,
    Job,
    JobId,
    KnowledgeSnapshot,
    LayoutDefinition,
    LearningRecord,
    LearningStatus,
    ParserVersionId,
    PdfRecord,
    PipelineStageName,
    RegressionStatus,
    ValidationRuleSet,
)
from mod_personnel_db.normalizers import Normalizer
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineException
from mod_personnel_db.pipeline.factory import PipelineFactory
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.pipeline.runner import NamedStage
from mod_personnel_db.pipeline.stage import PipelineStage
from mod_personnel_db.repositories import JobRepository, PDFRepository
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


@dataclass(frozen=True, slots=True)
class JobRunnerRepositories:
    """`JobRunner`が永続化に用いるRepository（抽象）の束（引数個数削減のための集約）。"""

    pdfs: PDFRepository
    jobs: JobRepository


class JobRunner:
    """`PipelineRunner`の呼び出し元（`pipeline/`パッケージの公開窓口）。"""

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

        snapshot = self._knowledge.load_snapshot()
        rules = self._knowledge.load_validation_rules()

        builder = PipelineFactory.create_builder()
        for name, stage in self._build_stages(snapshot, rules):
            builder.add_stage(name, stage)
        runner = builder.build()

        result = runner.run(context, job, initial_input=pdf)

        self._jobs.update_status(
            job_id,
            result.job.status,
            result.job.processed_count,
            result.job.failed_count,
        )

        if result.error is not None:
            self._record_learning_failure(result.error)

        return result

    def run_pending(self) -> tuple[PipelineResult, ...]:
        pending = self._pdfs.list_by_status(_PENDING_PDF_STATUS)
        return tuple(self.run_for_pdf(pdf) for pdf in pending)

    def get_job(self, job_id: JobId) -> Job | None:
        return self._jobs.get(job_id)

    def _build_stages(
        self, snapshot: KnowledgeSnapshot, rules: ValidationRuleSet
    ) -> tuple[NamedStage, ...]:
        return (
            ("document_analyzer", _as_stage(DocumentAnalyzer())),
            (
                "layout_detector",
                _as_stage(LayoutDetector(layout_definitions=self._layout_definitions)),
            ),
            ("section_parser", _as_stage(SectionParser())),
            ("field_extractor", _as_stage(FieldExtractor())),
            ("normalizer", _as_stage(Normalizer(snapshot))),
            ("validator", _as_stage(Validator(rules, snapshot))),
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
