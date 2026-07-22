"""FeatureStore契約（Protocol）と実装。Phase7 Task16-2に対応する。

docs/api/interfaces.md#featurestore が定める`FeatureStore`Protocol
（`compute(subject: RawRecord | NormalizedRecord) -> FeatureVector`）と、
docs/api/package-design.md のfeatures/節（Phase7 Task16-0で設計確定）が
定める統合方式を実装する。

`Confidence`算出等に用いる派生特徴量（`FeatureVector`、`models/feature.py`
で定義済み）を計算する。V2.0時点では永続ストレージを持たず、都度計算
（on-demand）する。`normalizers/`・`validators/`は本パッケージを直接
importしない。`JobRunner`（`pipeline/job_runner.py`、未実装のためこの
Task16-2では配線しない）が本パッケージを呼び出し、計算結果を
`Normalizer`/`Validator`のコンストラクタへ値オブジェクトとして注入する
設計である（ADR-0040/ADR-0041のKnowledgeSnapshot/ValidationRuleSet注入
パターンに準じる）。

具象実装（`DefaultFeatureStore`）・テスト用モック実装（`MockFeatureStore`）
はそれぞれ`features.store`・`features.mock`から提供する。
"""

from typing import Protocol

from mod_personnel_db.features.exceptions import FeatureRangeError, FeatureStoreError
from mod_personnel_db.features.mock import MockFeatureStore, default_feature_vector
from mod_personnel_db.features.store import FEATURE_SET_VERSION, DefaultFeatureStore
from mod_personnel_db.features.validation import validate_feature_ranges
from mod_personnel_db.models import FeatureVector, NormalizedRecord, RawRecord


class FeatureStore(Protocol):
    """Confidence算出等に使う派生特徴量を計算する（V2.0時点では永続化せず都度計算）。"""

    def compute(self, subject: RawRecord | NormalizedRecord) -> FeatureVector:
        """`subject`から`FeatureVector`を計算する。"""
        ...


def get_feature(
    vector: FeatureVector, name: str, default: float | str | bool | None = None
) -> float | str | bool | None:
    """`FeatureVector`から特徴量`name`の値を取得する（Feature取得API）。

    `name`が存在しない場合は`default`を返す。
    """
    return vector.features.get(name, default)


__all__ = [
    "FEATURE_SET_VERSION",
    "DefaultFeatureStore",
    "FeatureRangeError",
    "FeatureStore",
    "FeatureStoreError",
    "MockFeatureStore",
    "default_feature_vector",
    "get_feature",
    "validate_feature_ranges",
]
