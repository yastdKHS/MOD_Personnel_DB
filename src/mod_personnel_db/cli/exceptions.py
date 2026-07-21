"""CLI固有の例外。docs/api/interfaces.md#jobrunner, ADR-0046に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class CliCommandError(MODPersonnelDBError):
    """CLIコマンドの実行前提が満たされない場合（未知のコマンド、対象PDFが
    存在しない、必須オプションの未指定等）に送出する。
    """
