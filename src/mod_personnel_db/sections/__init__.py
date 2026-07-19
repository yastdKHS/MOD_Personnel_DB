"""Section Parser公開窓口。docs/api/interfaces.md#sectionparser, ADR-0037に対応する。

公開APIは`SectionParser.run()`のみ。`sections/`パッケージはPDFファイルを
直接読み込まず、`pypdf`等のPDF解析ライブラリにも依存しない。利用できる
PDF由来のテキストはLayout Detectorが生成した`LayoutArtifact.pages`のみ
である（ADR-0037）。
"""

from mod_personnel_db.sections.exceptions import SectionParserError
from mod_personnel_db.sections.parser import SectionParser

__all__ = [
    "SectionParser",
    "SectionParserError",
]
