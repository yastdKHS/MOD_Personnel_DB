"""Normalizer関連モデル。docs/api/models.md#normalizationresult に対応する（ADR-0040）。

`Normalizer.run()`の戻り値（`NormalizationResult`）と、レコード評価の中間結果
（`NormalizationCandidate`/`NormalizationEvidence`/`NormalizedField`）を定義する。
永続化対象の`NormalizedRecord`自体は`models/candidate.py`に定義される
（Phase1設計より無変更、ADR-0040）。`NormalizedField.name`は`RawField.name`と
同じキー（`column_N`等）であり、意味的フィールド名へのリネームは行わない。
"""

from dataclasses import dataclass

from mod_personnel_db.models.candidate import NormalizedRecord
from mod_personnel_db.models.ids import KnowledgeItemId
from mod_personnel_db.models.values import Confidence, ModelValidationError

_SCORE_RANGE = (0.0, 1.0)


@dataclass(frozen=True, slots=True)
class NormalizedField:
    """1つの列の正規化結果。"""

    name: str
    raw: str
    value: str
    normalization_method: str

    def __post_init__(self) -> None:
        if self.name == "":
            raise ModelValidationError("name must not be empty")
        if self.value == "":
            raise ModelValidationError("value must not be empty")
        if self.normalization_method == "":
            raise ModelValidationError("normalization_method must not be empty")


@dataclass(frozen=True, slots=True)
class NormalizationEvidence:
    """1レコード分の正規化の根拠。"""

    layout_id: str
    knowledge_version: str
    matched_item_ids: tuple[KnowledgeItemId, ...]

    def __post_init__(self) -> None:
        if self.layout_id == "":
            raise ModelValidationError("layout_id must not be empty")
        if self.knowledge_version == "":
            raise ModelValidationError("knowledge_version must not be empty")


@dataclass(frozen=True, slots=True)
class NormalizationCandidate:
    """1レコード分の評価結果。"""

    record_index: int
    score: float
    fields: tuple[NormalizedField, ...]
    evidence: NormalizationEvidence

    def __post_init__(self) -> None:
        if self.record_index < 0:
            raise ModelValidationError("record_index must be >= 0")
        if not (_SCORE_RANGE[0] <= self.score <= _SCORE_RANGE[1]):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Normalizerの戻り値（ADR-0040）。"""

    records: tuple[NormalizedRecord, ...]
    candidates: tuple[NormalizationCandidate, ...]
    confidence: Confidence
