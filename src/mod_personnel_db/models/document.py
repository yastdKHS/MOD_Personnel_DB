"""ドキュメント関連モデル。docs/api/models.md#document に対応する。

Version 2.0（ADR-0032, ADR-0033）: `Document`はPipelineを流れる「Document Identity」
であり、ページ単位の抽出済みテキストを保持しない。Version 1の`Document`/`Page`
（ページ単位のテキストを保持する設計）は、ADR-0032のMigration Planに従い
`DocumentV1`/`PageV1`として引き続き提供する（削除しない）。パイプライン上の
正式な型はPhase2 Task4時点でVersion 2.0の`Document`である。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from mod_personnel_db.models.ids import DocumentId, PdfId
from mod_personnel_db.models.values import Confidence, ModelValidationError

_SHA256_LENGTH = 64


@dataclass(frozen=True, slots=True)
class PageV1:
    """Version 1（Superseded, ADR-0032）。"""

    index: int
    text: str
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ModelValidationError("index must be >= 0")
        if self.width <= 0 or self.height <= 0:
            raise ModelValidationError("width/height must be positive")


@dataclass(frozen=True, slots=True)
class DocumentV1:
    """Version 1（Superseded, ADR-0032）。"""

    source_pdf_id: PdfId
    pages: tuple[PageV1, ...]
    analyzed_at: datetime

    def __post_init__(self) -> None:
        if len(self.pages) == 0:
            raise ModelValidationError("pages must not be empty")
        expected_indices = tuple(range(len(self.pages)))
        actual_indices = tuple(page.index for page in self.pages)
        if actual_indices != expected_indices:
            raise ModelValidationError("page indices must be a contiguous 0-based sequence")


class DocumentWarning(StrEnum):
    """Document Analyzerが生成する警告（ADR-0032）。"""

    ENCRYPTED = "encrypted"
    BROKEN_PDF = "broken_pdf"
    IMAGE_ONLY = "image_only"
    LARGE_PDF = "large_pdf"
    UNKNOWN_ENCODING = "unknown_encoding"
    UNSUPPORTED_VERSION = "unsupported_version"


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """PDFファイルそのものの静的属性（ADR-0033）。"""

    filename: str
    sha256: str
    file_size: int
    created_at: datetime | None
    modified_at: datetime | None
    pdf_version: str
    encrypted: bool

    def __post_init__(self) -> None:
        if len(self.sha256) != _SHA256_LENGTH:
            raise ModelValidationError(f"sha256 must be {_SHA256_LENGTH} hex characters")
        if self.file_size < 0:
            raise ModelValidationError("file_size must be >= 0")


@dataclass(frozen=True, slots=True)
class DocumentStatistics:
    """解析実行1回分の集計値（ADR-0033）。

    `text_length`はページ内文字数の軽量プローブによる計測値のみであり、抽出した
    テキスト本文そのものは保持しない（ADR-0032）。プローブ不可の場合は`None`。
    """

    page_count: int
    text_length: int | None
    image_count: int
    rotation_count: int
    analysis_time_ms: float

    def __post_init__(self) -> None:
        if self.page_count < 0:
            raise ModelValidationError("page_count must be >= 0")
        if self.text_length is not None and self.text_length < 0:
            raise ModelValidationError("text_length must be >= 0 or None")
        if self.image_count < 0:
            raise ModelValidationError("image_count must be >= 0")
        if self.rotation_count < 0:
            raise ModelValidationError("rotation_count must be >= 0")
        if self.analysis_time_ms < 0:
            raise ModelValidationError("analysis_time_ms must be >= 0")


@dataclass(frozen=True, slots=True)
class DocumentAnalysisResult:
    """`Document.analysis`として保持される（ADR-0032, ADR-0033）。"""

    metadata: DocumentMetadata
    statistics: DocumentStatistics
    warnings: tuple[DocumentWarning, ...]
    confidence: Confidence

    def __post_init__(self) -> None:
        if self.metadata.encrypted and DocumentWarning.ENCRYPTED not in self.warnings:
            raise ModelValidationError("encrypted metadata requires DocumentWarning.ENCRYPTED")


@dataclass(frozen=True, slots=True)
class Document:
    """Document Analyzerの出力（Version 2.0、ADR-0032）。Pipelineを流れる「Document Identity」。"""

    id: DocumentId
    source_pdf_id: PdfId
    analysis: DocumentAnalysisResult
    analyzed_at: datetime
    analyzer_version: str
