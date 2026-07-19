"""Section Parser実装。docs/api/interfaces.md#sectionparser, ADR-0037に対応する。

Layout Detector（段階2）が生成した`LayoutArtifact`のみを入力とする（段階3）。
PDF再読込・文字列抽出・RegexによるField抽出・Knowledge参照・Normalizer/
Validator/Repository参照・SQLite参照・Review参照・JSON生成・FTPは行わない。
`LayoutArtifact.pages`のテキストからHeader/Body/Footerを判定し、Section
（Personnel Block）を切り出す。

Section境界判定はページ境界を単位とする（1ページ=1Section候補）。実際の
発令PDFにおける複数ページにまたがるSectionの結合判定（同一見出しの継続等）
は、様式ごとの構造情報（`LayoutDefinition`）を要する可能性が高く、現時点の
`LayoutArtifact`が持つ情報のみでは信頼できる判定ができないため、Task6時点の
意図的な最小実装としてページ単位の判定に留める（将来の拡張点、Review Report
のTODO参照）。
"""

from dataclasses import dataclass

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    LayoutArtifact,
    LayoutArtifactPage,
    PersonnelSection,
    SectionCandidate,
    SectionEvidence,
    SectionParseResult,
)
from mod_personnel_db.models.values import ModelValidationError
from mod_personnel_db.pipeline import PipelineContext
from mod_personnel_db.sections.exceptions import SectionParserError

DEFAULT_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True, slots=True)
class _SplitLines:
    """1ページ分のHeader/Body/Footer判定結果（Personnel Block抽出の中間表現）。"""

    header: str | None
    body: tuple[str, ...]
    footer: str | None


class SectionParser:
    """`PipelineStage[LayoutArtifact, SectionParseResult]`を実装する。公開APIは`run()`のみ。"""

    def __init__(self, *, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        self._confidence_threshold = confidence_threshold

    def run(self, context: PipelineContext, artifact: LayoutArtifact) -> SectionParseResult:
        del context
        candidates = tuple(_evaluate_page(page) for page in artifact.pages)
        sections = _build_sections(artifact, candidates, self._confidence_threshold)
        return SectionParseResult(
            sections=sections, candidates=candidates, confidence=_overall_confidence(candidates)
        )


def _lines(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _split_header_body_footer(lines: tuple[str, ...]) -> _SplitLines:
    if not lines:
        return _SplitLines(header=None, body=(), footer=None)
    if len(lines) == 1:
        return _SplitLines(header=lines[0], body=(), footer=lines[0])
    return _SplitLines(header=lines[0], body=lines[1:-1], footer=lines[-1])


def _evaluate_page(page: LayoutArtifactPage) -> SectionCandidate:
    split = _split_header_body_footer(_lines(page.text))
    evidence = SectionEvidence(
        header_line=split.header,
        footer_line=split.footer,
        body_line_count=len(split.body),
        page_range=(page.index, page.index),
    )
    return SectionCandidate(section_index=page.index, score=_score(split), evidence=evidence)


def _score(split: _SplitLines) -> float:
    # split.body が非空になるのは split.header も非空の場合のみ
    # （_split_header_body_footer: 行が2行以上ある場合のみbodyが生じ、
    # その場合headerは必ずlines[0]として設定される）。
    if split.header is None:
        return 0.0
    return 1.0 if len(split.body) > 0 else 0.3


def _build_sections(
    artifact: LayoutArtifact, candidates: tuple[SectionCandidate, ...], threshold: float
) -> tuple[PersonnelSection, ...]:
    layout_id = artifact.detection.layout_id
    if layout_id is None:
        return ()
    sections: list[PersonnelSection] = []
    for page, candidate in zip(artifact.pages, candidates, strict=True):
        if candidate.score < threshold:
            continue
        lines = _lines(page.text)
        if not lines:
            continue
        sections.append(_to_personnel_section(artifact, layout_id, candidate, lines))
    return tuple(sections)


def _to_personnel_section(
    artifact: LayoutArtifact, layout_id: str, candidate: SectionCandidate, lines: tuple[str, ...]
) -> PersonnelSection:
    try:
        return PersonnelSection(
            document_ref=artifact.source_pdf_id,
            layout_id=layout_id,
            section_index=candidate.section_index,
            section_label=candidate.evidence.header_line,
            page_range=candidate.evidence.page_range,
            section_text="\n".join(lines),
        )
    except ModelValidationError as exc:
        raise SectionParserError(
            f"failed to construct PersonnelSection for section_index={candidate.section_index}"
        ) from exc


def _overall_confidence(candidates: tuple[SectionCandidate, ...]) -> Confidence:
    if not candidates:
        return Confidence(score=0.0, band=ConfidenceBand.LOW)
    average = sum(candidate.score for candidate in candidates) / len(candidates)
    return Confidence(score=average, band=_confidence_band(average))


def _confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.9:
        return ConfidenceBand.VERIFIED
    if score >= 0.75:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW
