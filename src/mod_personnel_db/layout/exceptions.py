"""Layout Detector固有の例外。docs/api/interfaces.md#layoutdetector, ADR-0035に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class LayoutDetectorError(MODPersonnelDBError):
    """Layout Detectorの実行中に発生した例外。

    pypdf・PyYAML固有の例外はここに集約し、`layout/`パッケージの外へ
    ライブラリ固有例外を漏らさない。未知の様式・低Confidenceはこの例外では
    なく`LayoutWarning`として`LayoutDetectionResult`に記録する
    （`run()`は正常終了する）。本例外は、PDFの再読込自体の失敗や
    `LayoutDefinition`のYAMLロード失敗等、判定処理そのものを実行できない
    場合にのみ送出する。
    """
