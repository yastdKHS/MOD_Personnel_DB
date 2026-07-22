"""features/ パッケージ専用の例外階層。docs/api/python-contract.md の例外設計に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class FeatureStoreError(MODPersonnelDBError):
    """`features/`パッケージの全カスタム例外の基底クラス。"""


class FeatureRangeError(FeatureStoreError):
    """`FeatureVector.features`の値が、特徴量ごとに定義された値域を満たさない場合。

    docs/api/models.md#featurevector が定める「`*_confidence`系は`0.0`〜`1.0`の
    値域を満たす」という値域検証（`features/`パッケージの責務として明示的に
    委譲されている）の違反を表す。
    """


__all__ = ["FeatureRangeError", "FeatureStoreError"]
