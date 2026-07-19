"""Layout Detector実装。docs/api/interfaces.md#layoutdetector, ADR-0035/0036/0037に対応する。

Document Analyzer（段階1）とは独立に、`document.file_path`を用いてPDFを自ら
再読込し、様式判定に必要な特徴量（Evidence）を抽出し、注入された
`LayoutDefinition`群と照合する。戻り値は`LayoutArtifact`（ADR-0037）であり、
判定結果（`LayoutDetectionResult`、`.detection`）に加え、再読込した各ページの
生テキストを保持する——これがSection ParserがPDF本文を得る唯一の経路となる。
Section生成・Field抽出・Regexによる値抽出・Knowledge参照・Normalizer/
Validator/Repository参照・SQLite参照は行わない。
"""

import io
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pypdf import PageObject, PdfReader
from pypdf.errors import PyPdfError

from mod_personnel_db.layout.exceptions import LayoutDetectorError
from mod_personnel_db.models import (
    BoundingBoxStatistics,
    ConfidenceBand,
    Document,
    LayoutArtifact,
    LayoutArtifactPage,
    LayoutCandidate,
    LayoutConfidence,
    LayoutDefinition,
    LayoutDetectionResult,
    LayoutEvidence,
    LayoutMatch,
    LayoutRule,
    LayoutRuleKind,
    LayoutWarning,
    PageStatistics,
    RotationStatistics,
)
from mod_personnel_db.pipeline import PipelineContext

DEFAULT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.3
_AMBIGUITY_MARGIN = 0.05


@dataclass(frozen=True, slots=True)
class _PageFeatures:
    """PDFの1ページ分から抽出した生特徴量（`layout/`パッケージ外には公開しない）。"""

    char_count: int
    width: float
    height: float
    rotation: int
    font_names: frozenset[str]
    text: str


class LayoutDetector:
    """`PipelineStage[Document, LayoutArtifact]`を実装する。公開APIは`run()`のみ。"""

    def __init__(
        self,
        *,
        layout_definitions: tuple[LayoutDefinition, ...],
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    ) -> None:
        self._layout_definitions = layout_definitions
        self._confidence_threshold = confidence_threshold
        self._low_confidence_threshold = low_confidence_threshold

    def run(self, context: PipelineContext, document: Document) -> LayoutArtifact:
        del context
        raw_bytes = _read_bytes(document.file_path)
        reader = _open_reader(raw_bytes)
        pages = _extract_page_features(reader)
        evidence = _build_evidence(pages)
        candidates = _score_candidates(self._layout_definitions, evidence)
        detection = _assemble_result(
            candidates,
            self._layout_definitions,
            evidence,
            self._confidence_threshold,
            self._low_confidence_threshold,
        )
        return LayoutArtifact(
            source_pdf_id=document.source_pdf_id,
            detection=detection,
            pages=tuple(
                LayoutArtifactPage(index=index, text=page.text) for index, page in enumerate(pages)
            ),
        )


def _read_bytes(file_path: str) -> bytes:
    try:
        return Path(file_path).read_bytes()
    except OSError as exc:
        raise LayoutDetectorError(f"failed to read PDF file: {file_path}") from exc


def _open_reader(raw_bytes: bytes) -> PdfReader:
    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
        _ = len(reader.pages)
    except PyPdfError as exc:
        raise LayoutDetectorError("failed to parse PDF for layout detection") from exc
    return reader


def _extract_page_features(reader: PdfReader) -> tuple[_PageFeatures, ...]:
    return tuple(_page_features(page) for page in reader.pages)


def _page_features(page: PageObject) -> _PageFeatures:
    text = _extract_text(page)
    mediabox = page.mediabox
    rotation = page.rotation % 360
    return _PageFeatures(
        char_count=len(text),
        width=float(mediabox.width),
        height=float(mediabox.height),
        rotation=rotation,
        font_names=_font_names(page),
        text=text,
    )


