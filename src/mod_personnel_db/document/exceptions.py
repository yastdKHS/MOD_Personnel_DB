"""Document Analyzer固有の例外。docs/api/interfaces.md#documentanalyzer, ADR-0032に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class DocumentAnalyzerError(MODPersonnelDBError):
    """Document Analyzerの実行中に発生した例外。

    PDFパースライブラリ固有の例外はここに集約し、`document/`パッケージの外へ
    ライブラリ固有例外を漏らさない（Task4禁止事項）。PDFの内容品質に起因する
    問題（破損・暗号化等）は例外ではなく`DocumentWarning`として`Document`に
    記録する。本例外は、ファイル不在・I/Oエラー等、解析そのものを実行できない
    場合にのみ送出する。
    """
