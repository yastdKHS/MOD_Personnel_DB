"""`features/`例外階層の検証（Phase7 Task16-2）。"""

from mod_personnel_db.features import FeatureRangeError, FeatureStoreError
from mod_personnel_db.utils.exceptions import MODPersonnelDBError


def test_feature_store_error_is_mod_personnel_db_error() -> None:
    assert issubclass(FeatureStoreError, MODPersonnelDBError)


def test_feature_range_error_is_feature_store_error() -> None:
    assert issubclass(FeatureRangeError, FeatureStoreError)
