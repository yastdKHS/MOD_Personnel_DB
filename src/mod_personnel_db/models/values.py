"""共有値オブジェクト。docs/api/models.md#confidence に対応する。"""

from dataclasses import dataclass
from typing import Literal

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class ModelValidationError(MODPersonnelDBError):
    """モデルのValidation Rule違反。"""


@dataclass(frozen=True, slots=True)
class Confidence:
    score: float
    band: Literal["verified", "high", "medium", "low"]

    def __post_init__(self) -> None:
        if not (0.0 <= self.score <= 1.0):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")
