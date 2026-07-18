"""ドメインモデル共通のEnum定義。docs/api/python-contract.md#enum利用方針 に対応する。

対象は「3値以上、かつ複数箇所で再利用される値集合」。Repository実装
（repositories/sqlite/）が既に生のstrとして直接読み書きしている既存の
フィールド（KnowledgeItem.category, PdfRecord.status, Job.job_type/status,
ExportRecord.format, CandidateRecord.validation_status）は、本タスクの
対象外（Repository修正禁止）であるため、Literalのまま据え置く
（詳細は各モデルのdocstringおよび完了報告のTODOを参照）。

`str, Enum`の多重継承は docs/api/python-contract.md#enum利用方針 および
docs/api/models.md の`LearningStatus`が明示的に指定するパターンであり、
ruffのUP042（enum.StrEnumへの置き換え推奨）は本タスクの範囲では意図的に
抑制する（既存設計文書との整合を優先。将来的な docs 側の見直しはTODO参照）。
"""

from enum import Enum


class ConfidenceBand(str, Enum):  # noqa: UP042 -- docs/api/python-contract.mdが指定するパターン
    """Confidenceの信頼度バンド。"""

    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PipelineStage(str, Enum):  # noqa: UP042
    """中核パイプライン段階。"""

    LAYOUT_DETECTOR = "layout_detector"
    SECTION_PARSER = "section_parser"
    FIELD_EXTRACTOR = "field_extractor"
    NORMALIZER = "normalizer"
    VALIDATOR = "validator"


class ErrorCategory(str, Enum):  # noqa: UP042
    """未知パターンの原因分類。ADR-0012の優先順位分類に対応する。"""

    UNKNOWN_ALIAS = "unknown_alias"
    UNKNOWN_LAYOUT = "unknown_layout"
    KNOWLEDGE_GAP = "knowledge_gap"
    LAYOUT_GAP = "layout_gap"
    TRUE_EXCEPTION = "true_exception"


class RegressionStatus(str, Enum):  # noqa: UP042
    """Learning Datasetエントリの回帰テスト状態。"""

    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


class LearningStatus(str, Enum):  # noqa: UP042
    """Learning Datasetのライフサイクル状態。"""

    OPEN = "open"
    IN_REVIEW = "in_review"
    REFLECTED = "reflected"
    VERIFIED = "verified"
    WONTFIX = "wontfix"
