"""Section Parser固有の例外。docs/api/interfaces.md#sectionparser, ADR-0037に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class SectionParserError(MODPersonnelDBError):
    """Section Parserの実行中に発生した例外。

    セクション境界が見つからない・低Confidence等の内容品質の問題は例外では
    なく`SectionParseResult`（空の`sections`、低い`confidence`）として表現する
    （`run()`は正常終了する）。本例外は、入力の`LayoutArtifact`自体が不整合
    （後続処理を続行できない）である場合にのみ送出する。
    """
