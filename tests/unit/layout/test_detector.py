from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PageObject
from pypdf.errors import PdfReadError

from mod_personnel_db.layout import LayoutDetector, LayoutDetectorError
from mod_personnel_db.models import (
    Document,
    LayoutDefinition,
    LayoutRule,
    LayoutRuleKind,
    LayoutWarning,
)
from mod_personnel_db.pipeline.context import PipelineContext

from ._layout_fixtures import format_a_definition, format_b_definition
from ._pdf_fixtures import (
    blank_pdf_bytes,
    broken_pdf_bytes,
    rotated_text_pdf_bytes,
    text_pdf_bytes,
)

# --- 正常系 ---


def test_detector_matches_known_layout(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=(format_a_definition(),))

    result = detector.run(context, document)

    assert result.detection.layout_id == "format_a"
    assert result.detection.layout_version == 1
    assert result.detection.confidence.score == pytest.approx(1.0)
    assert LayoutWarning.NO_MATCH not in result.detection.warnings


# --- 未知Layout ---


def test_detector_no_definitions_produces_no_match(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.detection.layout_id is None
    assert result.detection.layout_version is None
    assert result.detection.candidate_layouts == ()
    assert LayoutWarning.NO_MATCH in result.detection.warnings


def test_detector_unmatched_layout_produces_no_match_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("blank.pdf", blank_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=(format_b_definition(),))

    result = detector.run(context, document)

    assert result.detection.layout_id is None
    assert LayoutWarning.NO_MATCH in result.detection.warnings
    assert len(result.detection.candidate_layouts) == 1


# --- Confidence境界 ---


def test_detector_score_just_below_threshold_is_low_confidence_not_no_match(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("blank.pdf", blank_pdf_bytes())
    document = make_document(path)
    # min_pagesルール(weight=0.3)のみ満たし、headerルール(weight=0.7)は満たさない
    # -> score=0.3。デフォルトのlow_confidence_threshold(0.3)以上、
    # confidence_threshold(0.6)未満のためLOW_CONFIDENCEになる境界。
    detector = LayoutDetector(layout_definitions=(format_a_definition(),))

    result = detector.run(context, document)

    assert result.detection.layout_id is None
    assert result.detection.confidence.score == pytest.approx(0.3)
    assert LayoutWarning.LOW_CONFIDENCE in result.detection.warnings
    assert LayoutWarning.NO_MATCH not in result.detection.warnings


def test_detector_score_below_low_confidence_threshold_is_no_match(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("blank.pdf", blank_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(
        layout_definitions=(format_a_definition(),), low_confidence_threshold=0.5
    )

    result = detector.run(context, document)

    assert result.detection.layout_id is None
    assert LayoutWarning.NO_MATCH in result.detection.warnings
    assert LayoutWarning.LOW_CONFIDENCE not in result.detection.warnings


def test_detector_custom_confidence_threshold_is_respected(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("blank.pdf", blank_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=(format_a_definition(),), confidence_threshold=0.2)

    result = detector.run(context, document)

    assert result.detection.layout_id == "format_a"


# --- 複数候補 ---


def test_detector_returns_all_candidates_sorted_by_score(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=(format_b_definition(), format_a_definition()))

    result = detector.run(context, document)

    assert [candidate.layout_id for candidate in result.detection.candidate_layouts] == [
        "format_a",
        "format_b",
    ]
    candidates = result.detection.candidate_layouts
    assert candidates[0].score >= candidates[1].score


def test_detector_ambiguous_candidates_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    twin_a = format_a_definition(era_id="format_a")
    twin_b = format_a_definition(era_id="format_a_twin")
    detector = LayoutDetector(layout_definitions=(twin_a, twin_b))

    result = detector.run(context, document)

    assert LayoutWarning.AMBIGUOUS_CANDIDATES in result.detection.warnings


# --- Evidence生成 ---


def test_detector_evidence_reflects_page_and_font_statistics(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes(page_count=3))
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.detection.evidence.page_statistics.page_count == 3
    assert result.detection.evidence.page_statistics.average_char_count > 0
    assert "Helvetica" in result.detection.evidence.font_statistics
    assert result.detection.evidence.header_signature == "MOD PERSONNEL ORDER FORMAT A"
    assert result.detection.evidence.footer_signature == "END OF DOCUMENT"
    assert result.detection.evidence.bbox_statistics.average_width == pytest.approx(210.0)
    assert result.detection.evidence.bbox_statistics.average_height == pytest.approx(297.0)


def test_detector_evidence_rotation_statistics(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("rotated.pdf", rotated_text_pdf_bytes(rotation=90))
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.detection.evidence.rotation_statistics.rotated_page_count == 1
    assert result.detection.evidence.rotation_statistics.dominant_rotation == 90


def test_detector_evidence_on_empty_pdf_has_zero_statistics(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("empty.pdf", blank_pdf_bytes(page_count=0))
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.detection.evidence.page_statistics.page_count == 0
    assert result.detection.evidence.header_signature is None
    assert result.detection.evidence.footer_signature is None


# --- LayoutArtifact生成（ADR-0037） ---


def test_detector_artifact_carries_source_pdf_id(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.source_pdf_id == document.source_pdf_id


def test_detector_artifact_pages_carry_extracted_text(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes(page_count=3))
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert [page.index for page in result.pages] == [0, 1, 2]
    assert "MOD PERSONNEL ORDER FORMAT A" in result.pages[0].text
    assert "END OF DOCUMENT" in result.pages[0].text


def test_detector_artifact_pages_empty_for_empty_pdf(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("empty.pdf", blank_pdf_bytes(page_count=0))
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.pages == ()


# --- PDF再読込 ---


def test_detector_rereads_pdf_independently_of_document_analysis(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes(page_count=5))
    document = make_document(path)
    # conftest.pyのmake_documentはpage_count=1のDocumentAnalysisResultを合成するが、
    # Layout Detectorはdocument.analysisを一切参照せずdocument.file_pathを再読込する。
    assert document.analysis.statistics.page_count == 1
    detector = LayoutDetector(layout_definitions=())

    result = detector.run(context, document)

    assert result.detection.evidence.page_statistics.page_count == 5


def test_detector_rejects_missing_file(
    context: PipelineContext,
    tmp_path: Path,
    make_document: Callable[[Path], Document],
) -> None:
    missing = tmp_path / "does-not-exist.pdf"
    document = make_document(missing)
    detector = LayoutDetector(layout_definitions=())

    with pytest.raises(LayoutDetectorError):
        detector.run(context, document)


# --- 例外変換 ---


def test_detector_wraps_broken_pdf_as_layout_detector_error(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("broken.pdf", broken_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    with pytest.raises(LayoutDetectorError):
        detector.run(context, document)


def test_detector_wraps_pypdf_extract_text_error(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    with patch.object(PageObject, "extract_text", side_effect=PdfReadError("simulated")):
        result = detector.run(context, document)

    assert result.detection.evidence.header_signature is None


def test_detector_wraps_unicode_error_on_extract_text(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    detector = LayoutDetector(layout_definitions=())

    with patch.object(
        PageObject, "extract_text", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "boom")
    ):
        result = detector.run(context, document)

    assert result.detection.evidence.header_signature is None


# --- ルール種別ごとの評価 ---


def test_detector_footer_pattern_rule_matches(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    definition = LayoutDefinition(
        era_id="footer_only",
        version=1,
        rules=(
            LayoutRule(
                rule_id="footer",
                kind=LayoutRuleKind.FOOTER_PATTERN,
                value="END OF DOCUMENT",
                weight=1.0,
            ),
        ),
    )
    detector = LayoutDetector(layout_definitions=(definition,))

    result = detector.run(context, document)

    assert result.detection.layout_id == "footer_only"


def test_detector_font_name_contains_rule_matches(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes(font_name="Helvetica"))
    document = make_document(path)
    definition = LayoutDefinition(
        era_id="font_only",
        version=1,
        rules=(
            LayoutRule(
                rule_id="font",
                kind=LayoutRuleKind.FONT_NAME_CONTAINS,
                value="Helvetica",
                weight=1.0,
            ),
        ),
    )
    detector = LayoutDetector(layout_definitions=(definition,))

    result = detector.run(context, document)

    assert result.detection.layout_id == "font_only"


def test_detector_min_page_count_rule_with_invalid_value_fails_gracefully(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
) -> None:
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    definition = LayoutDefinition(
        era_id="bad_rule",
        version=1,
        rules=(
            LayoutRule(
                rule_id="min_pages",
                kind=LayoutRuleKind.MIN_PAGE_COUNT,
                value="not-a-number",
                weight=1.0,
            ),
        ),
    )
    detector = LayoutDetector(layout_definitions=(definition,))

    result = detector.run(context, document)

    assert result.detection.candidate_layouts[0].score == 0.0
    detail = result.detection.candidate_layouts[0].failed_rules[0].detail
    assert detail == "invalid MIN_PAGE_COUNT value: 'not-a-number'"


# --- Confidence band ---


@pytest.mark.parametrize(
    "case",
    [
        (0.8, 0.2, "high"),
        (0.6, 0.4, "medium"),
    ],
)
def test_detector_confidence_band_reflects_score(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_document: Callable[[Path], Document],
    case: tuple[float, float, str],
) -> None:
    weight_a, weight_b, expected_band = case
    path = write_pdf("format_a.pdf", text_pdf_bytes())
    document = make_document(path)
    definition = LayoutDefinition(
        era_id="partial",
        version=1,
        rules=(
            LayoutRule(
                rule_id="header",
                kind=LayoutRuleKind.HEADER_PATTERN,
                value="MOD PERSONNEL ORDER FORMAT A",
                weight=weight_a,
            ),
            LayoutRule(
                rule_id="footer",
                kind=LayoutRuleKind.FOOTER_PATTERN,
                value="THIS WILL NOT MATCH",
                weight=weight_b,
            ),
        ),
    )
    detector = LayoutDetector(layout_definitions=(definition,), confidence_threshold=0.0)

    result = detector.run(context, document)

    assert result.detection.confidence.band.value == expected_band
