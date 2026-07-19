import pytest

from mod_personnel_db.extractors import FieldExtractor
from mod_personnel_db.pipeline.context import PipelineContext

from .conftest import make_section

# --- 正常系: 列認識・RawRecord生成 ---


def test_extractor_splits_multi_column_line_into_raw_fields(context: PipelineContext) -> None:
    section = make_section("山田太郎  陸将補  第1師団")
    result = FieldExtractor().run(context, section)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.raw_fields == {
        "column_1": "山田太郎",
        "column_2": "陸将補",
        "column_3": "第1師団",
    }
    assert record.section_ref is None
    assert record.record_index == 0


def test_extractor_preserves_pdf_values_verbatim(context: PipelineContext) -> None:
    # 行頭・行末の空白はSection Parser由来の行単位ストリップと同様に除去されるが、
    # 値の内部にある全角スペースはそのまま保持される（PDFに書かれていた値のまま）。
    section = make_section("　山田　太郎　  陸将補")
    result = FieldExtractor().run(context, section)

    assert result.records[0].raw_fields["column_1"] == "山田　太郎"


def test_extractor_evidence_reports_line_and_column_count(context: PipelineContext) -> None:
    section = make_section("山田太郎  陸将補")
    result = FieldExtractor().run(context, section)

    evidence = result.candidates[0].evidence
    assert evidence.line == "山田太郎  陸将補"
    assert evidence.column_count == 2


# --- 複数行 ---


def test_extractor_each_line_becomes_its_own_record(context: PipelineContext) -> None:
    section = make_section("山田太郎  陸将補\n鈴木花子  海将補")
    result = FieldExtractor().run(context, section)

    assert len(result.records) == 2
    assert [record.record_index for record in result.records] == [0, 1]
    assert result.records[1].raw_fields["column_1"] == "鈴木花子"


# --- 低Confidence ---


def test_extractor_single_column_line_below_default_threshold_excluded(
    context: PipelineContext,
) -> None:
    section = make_section("単一列のみの行")
    result = FieldExtractor().run(context, section)

    assert result.records == ()
    assert len(result.candidates) == 1
    assert result.candidates[0].score == pytest.approx(0.4)


def test_extractor_custom_confidence_threshold_is_respected(context: PipelineContext) -> None:
    section = make_section("単一列のみの行")
    extractor = FieldExtractor(confidence_threshold=0.3)

    result = extractor.run(context, section)

    assert len(result.records) == 1


# --- 空Section・Confidence算出 ---


def test_extractor_evaluates_only_non_blank_lines(context: PipelineContext) -> None:
    section = make_section("山田太郎  陸将補\n\n   \n")
    result = FieldExtractor().run(context, section)

    assert len(result.candidates) == 1


def test_extractor_overall_confidence_is_average_of_candidate_scores(
    context: PipelineContext,
) -> None:
    section = make_section("山田太郎  陸将補\n鈴木花子  海将補")
    result = FieldExtractor().run(context, section)

    assert result.confidence.score == 1.0
    assert result.confidence.band.value == "verified"


def test_extractor_confidence_band_medium_for_half_scoring_lines(context: PipelineContext) -> None:
    section = make_section("山田太郎  陸将補\n単一列")
    result = FieldExtractor().run(context, section)

    assert result.confidence.score == pytest.approx(0.7)
    assert result.confidence.band.value == "medium"


def test_extractor_confidence_band_high_for_mostly_high_scoring_lines(
    context: PipelineContext,
) -> None:
    section = make_section("A  B\nC  D\nE  F\n単一列")
    result = FieldExtractor().run(context, section)

    assert result.confidence.score == pytest.approx(0.85)
    assert result.confidence.band.value == "high"


def test_extractor_whitespace_only_section_text_produces_empty_result(
    context: PipelineContext,
) -> None:
    # PersonnelSection.section_textは空文字列のみ拒否するため、空白のみの文字列は
    # 構築可能だが、Field Extractorの評価対象行は0件になる。
    section = make_section("   \n  \n")
    result = FieldExtractor().run(context, section)

    assert result.records == ()
    assert result.candidates == ()
    assert result.confidence.score == 0.0
    assert result.confidence.band.value == "low"