def _extract_text(page: PageObject) -> str:
    # ruffのフォーマッタ（本環境: 0.15.22）が `except (A, B):` の括弧を誤って
    # 削除し無効な構文を生成するバグを踏むため、意図的に2つのexcept節に分けている。
    try:
        return page.extract_text()
    except PyPdfError:
        return ""
    except UnicodeError:
        return ""


def _font_names(page: PageObject) -> frozenset[str]:
    resources = page.get("/Resources")
    if resources is None:
        return frozenset()
    fonts = resources.get("/Font")
    if fonts is None:
        return frozenset()
    names = {name for name in (_base_font_name(ref) for ref in fonts.values()) if name is not None}
    return frozenset(names)


def _base_font_name(font_ref: object) -> str | None:
    get_object = getattr(font_ref, "get_object", None)
    if get_object is None:
        return None
    font_obj = get_object()
    base_font = font_obj.get("/BaseFont") if hasattr(font_obj, "get") else None
    return str(base_font).lstrip("/") if base_font is not None else None


def _build_evidence(pages: tuple[_PageFeatures, ...]) -> LayoutEvidence:
    page_count = len(pages)
    average_char_count = sum(page.char_count for page in pages) / page_count if page_count else 0.0
    average_width = sum(page.width for page in pages) / page_count if page_count else 0.0
    average_height = sum(page.height for page in pages) / page_count if page_count else 0.0
    rotated_page_count = sum(1 for page in pages if page.rotation != 0)
    line_count, block_count = _line_and_block_totals(pages)
    font_statistics = tuple(sorted({name for page in pages for name in page.font_names}))

    page_statistics = PageStatistics(page_count=page_count, average_char_count=average_char_count)
    bbox_statistics = BoundingBoxStatistics(
        average_width=average_width, average_height=average_height
    )
    rotation_statistics = RotationStatistics(
        rotated_page_count=rotated_page_count, dominant_rotation=_dominant_rotation(pages)
    )
    return LayoutEvidence(
        font_statistics=font_statistics,
        page_statistics=page_statistics,
        bbox_statistics=bbox_statistics,
        rotation_statistics=rotation_statistics,
        header_signature=_signature_line(pages[0].text) if pages else None,
        footer_signature=_signature_line(pages[-1].text, from_end=True) if pages else None,
        line_statistics=line_count / page_count if page_count else 0.0,
        block_statistics=block_count / page_count if page_count else 0.0,
    )


def _dominant_rotation(pages: tuple[_PageFeatures, ...]) -> int:
    if not pages:
        return 0
    counts = Counter(page.rotation for page in pages)
    return counts.most_common(1)[0][0]


def _line_and_block_totals(pages: tuple[_PageFeatures, ...]) -> tuple[int, int]:
    line_count = 0
    block_count = 0
    for page in pages:
        lines = [line for line in page.text.splitlines() if line.strip()]
        blocks = [block for block in page.text.split("\n\n") if block.strip()]
        line_count += len(lines)
        block_count += len(blocks)
    return line_count, block_count


def _signature_line(text: str, *, from_end: bool = False) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    return lines[-1] if from_end else lines[0]


def _score_candidates(
    layout_definitions: tuple[LayoutDefinition, ...], evidence: LayoutEvidence
) -> tuple[LayoutCandidate, ...]:
    candidates = [_evaluate_definition(definition, evidence) for definition in layout_definitions]
    return tuple(sorted(candidates, key=lambda candidate: candidate.score, reverse=True))


def _evaluate_definition(definition: LayoutDefinition, evidence: LayoutEvidence) -> LayoutCandidate:
    matched: list[LayoutMatch] = []
    failed: list[LayoutMatch] = []
    matched_weight = 0.0
    total_weight = sum(rule.weight for rule in definition.rules)

    for rule in definition.rules:
        ok, detail = _evaluate_rule(rule, evidence)
        match = LayoutMatch(rule_id=rule.rule_id, matched=ok, detail=detail)
        if ok:
            matched.append(match)
            matched_weight += rule.weight
        else:
            failed.append(match)

    score = matched_weight / total_weight if total_weight else 0.0
    return LayoutCandidate(
        layout_id=definition.era_id,
        score=score,
        matched_rules=tuple(matched),
        failed_rules=tuple(failed),
    )


