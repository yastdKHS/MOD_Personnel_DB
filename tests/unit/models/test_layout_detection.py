import pytest

from mod_personnel_db.models import (
    BoundingBoxStatistics,
    ConfidenceBand,
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
    PdfId,
    RotationStatistics,
)
from mod_personnel_db.models.values import ModelValidationError

_PAGE_STATS = PageStatistics(page_count=1, average_char_count=10.0)
_BBOX_STATS = BoundingBoxStatistics(average_width=210.0, average_height=297.0)
_ROTATION_STATS = RotationStatistics(rotated_page_count=0, dominant_rotation=0)


def _evidence(*, line_statistics: float = 0.0, block_statistics: float = 0.0) -> LayoutEvidence:
    return LayoutEvidence(
        font_statistics=(),
        page_statistics=_PAGE_STATS,
        bbox_statistics=_BBOX_STATS,
        rotation_statistics=_ROTATION_STATS,
        header_signature=None,
        footer_signature=None,
        line_statistics=line_statistics,
        block_statistics=block_statistics,
    )


def test_layout_match_construction() -> None:
    match = LayoutMatch(rule_id="r1", matched=True, detail="ok")
    assert match.matched is True


def test_layout_candidate_normal_construction() -> None:
    candidate = LayoutCandidate(layout_id="format_a", score=0.8, matched_rules=(), failed_rules=())
    assert candidate.score == 0.8


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_layout_candidate_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ModelValidationError):
        LayoutCandidate(layout_id="format_a", score=score, matched_rules=(), failed_rules=())


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_layout_confidence_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ModelValidationError):
        LayoutConfidence(score=score, band=ConfidenceBand.LOW)


def test_page_statistics_rejects_negative_page_count() -> None:
    with pytest.raises(ModelValidationError):
        PageStatistics(page_count=-1, average_char_count=0.0)


def test_page_statistics_rejects_negative_average_char_count() -> None:
    with pytest.raises(ModelValidationError):
        PageStatistics(page_count=0, average_char_count=-1.0)


def test_bbox_statistics_rejects_negative_dimensions() -> None:
    with pytest.raises(ModelValidationError):
        BoundingBoxStatistics(average_width=-1.0, average_height=1.0)


def test_rotation_statistics_rejects_negative_count() -> None:
    with pytest.raises(ModelValidationError):
        RotationStatistics(rotated_page_count=-1, dominant_rotation=0)


def test_layout_evidence_normal_construction() -> None:
    evidence = _evidence()
    assert evidence.page_statistics.page_count == 1


def test_layout_evidence_rejects_negative_line_statistics() -> None:
    with pytest.raises(ModelValidationError):
        _evidence(line_statistics=-1.0)


def test_layout_evidence_rejects_negative_block_statistics() -> None:
    with pytest.raises(ModelValidationError):
        _evidence(block_statistics=-1.0)


def test_layout_detection_result_matched_layout() -> None:
    result = LayoutDetectionResult(
        layout_id="format_a",
        layout_version=1,
        confidence=LayoutConfidence(score=0.9, band=ConfidenceBand.VERIFIED),
        candidate_layouts=(),
        evidence=_evidence(),
        warnings=(),
    )
    assert result.layout_id == "format_a"


def test_layout_detection_result_unmatched_layout_requires_warning() -> None:
    result = LayoutDetectionResult(
        layout_id=None,
        layout_version=None,
        confidence=LayoutConfidence(score=0.0, band=ConfidenceBand.LOW),
        candidate_layouts=(),
        evidence=_evidence(),
        warnings=(LayoutWarning.NO_MATCH,),
    )
    assert result.layout_id is None


def test_layout_detection_result_rejects_inconsistent_layout_id_and_version() -> None:
    with pytest.raises(ModelValidationError):
        LayoutDetectionResult(
            layout_id="format_a",
            layout_version=None,
            confidence=LayoutConfidence(score=0.9, band=ConfidenceBand.VERIFIED),
            candidate_layouts=(),
            evidence=_evidence(),
            warnings=(),
        )


