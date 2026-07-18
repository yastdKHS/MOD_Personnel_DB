"""ドメインモデル公開窓口。docs/api/models.md の平坦な名前空間に対応する（13モデル全種）。"""

from mod_personnel_db.models.candidate import (
    CandidateRecord,
    NormalizedRecord,
    NormalizedValue,
    PersonnelSection,
    RawRecord,
    ValidationResult,
    ValidationViolation,
)
from mod_personnel_db.models.document import Document, Page
from mod_personnel_db.models.enums import (
    ConfidenceBand,
    ErrorCategory,
    LearningStatus,
    PipelineStage,
    RegressionStatus,
)
from mod_personnel_db.models.export import ExportRecord
from mod_personnel_db.models.feature import FeatureVector
from mod_personnel_db.models.gold import GoldRecord
from mod_personnel_db.models.ids import (
    CandidateId,
    ExportId,
    GoldRecordId,
    JobId,
    KnowledgeItemId,
    LayoutId,
    LearningRecordId,
    ParserVersionId,
    PdfId,
    PersonnelSectionId,
    ReviewItemId,
    ReviewSessionId,
)
from mod_personnel_db.models.job import Job, ParserVersion
from mod_personnel_db.models.knowledge import KnowledgeItem, Layout
from mod_personnel_db.models.learning import LearningRecord
from mod_personnel_db.models.pdf import PdfRecord
from mod_personnel_db.models.review import ReviewItem
from mod_personnel_db.models.values import Confidence

__all__ = [
    "CandidateId",
    "CandidateRecord",
    "Confidence",
    "ConfidenceBand",
    "Document",
    "ErrorCategory",
    "ExportId",
    "ExportRecord",
    "FeatureVector",
    "GoldRecord",
    "GoldRecordId",
    "Job",
    "JobId",
    "KnowledgeItem",
    "KnowledgeItemId",
    "Layout",
    "LayoutId",
    "LearningRecord",
    "LearningRecordId",
    "LearningStatus",
    "NormalizedRecord",
    "NormalizedValue",
    "Page",
    "ParserVersion",
    "ParserVersionId",
    "PdfId",
    "PdfRecord",
    "PersonnelSection",
    "PersonnelSectionId",
    "PipelineStage",
    "RawRecord",
    "RegressionStatus",
    "ReviewItem",
    "ReviewItemId",
    "ReviewSessionId",
    "ValidationResult",
    "ValidationViolation",
]
