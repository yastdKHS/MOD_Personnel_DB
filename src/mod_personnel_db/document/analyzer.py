"""Document Analyzer実装。docs/api/interfaces.md#documentanalyzer, ADR-0032, ADR-0033に対応する。

PDF解析（構造抽出）・OCR・文字抽出・Layout/Section/Field解析は行わない。PDFの
存在確認・メタデータ取得・健全性確認・基本統計・警告生成のみを責務とする。
"""

import hashlib
import io
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from pypdf import PageObject, PdfReader
from pypdf.errors import PyPdfError

from mod_personnel_db.document.exceptions import DocumentAnalyzerError
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    Document,
    DocumentAnalysisResult,
    DocumentId,
    DocumentMetadata,
    DocumentStatistics,
    DocumentWarning,
    PdfRecord,
)
from mod_personnel_db.pipeline import PipelineContext

ANALYZER_VERSION = "v0.1.0"
DEFAULT_LARGE_PDF_THRESHOLD_BYTES = 50 * 1024 * 1024

_PDF_HEADER_PATTERN = re.compile(r"%PDF-(\d+\.\d+)")
_SUPPORTED_PDF_VERSIONS = frozenset({"1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "2.0"})
_DEGRADED_WARNINGS = frozenset({DocumentWarning.BROKEN_PDF, DocumentWarning.ENCRYPTED})


@dataclass(frozen=True, slots=True)
class _ProbeResult:
    """PDFライブラリを用いた構造プローブの内部結果（`document/`パッケージ外には公開しない）。"""

    page_count: int
    image_count: int
    rotation_count: int
    text_length: int | None
    warnings: frozenset[DocumentWarning]


class DocumentAnalyzer:
    """`PipelineStage[PdfRecord, Document]`を実装する。公開APIは`run()`のみ。"""

    def __init__(
        self,
        *,
        analyzer_version: str = ANALYZER_VERSION,
        large_pdf_threshold_bytes: int = DEFAULT_LARGE_PDF_THRESHOLD_BYTES,
    ) -> None:
        self._analyzer_version = analyzer_version
        self._large_pdf_threshold_bytes = large_pdf_threshold_bytes

    def run(self, context: PipelineContext, source: PdfRecord) -> Document:
        del context
        if source.id is None:
            raise DocumentAnalyzerError("PdfRecord.id must be set before Document Analyzer runs")

        path = _ensure_exists(source.file_path)
        started_at = monotonic()
        raw_bytes = _read_bytes(path)
        stat = path.stat()
        probe = _probe(raw_bytes)
        pdf_version = _detect_pdf_version(raw_bytes)
        warnings = _collect_warnings(
            probe, pdf_version, stat.st_size, self._large_pdf_threshold_bytes
        )
        elapsed_ms = (monotonic() - started_at) * 1000

        metadata = DocumentMetadata(
            filename=path.name,
            sha256=hashlib.sha256(raw_bytes).hexdigest(),
            file_size=stat.st_size,
            created_at=_to_datetime(stat.st_ctime),
            modified_at=_to_datetime(stat.st_mtime),
            pdf_version=pdf_version or "unknown",
            encrypted=DocumentWarning.ENCRYPTED in warnings,
        )
        statistics = DocumentStatistics(
            page_count=probe.page_count,
            text_length=probe.text_length,
            image_count=probe.image_count,
            rotation_count=probe.rotation_count,
            analysis_time_ms=elapsed_ms,
        )
        analysis = DocumentAnalysisResult(
            metadata=metadata,
            statistics=statistics,
            warnings=tuple(sorted(warnings, key=lambda warning: warning.value)),
            confidence=_compute_confidence(warnings),
        )
        return Document(
            id=DocumentId(secrets.randbits(63)),
            source_pdf_id=source.id,
            analysis=analysis,
            analyzed_at=datetime.now(UTC),
            analyzer_version=self._analyzer_version,
        )


def _ensure_exists(file_path: str) -> Path:
    path = Path(file_path)
    if not path.is_file():
        raise DocumentAnalyzerError(f"PDF file not found: {file_path}")
    return path


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise DocumentAnalyzerError(f"failed to read PDF file: {path}") from exc


def _to_datetime(epoch_seconds: float) -> datetime:
    return datetime.fromtimestamp(epoch_seconds, tz=UTC)


def _detect_pdf_version(raw_bytes: bytes) -> str | None:
    header = raw_bytes[:16].decode("ascii", errors="replace")
    match = _PDF_HEADER_PATTERN.match(header)
    return match.group(1) if match else None


def _probe(raw_bytes: bytes) -> _ProbeResult:
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except PyPdfError:
        return _ProbeResult(0, 0, 0, None, frozenset({DocumentWarning.BROKEN_PDF}))

    warnings: set[DocumentWarning] = set()
    if reader.is_encrypted:
        warnings.add(DocumentWarning.ENCRYPTED)

    try:
        page_count = len(reader.pages)
    except PyPdfError:
        warnings.add(DocumentWarning.BROKEN_PDF)
        return _ProbeResult(0, 0, 0, None, frozenset(warnings))

    image_count, rotation_count, counted_text_length, encoding_ok = _inspect_pages(reader.pages)
    text_length: int | None = counted_text_length
    if not encoding_ok:
        warnings.add(DocumentWarning.UNKNOWN_ENCODING)
        text_length = None

    return _ProbeResult(page_count, image_count, rotation_count, text_length, frozenset(warnings))


def _inspect_pages(pages: list[PageObject]) -> tuple[int, int, int, bool]:
    image_count = 0
    rotation_count = 0
    text_length = 0
    encoding_ok = True
    for page in pages:
        contribution = _inspect_page(page)
        if contribution is None:
            encoding_ok = False
            continue
        page_images, page_rotated, page_text_length = contribution
        image_count += page_images
        rotation_count += 1 if page_rotated else 0
        text_length += page_text_length
    return image_count, rotation_count, text_length, encoding_ok


def _inspect_page(page: PageObject) -> tuple[int, bool, int] | None:
    # ruffのフォーマッタ（本環境: 0.15.22）が `except (A, B):` の括弧を誤って
    # 削除し無効な構文を生成するバグを踏むため、意図的に2つのexcept節に分けている
    # （単一のタプル化例外節にしない）。
    try:
        image_count = len(page.images)
        rotated = page.rotation % 360 != 0
        text_length = len(page.extract_text())
    except PyPdfError:
        return None
    except UnicodeError:
        return None
    return image_count, rotated, text_length


def _collect_warnings(
    probe: _ProbeResult, pdf_version: str | None, file_size: int, large_pdf_threshold_bytes: int
) -> set[DocumentWarning]:
    warnings = set(probe.warnings)
    if file_size > large_pdf_threshold_bytes:
        warnings.add(DocumentWarning.LARGE_PDF)
    if pdf_version is None or pdf_version not in _SUPPORTED_PDF_VERSIONS:
        warnings.add(DocumentWarning.UNSUPPORTED_VERSION)
    if (
        probe.page_count > 0
        and not (warnings & _DEGRADED_WARNINGS)
        and (probe.text_length or 0) == 0
    ):
        warnings.add(DocumentWarning.IMAGE_ONLY)
    return warnings


def _compute_confidence(warnings: set[DocumentWarning]) -> Confidence:
    if DocumentWarning.BROKEN_PDF in warnings:
        return Confidence(score=0.0, band=ConfidenceBand.LOW)
    if warnings:
        return Confidence(score=0.6, band=ConfidenceBand.MEDIUM)
    return Confidence(score=1.0, band=ConfidenceBand.VERIFIED)
