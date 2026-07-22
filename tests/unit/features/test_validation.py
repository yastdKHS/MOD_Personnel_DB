"""`validate_feature_ranges`の検証（Phase7 Task16-2）。

docs/api/models.md#featurevector が`features/`パッケージの責務として
委譲する「`_confidence`/`_rate`系の`float`値は`0.0`〜`1.0`」という値域検証。
"""

import pytest

from mod_personnel_db.features import FeatureRangeError, validate_feature_ranges


def test_in_range_confidence_and_rate_values_pass() -> None:
    validate_feature_ranges({"ocr_confidence": 0.5, "org_error_rate_90d": 1.0, "other": 42.0})


def test_boundary_values_are_accepted() -> None:
    validate_feature_ranges({"a_confidence": 0.0, "b_rate": 1.0})


def test_out_of_range_confidence_raises() -> None:
    with pytest.raises(FeatureRangeError):
        validate_feature_ranges({"ocr_confidence": 1.5})


def test_negative_rate_raises() -> None:
    with pytest.raises(FeatureRangeError):
        validate_feature_ranges({"error_rate": -0.1})


def test_non_ratio_suffixed_float_is_not_validated() -> None:
    validate_feature_ranges({"raw_field_avg_length": 999.0})


def test_non_float_values_are_not_validated() -> None:
    validate_feature_ranges({"layout_confidence": "high", "matched_confidence": True})
