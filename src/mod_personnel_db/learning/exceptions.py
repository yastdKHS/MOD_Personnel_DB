"""LearningService固有の例外。docs/api/interfaces.md#learningservice に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class LearningServiceError(MODPersonnelDBError):
    """LearningServiceのライフサイクル管理規則違反。

    不正な初期状態でのrecord_error()、状態遷移グラフ
    （docs/architecture/learning_dataset.md#ライフサイクル）に存在しない
    transition()、および存在しないLearningRecordIdへのtransition()呼び出しで
    送出する。RepositoryError（永続化層の例外）とは区別する。
    """
