"""ドメインモデル共通のEnum定義。docs/api/python-contract.md#enum利用方針 に対応する。

対象は「3値以上、かつ複数箇所で再利用される値集合」。Repository実装
（repositories/sqlite/）が既に生のstrとして直接読み書きしている既存の
フィールド（KnowledgeItem.category, PdfRecord.status, Job.job_type/status,
ExportRecord.format, CandidateRecord.validation_status）は、本タスクの
対象外（Repository修正禁止）であるため、Literalのまま据え置く
（詳細は各モデルのdocstringおよび完了報告のTODOを参照）。

Enum実装はPhase2 Task3にて `str, Enum` の多重継承から `enum.StrEnum` へ
移行した（ADR-0030）。docs/api/python-contract.md・docs/api/models.mdも
同期更新済み。
"""

from enum import StrEnum


class ConfidenceBand(StrEnum):
    """Confidenceの信頼度バンド。"""

    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PipelineStageName(StrEnum):
    """中核パイプライン段階の名称。docs/architecture/learning_dataset.md に対応する。

    docs/api/pipeline.md が定義する`PipelineStage`（Stage実装が満たすProtocol、
    src/mod_personnel_db/pipeline/stage.py）とは別物であるため、命名を分離した
    （Phase2 Task3でPipeline Frameworkを実装するにあたり発見・是正）。
    """

    LAYOUT_DETECTOR = "layout_detector"
    SECTION_PARSER = "section_parser"
    FIELD_EXTRACTOR = "field_extractor"
    NORMALIZER = "normalizer"
    VALIDATOR = "validator"


class ErrorCategory(StrEnum):
    """未知パターンの原因分類。ADR-0012の優先順位分類に対応する。"""

    UNKNOWN_ALIAS = "unknown_alias"
    UNKNOWN_LAYOUT = "unknown_layout"
    KNOWLEDGE_GAP = "knowledge_gap"
    LAYOUT_GAP = "layout_gap"
    TRUE_EXCEPTION = "true_exception"


class RegressionStatus(StrEnum):
    """Learning Datasetエントリの回帰テスト状態。"""

    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


class LearningStatus(StrEnum):
    """Learning Datasetのライフサイクル状態。"""

    OPEN = "open"
    IN_REVIEW = "in_review"
    REFLECTED = "reflected"
    VERIFIED = "verified"
    WONTFIX = "wontfix"
