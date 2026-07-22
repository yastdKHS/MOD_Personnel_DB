"""テスト用の`MockFeatureStore`実装。実際の特徴量計算ロジックを一切行わない。

呼び出し元（将来の`fetch/`・`services/`・`normalizers/`・`validators/`の
テストコード等）が、あらかじめ用意した`FeatureVector`を`compute()`から
返させることで、`features/`の実装詳細に依存しない結合テストを書けるように
するためのモックである。
"""

from __future__ import annotations

from datetime import UTC, datetime

from mod_personnel_db.features.store import FEATURE_SET_VERSION
from mod_personnel_db.models import CandidateId, FeatureVector, NormalizedRecord, RawRecord


class MockFeatureStore:
    """呼び出し順に事前設定した`FeatureVector`を返す、またはデフォルトを生成するモック実装。"""

    def __init__(self, responses: list[FeatureVector] | None = None) -> None:
        self._responses = list(responses) if responses is not None else None
        self.calls: list[RawRecord | NormalizedRecord] = []

    def compute(self, subject: RawRecord | NormalizedRecord) -> FeatureVector:
        self.calls.append(subject)
        if self._responses is not None:
            return self._responses[len(self.calls) - 1]
        return default_feature_vector()


def default_feature_vector(subject_ref: CandidateId | None = None) -> FeatureVector:
    """既定のダミー`FeatureVector`を生成する（`MockFeatureStore`の既定応答）。"""
    return FeatureVector(
        subject_ref=subject_ref if subject_ref is not None else CandidateId(0),
        features={"raw_field_fill_rate": 1.0, "ocr_suspicious_char_rate": 0.0},
        feature_set_version=FEATURE_SET_VERSION,
        computed_at=datetime.now(UTC),
    )


__all__ = ["MockFeatureStore", "default_feature_vector"]
