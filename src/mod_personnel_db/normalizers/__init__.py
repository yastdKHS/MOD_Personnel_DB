"""Normalizer公開窓口。docs/api/interfaces.md#normalizer, ADR-0040に対応する。"""

from mod_personnel_db.normalizers.exceptions import NormalizerError
from mod_personnel_db.normalizers.normalizer import Normalizer

__all__ = ["Normalizer", "NormalizerError"]
