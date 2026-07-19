"""Learning Datasetモデル。docs/api/models.md#learningrecord に対応する。

status遷移の合法性（open→in_review→reflected→verifiedまたはwontfixのみ、
逆行・スキップ禁止）は、単一インスタンスの__post_init__では検証できない
（遷移前の状態を要するBusiness Logicであり、将来のLearningService等の
責務）。ここでは単一インスタンスの整合性のみを検証する。
"""

from dataclasses import dataclass
from datetime import datetime

from mod_personnel_db.models.enums import (
    ErrorCategory,
    LearningStatus,
    PipelineStageName,
    RegressionStatus,
)
from mod_personnel_db.models.ids import (
    CandidateId,
    KnowledgeItemId,
    LayoutId,
    LearningRecordId,
    ParserVersionId,
    ReviewItemId,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


@dataclass(frozen=True, slots=True)
class LearningRecord:
    id: LearningRecordId | None
    source_candidate_id: CandidateId | None
    source_review_item_id: ReviewItemId | None
    pipeline_stage: PipelineStageName
    error_category: ErrorCategory
    field_name: str | None
    wrong_value: str
    correct_value: str | None
    correction_summary: str | None
    reviewer_comment: str | None
    parser_version_id: ParserVersionId | None
    layout_id: LayoutId | None
    confidence: Confidence | None
    status: LearningStatus
    reflected_in_knowledge_item_id: KnowledgeItemId | None
    reflected_in_layout_id: LayoutId | None
    git_commit_hash: str | None
    pull_request_url: str | None
    regression_status: RegressionStatus
    regression_run_at: datetime | None
    regression_details: str | None
    improvement_candidate: str | None
    created_at: datetime
    resolved_at: datetime | None

    def __post_init__(self) -> None:
        if self.status != LearningStatus.OPEN and self.correct_value is None:
            raise ModelValidationError("correct_value must be set once status is not 'open'")
        verified_without_pass = (
            self.status == LearningStatus.VERIFIED
            and self.regression_status != RegressionStatus.PASSED
        )
        if verified_without_pass:
            raise ModelValidationError("status='verified' requires regression_status='passed'")
