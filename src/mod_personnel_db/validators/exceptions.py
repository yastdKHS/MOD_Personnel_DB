"""Validator固有の例外。docs/api/interfaces.md#validator, ADR-0043に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class ValidatorError(MODPersonnelDBError):
    """Validatorの実行中に発生した例外。

    Validation NGは例外ではなく`ValidationResult`（`status="failed"`）として
    表現する（`run()`は正常終了する）。本例外は、入力の`NormalizedRecord`から
    `ValidationResult`を構築できない等、処理そのものを継続できない場合にのみ
    送出する。
    """
