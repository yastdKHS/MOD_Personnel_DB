"""ドメインモデル公開窓口。docs/api/models.md の平坦な名前空間に対応する。

Parser未実装のため、Document/PersonnelSection抽出前段・LearningRecord/
FeatureVector等、Parser・Learning・Feature Storeに依存するモデルは
本タスクの対象外（Phase2 Task1のTODO参照）。
"""

from mod_personnel_db.models.candidate import (
    CandidateRecord,
    NormalizedRecord,
    NormalizedValue,
    PersonnelSection,
    RawRecord,
    ValidationResult,
    ValidationViolation,
)
from mod_personnel_db.models.export import ExportRecord
from mod_personnel_db.models.gold import GoldRecord
from mod_personnel_db.models.ids import (
    CandidateId,
    ExportId,
    GoldRecordId,
    JobId,
    KnowledgeItemId,
    LayoutId,
    ParserVersionId,
    PdfId,
    PersonnelSectionId,
    ReviewItemId,
    ReviewSessionId,
)
from mod_personnel_db.models.job import Job, ParserVersion
from mod_personnel_db.models.knowledge import KnowledgeItem, Layout
from mod_personnel_db.models.pdf import PdfRecord
from mod_personnel_db.models.review import ReviewItem
from mod_personnel_db.models.values import Confidence

__all__ = [
    "CandidateId",
    "CandidateRecord",
    "Confidence",
    "ExportId",
    "ExportRecord",
    "GoldRecord",
    "GoldRecordId",
    "Job",
    "JobId",
    "KnowledgeItem",
    "KnowledgeItemId",
    "Layout",
    "LayoutId",
    "NormalizedRecord",
    "NormalizedValue",
    "ParserVersion",
    "ParserVersionId",
    "PdfId",
    "PdfRecord",
    "PersonnelSection",
    "PersonnelSectionId",
    "RawRecord",
    "ReviewItem",
    "ReviewItemId",
    "ReviewSessionId",
    "ValidationResult",
    "ValidationViolation",
]
