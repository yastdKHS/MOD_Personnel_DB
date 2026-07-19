"""Layout Detector公開窓口。docs/api/interfaces.md#layoutdetector, ADR-0035, ADR-0036に対応する。

`document/`パッケージ（Document Analyzer）と同様、公開APIは`LayoutDetector.run()`のみ。
`layout/`パッケージだけが、`document.file_path`を用いてPDF本文・文字列・Font・
Bounding Box・Drawing・Rotation・画像・Annotationへアクセスする（ADR-0035）。
"""

from mod_personnel_db.layout.definitions import load_layout_definition, load_layout_definitions
from mod_personnel_db.layout.detector import LayoutDetector
from mod_personnel_db.layout.exceptions import LayoutDetectorError

__all__ = [
    "LayoutDetector",
    "LayoutDetectorError",
    "load_layout_definition",
    "load_layout_definitions",
]
