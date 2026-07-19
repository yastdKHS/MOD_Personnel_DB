"""Knowledge Base関連モデル。docs/api/models.md のKnowledgeItem/Layout/KnowledgeSnapshotに対応。"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

from mod_personnel_db.models.ids import KnowledgeItemId, LayoutId
from mod_personnel_db.models.values import ModelValidationError

KnowledgeCategory = Literal[
    "organization",
    "position",
    "rank",
    "alias",
    "historical",
    "typography",
    "layout",
    "validation",
]


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    id: KnowledgeItemId
    category: KnowledgeCategory
    source_file: str
    item_key: str
    canonical_value: str
    effective_from: date | None
    effective_to: date | None
    provenance_source: str
    version: int

    def __post_init__(self) -> None:
        # ネストしたifはmypyのOptional narrowing維持のため意図的（SIM102対象外）。
        if self.effective_from is not None and self.effective_to is not None:  # noqa: SIM102
            if self.effective_to <= self.effective_from:
                raise ModelValidationError("effective_to must be > effective_from")


@dataclass(frozen=True, slots=True)
class Layout:
    id: LayoutId | None
    era_id: str
    version: int
    manifest_path: str
    manifest_checksum: str
    valid_from: date
    valid_to: date | None
    status: Literal["active", "deprecated"]

    def __post_init__(self) -> None:
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ModelValidationError("valid_to must be > valid_from")


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    """Normalizerにコンストラクタ注入される、ある時点の知識ベース全体のスナップショット（ADR-0040）。"""

    items: tuple[KnowledgeItem, ...]
    snapshot_checksum: str
    as_of: date

    def __post_init__(self) -> None:
        if self.snapshot_checksum == "":
            raise ModelValidationError("snapshot_checksum must not be empty")
