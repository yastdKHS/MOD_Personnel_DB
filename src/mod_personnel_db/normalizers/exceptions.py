"""Normalizer固有の例外。docs/api/interfaces.md#normalizer, ADR-0040に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class NormalizerError(MODPersonnelDBError):
    """Normalizerの実行中に発生した例外。

    低Confidence・Knowledge未一致等の内容品質の問題は例外ではなく
    `NormalizationResult`（空の`records`、低い`confidence`）として表現する
    （`run()`は正常終了する）。本例外は、入力の`RawRecord`から`NormalizedRecord`を
    構築できない等、処理そのものを継続できない場合にのみ送出する。
    """
