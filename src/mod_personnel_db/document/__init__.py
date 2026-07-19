"""Document Analyzer公開窓口。docs/api/interfaces.md#documentanalyzer に対応する

Phase2 Task4で実装。
"""

from mod_personnel_db.document.analyzer import DocumentAnalyzer
from mod_personnel_db.document.exceptions import DocumentAnalyzerError

__all__ = [
    "DocumentAnalyzer",
    "DocumentAnalyzerError",
]