def test_layout_detection_result_unmatched_layout_without_warning_is_rejected() -> None:
    with pytest.raises(ModelValidationError):
        LayoutDetectionResult(
            layout_id=None,
            layout_version=None,
            confidence=LayoutConfidence(score=0.0, band=ConfidenceBand.LOW),
            candidate_layouts=(),
            evidence=_evidence(),
            warnings=(),
        )


def test_layout_rule_normal_construction() -> None:
    rule = LayoutRule(rule_id="r1", kind=LayoutRuleKind.HEADER_PATTERN, value="x", weight=0.5)
    assert rule.weight == 0.5


def test_layout_rule_rejects_non_positive_weight() -> None:
    with pytest.raises(ModelValidationError):
        LayoutRule(rule_id="r1", kind=LayoutRuleKind.HEADER_PATTERN, value="x", weight=0.0)


def test_layout_definition_normal_construction() -> None:
    rule = LayoutRule(rule_id="r1", kind=LayoutRuleKind.MIN_PAGE_COUNT, value="1", weight=1.0)
    definition = LayoutDefinition(era_id="format_a", version=1, rules=(rule,))
    assert definition.era_id == "format_a"


def test_layout_definition_rejects_empty_rules() -> None:
    with pytest.raises(ModelValidationError):
        LayoutDefinition(era_id="format_a", version=1, rules=())


def test_layout_definition_rejects_duplicate_rule_ids() -> None:
    rule = LayoutRule(rule_id="r1", kind=LayoutRuleKind.MIN_PAGE_COUNT, value="1", weight=1.0)
    with pytest.raises(ModelValidationError):
        LayoutDefinition(era_id="format_a", version=1, rules=(rule, rule))


@pytest.mark.parametrize("warning", list(LayoutWarning))
def test_layout_warning_enum_members(warning: LayoutWarning) -> None:
    assert isinstance(warning.value, str)


@pytest.mark.parametrize("kind", list(LayoutRuleKind))
def test_layout_rule_kind_enum_members(kind: LayoutRuleKind) -> None:
    assert isinstance(kind.value, str)


def _detection(
    *, layout_id: str | None = None, layout_version: int | None = None
) -> LayoutDetectionResult:
    warnings = () if layout_id is not None else (LayoutWarning.NO_MATCH,)
    return LayoutDetectionResult(
        layout_id=layout_id,
        layout_version=layout_version,
        confidence=LayoutConfidence(score=0.0, band=ConfidenceBand.LOW),
        candidate_layouts=(),
        evidence=_evidence(),
        warnings=warnings,
    )


def test_layout_artifact_page_normal_construction() -> None:
    page = LayoutArtifactPage(index=0, text="hello")
    assert page.text == "hello"


def test_layout_artifact_page_rejects_negative_index() -> None:
    with pytest.raises(ModelValidationError):
        LayoutArtifactPage(index=-1, text="")


def test_layout_artifact_normal_construction() -> None:
    artifact = LayoutArtifact(
        source_pdf_id=PdfId(1),
        detection=_detection(),
        pages=(LayoutArtifactPage(index=0, text="a"), LayoutArtifactPage(index=1, text="b")),
    )
    assert artifact.detection.layout_id is None
    assert [page.index for page in artifact.pages] == [0, 1]


def test_layout_artifact_allows_empty_pages() -> None:
    artifact = LayoutArtifact(source_pdf_id=PdfId(1), detection=_detection(), pages=())
    assert artifact.pages == ()


def test_layout_artifact_rejects_non_contiguous_page_indices() -> None:
    with pytest.raises(ModelValidationError):
        LayoutArtifact(
            source_pdf_id=PdfId(1),
            detection=_detection(),
            pages=(LayoutArtifactPage(index=0, text="a"), LayoutArtifactPage(index=2, text="b")),
        )
