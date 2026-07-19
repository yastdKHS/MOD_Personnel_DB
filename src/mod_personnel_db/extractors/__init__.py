"""Field Extractor公開窓口。docs/api/interfaces.md#fieldextractor, ADR-0038に対応する。

公開APIは`FieldExtractor.run()`のみ。`extractors/`パッケージは
`repositories/`・`knowledge/`・`normalizers/`・`validators/`・`review/`・
`sqlite3`のいずれにも依存しない。
"""

from mod_personnel_db.extractors.exceptions import FieldExtractorError
from mod_personnel_db.extractors.extractor import FieldExtractor

__all__ = [
    "FieldExtractor",
    "FieldExtractorError",
]
