"""`FeatureVector.features`の値域検証。docs/api/models.md#featurevector が
`features/`パッケージの責務として明示的に委譲する検証を実装する。

対象は`_confidence`または`_rate`で終わる特徴量名の`float`値のみとし、
`0.0`〜`1.0`の範囲内であることを要求する（`ocr_confidence`,
`org_error_rate_90d`等）。それ以外の特徴量名・型（`str`/`bool`、および
上記接尾辞に該当しない`float`）は値域検証の対象外とする。
"""

from collections.abc import Mapping

from mod_personnel_db.features.exceptions import FeatureRangeError

_RATIO_SUFFIXES = ("_confidence", "_rate")


def validate_feature_ranges(features: Mapping[str, float | str | bool]) -> None:
    """`_confidence`/`_rate`接尾辞の`float`特徴量が`0.0`〜`1.0`の範囲内であることを検証する。

    範囲外の値が見つかった場合は`FeatureRangeError`を送出する。
    """
    for name, value in features.items():
        if not isinstance(value, float):
            continue
        if not name.endswith(_RATIO_SUFFIXES):
            continue
        if not (0.0 <= value <= 1.0):
            raise FeatureRangeError(f"feature '{name}' must be within [0.0, 1.0], got {value}")


__all__ = ["validate_feature_ranges"]