def _evaluate_rule(rule: LayoutRule, evidence: LayoutEvidence) -> tuple[bool, str | None]:
    if rule.kind == LayoutRuleKind.HEADER_PATTERN:
        return _pattern_match(rule.value, evidence.header_signature)
    if rule.kind == LayoutRuleKind.FOOTER_PATTERN:
        return _pattern_match(rule.value, evidence.footer_signature)
    if rule.kind == LayoutRuleKind.MIN_PAGE_COUNT:
        return _min_page_count_match(rule.value, evidence.page_statistics.page_count)
    return _font_name_contains_match(rule.value, evidence.font_statistics)


def _pattern_match(pattern: str, signature: str | None) -> tuple[bool, str | None]:
    if signature is None:
        return False, "signature not available"
    return (pattern in signature), f"signature={signature!r}"


def _min_page_count_match(value: str, page_count: int) -> tuple[bool, str | None]:
    try:
        threshold = int(value)
    except ValueError:
        return False, f"invalid MIN_PAGE_COUNT value: {value!r}"
    return (page_count >= threshold), f"page_count={page_count}"


def _font_name_contains_match(
    value: str, font_statistics: tuple[str, ...]
) -> tuple[bool, str | None]:
    matched = any(value in font for font in font_statistics)
    return matched, f"font_statistics={font_statistics!r}"


def _assemble_result(
    candidates: tuple[LayoutCandidate, ...],
    layout_definitions: tuple[LayoutDefinition, ...],
    evidence: LayoutEvidence,
    confidence_threshold: float,
    low_confidence_threshold: float,
) -> LayoutDetectionResult:
    if not candidates:
        return LayoutDetectionResult(
            layout_id=None,
            layout_version=None,
            confidence=LayoutConfidence(score=0.0, band=ConfidenceBand.LOW),
            candidate_layouts=candidates,
            evidence=evidence,
            warnings=(LayoutWarning.NO_MATCH,),
        )

    winner = candidates[0]
    confidence = LayoutConfidence(score=winner.score, band=_confidence_band(winner.score))
    warnings = _collect_warnings(candidates, winner, confidence_threshold, low_confidence_threshold)

    if winner.score < confidence_threshold:
        return LayoutDetectionResult(
            layout_id=None,
            layout_version=None,
            confidence=confidence,
            candidate_layouts=candidates,
            evidence=evidence,
            warnings=warnings,
        )

    return LayoutDetectionResult(
        layout_id=winner.layout_id,
        layout_version=_version_for(winner.layout_id, layout_definitions),
        confidence=confidence,
        candidate_layouts=candidates,
        evidence=evidence,
        warnings=warnings,
    )


def _collect_warnings(
    candidates: tuple[LayoutCandidate, ...],
    winner: LayoutCandidate,
    confidence_threshold: float,
    low_confidence_threshold: float,
) -> tuple[LayoutWarning, ...]:
    warnings: set[LayoutWarning] = set()
    if winner.score < low_confidence_threshold:
        warnings.add(LayoutWarning.NO_MATCH)
    elif winner.score < confidence_threshold:
        warnings.add(LayoutWarning.LOW_CONFIDENCE)
    if (
        len(candidates) >= 2
        and winner.score >= confidence_threshold
        and (candidates[0].score - candidates[1].score) < _AMBIGUITY_MARGIN
    ):
        warnings.add(LayoutWarning.AMBIGUOUS_CANDIDATES)
    return tuple(sorted(warnings, key=lambda warning: warning.value))


def _confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.9:
        return ConfidenceBand.VERIFIED
    if score >= 0.75:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


def _version_for(era_id: str, layout_definitions: tuple[LayoutDefinition, ...]) -> int:
    for definition in layout_definitions:
        if definition.era_id == era_id:
            return definition.version
    raise LayoutDetectorError(f"no LayoutDefinition found for era_id={era_id}")
