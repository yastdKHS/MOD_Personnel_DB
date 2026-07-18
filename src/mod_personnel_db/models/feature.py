"""FeatureStore出力モデル。docs/api/models.md#featurevector に対応する。

float値ごとの値域検証（例: *_confidence系は0.0〜1.0）はfeatures/パッケージ
（未実装）の責務として設計時点で明示的に委譲されており、本モデルでは
実装しない（docs/api/models.md#featurevector）。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from mod_personnel_db.models.ids import CandidateId
from mod_personnel_db.models.values import ModelValidationError


@dataclass(frozen=True, slots=True)
class FeatureVector:
    subject_ref: CandidateId
    features: Mapping[str, float | str | bool]
    feature_set_version: str
    computed_at: datetime

    def __post_init__(self) -> None:
        if len(self.features) == 0:
            raise ModelValidationError("features must not be empty")
        if self.feature_set_version == "":
            raise ModelValidationError("feature_set_version must not be empty")
