"""Field Extractor固有の例外。docs/api/interfaces.md#fieldextractor, ADR-0038に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class FieldExtractorError(MODPersonnelDBError):
    """Field Extractorの実行中に発生した例外。

    列認識できない・低Confidence等の内容品質の問題は例外ではなく
    `FieldExtractionResult`（空の`records`、低い`confidence`）として表現する
    （`run()`は正常終了する）。本例外は、入力の`PersonnelSection`から
    `RawRecord`を構築できない等、処理そのものを継続できない場合にのみ
    送出する。
    """
