import pytest

from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.sections import SectionParser

from .conftest import make_artifact

# --- 正常系: Header/Body/Footer判定・Personnel Block抽出 ---


def test_parser_single_section_from_one_page(context: PipelineContext) -> None:
    artifact = make_artifact(("見出し\n山田太郎 陸将補\n以上",))
    result = SectionParser().run(context, artifact)

    assert len(result.sections) == 1
    section = result.sections[0]
    assert section.section_label == "見出し"
    assert section.layout_id == "format_a"
    assert section.page_range == (0, 0)
    assert "山田太郎" in section.section_text


def test_parser_evidence_reports_header_body_footer(context: PipelineContext) -> None:
    artifact = make_artifact(("見出し\n山田太郎 陸将補\n以上",))
    result = SectionParser().run(context, artifact)

    evidence = result.candidates[0].evidence
    assert evidence.header_line == "見出し"
    assert evidence.footer_line == "以上"
    assert evidence.body_line_count == 1


# --- Section境界判定: ページ境界を単位とする ---


def test_parser_each_page_becomes_its_own_section(context: PipelineContext) -> None:
    artifact = make_artifact(
        ("見出しA\n本文A\n以上A", "見出しB\n本文B\n以上B"),
    )
    result = SectionParser().run(context, artifact)

    assert len(result.sections) == 2
    assert [section.section_label for section in result.sections] == ["見出しA", "見出しB"]
    assert [section.page_range for section in result.sections] == [(0, 0), (1, 1)]


def test_parser_section_index_matches_page_index(context: PipelineContext) -> None:
    artifact = make_artifact(("A見出し\n本文A\nA以上", "B見出し\n本文B\nB以上"))
    result = SectionParser().run(context, artifact)

    assert [section.section_index for section in result.sections] == [0, 1]


def test_parser_repeated_header_still_yields_separate_page_sections(
    context: PipelineContext,
) -> None:
    # 同一見出しが複数ページに現れても、ページ境界単位でSectionを分ける
    # （Task6時点の意図的な最小実装、docstring/Review Report参照）。
    artifact = make_artifact(("見出し\n本文1\n以上", "見出し\n本文2\n以上"))
    result = SectionParser().run(context, artifact)

    assert len(result.sections) == 2
    assert [section.page_range for section in result.sections] == [(0, 0), (1, 1)]


# --- 低Confidence・未一致Layout ---


def test_parser_unmatched_layout_produces_no_sections(context: PipelineContext) -> None:
    artifact = make_artifact(("見出し\n本文\n以上",), layout_id=None, layout_version=None)
    result = SectionParser().run(context, artifact)

    assert result.sections == ()
    assert len(result.candidates) == 1
    assert result.candidates[0].score > 0.0


def test_parser_low_score_page_below_threshold_is_excluded(context: PipelineContext) -> None:
    artifact = make_artifact(("たった1行だけ",))
    parser = SectionParser(confidence_threshold=0.9)

    result = parser.run(context, artifact)

    assert result.sections == ()
    assert len(result.candidates) == 1


def test_parser_custom_confidence_threshold_is_respected(context: PipelineContext) -> None:
    artifact = make_artifact(("たった1行だけ",))
    parser = SectionParser(confidence_threshold=0.2)

    result = parser.run(context, artifact)

    assert len(result.sections) == 1


# --- 空Artifact ---


def test_parser_empty_artifact_returns_empty_result(context: PipelineContext) -> None:
    artifact = make_artifact(())
    result = SectionParser().run(context, artifact)

    assert result.sections == ()
    assert result.candidates == ()
    assert result.confidence.score == 0.0


def test_parser_blank_page_produces_zero_score_candidate(context: PipelineContext) -> None:
    artifact = make_artifact(("   \n\n  ",))
    result = SectionParser().run(context, artifact)

    assert result.sections == ()
    assert len(result.candidates) == 1
    assert result.candidates[0].score == 0.0


def test_parser_blank_page_excluded_even_with_zero_threshold(context: PipelineContext) -> None:
    # threshold=0.0だとcandidate.score(0.0) < threshold は偽になるが、
    # 空ページ（lines無し）はSectionとして構築されない。
    artifact = make_artifact(("   \n\n  ",))
    parser = SectionParser(confidence_threshold=0.0)

    result = parser.run(context, artifact)

    assert result.sections == ()
    assert len(result.candidates) == 1


# --- Confidence算出 ---


def test_parser_overall_confidence_is_average_of_candidate_scores(context: PipelineContext) -> None:
    artifact = make_artifact(("見出しA\n本文A\n以上A", "見出しB\n本文B\n以上B"))
    result = SectionParser().run(context, artifact)

    assert result.confidence.score == 1.0
    assert result.confidence.band.value == "verified"


def test_parser_confidence_band_high_for_mostly_high_scoring_pages(
    context: PipelineContext,
) -> None:
    # 1.0(見出し+本文) が3ページ、0.0(空白) が1ページ -> 平均0.75 -> high。
    artifact = make_artifact(
        ("見出しA\n本文A\n以上A", "見出しB\n本文B\n以上B", "見出しC\n本文C\n以上C", "   ")
    )
    result = SectionParser().run(context, artifact)

    assert result.confidence.score == pytest.approx(0.75)
    assert result.confidence.band.value == "high"


def test_parser_confidence_band_medium_for_half_scoring_pages(context: PipelineContext) -> None:
    # 1.0(見出し+本文) が1ページ、0.0(空白) が1ページ -> 平均0.5 -> medium。
    artifact = make_artifact(("見出しA\n本文A\n以上A", "   "))
    result = SectionParser().run(context, artifact)

    assert result.confidence.score == pytest.approx(0.5)
    assert result.confidence.band.value == "medium"
