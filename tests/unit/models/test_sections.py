import pytest

from mod_personnel_db.models import (
    ConfidenceBand,
    PdfId,
    PersonnelSection,
    SectionCandidate,
    SectionEvidence,
    SectionParseResult,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


def _evidence(*, body_line_count: int = 1, page_range: tuple[int, int] = (0, 0)) -> SectionEvidence:
    return SectionEvidence(
        header_line="header",
        footer_line="footer",
        body_line_count=body_line_count,
        page_range=page_range,
    )


def _section(*, layout_id: str = "format_a") -> PersonnelSection:
    return PersonnelSection(
        document_ref=PdfId(1),
        layout_id=layout_id,
        section_index=0,
        section_label="header",
        page_range=(0, 0),
        section_text="発令一覧",
    )


def test_personnel_section_layout_id_accepts_era_id_string() -> None:
    section = _section(layout_id="reiwa")
    assert section.layout_id == "reiwa"


def test_section_evidence_normal_construction() -> None:
    evidence = _evidence()
    assert evidence.body_line_count == 1


def test_section_evidence_rejects_negative_body_line_count() -> None:
    with pytest.raises(ModelValidationError):
        _evidence(body_line_count=-1)


def test_section_evidence_rejects_invalid_page_range() -> None:
    with pytest.raises(ModelValidationError):
        _evidence(page_range=(2, 1))


def test_section_candidate_normal_construction() -> None:
    candidate = SectionCandidate(section_index=0, score=0.8, evidence=_evidence())
    assert candidate.score == 0.8


def test_section_candidate_rejects_negative_section_index() -> None:
    with pytest.raises(ModelValidationError):
        SectionCandidate(section_index=-1, score=0.5, evidence=_evidence())


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_section_candidate_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ModelValidationError):
        SectionCandidate(section_index=0, score=score, evidence=_evidence())


def test_section_parse_result_normal_construction() -> None:
    candidate = SectionCandidate(section_index=0, score=1.0, evidence=_evidence())
    result = SectionParseResult(
        sections=(_section(),),
        candidates=(candidate,),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    )
    assert len(result.sections) == 1


def test_section_parse_result_allows_empty_sections() -> None:
    result = SectionParseResult(
        sections=(), candidates=(), confidence=Confidence(score=0.0, band=ConfidenceBand.LOW)
    )
    assert result.sections == ()
