"""`get_feature`（Feature取得API）の単体テスト（Phase7 Task16-2）。"""

from mod_personnel_db.features import default_feature_vector, get_feature


def test_get_feature_returns_existing_value() -> None:
    vector = default_feature_vector()

    assert get_feature(vector, "raw_field_fill_rate") == 1.0


def test_get_feature_returns_default_for_missing_key() -> None:
    vector = default_feature_vector()

    assert get_feature(vector, "no_such_feature", default=0.0) == 0.0


def test_get_feature_returns_none_when_no_default_given() -> None:
    vector = default_feature_vector()

    assert get_feature(vector, "no_such_feature") is None
