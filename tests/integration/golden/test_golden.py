"""Golden Test（ADR-0007）の自動実行。

`tests/golden/sample_pdfs/`の各PDFを、`layouts/`・`knowledge/`の実データを
用いて中核パイプライン（Document Analyzer → Layout Detector → Section
Parser → Field Extractor → Normalizer → Validator）へ実際に入力し、
`tests/golden/sample_outputs/`の期待JSONと全体一致することを確認する。

Composition Root（`cli/bootstrap.py`）は経由しない。各段階の公開API
（`DocumentAnalyzer`/`LayoutDetector`/`SectionParser`/`FieldExtractor`/
`Normalizer`/`Validator`の各クラスと`run()`、`layout.definitions.
load_layout_definitions`、`knowledge.service.FileKnowledgeService`の
各公開API）のみを直接呼び出す。`repositories/sqlite/`・`JobRunner`は
使用しない。
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from mod_personnel_db.document.analyzer import DocumentAnalyzer
from mod_personnel_db.extractors.extractor import FieldExtractor
from mod_personnel_db.knowledge.service import FileKnowledgeService
from mod_personnel_db.layout.definitions import load_layout_definitions
from mod_personnel_db.layout.detector import LayoutDetector
from mod_personnel_db.models import (
    JobId,
    KnowledgeSnapshot,
    LayoutArtifact,
    LayoutDefinition,
    ParserVersionId,
    PdfId,
    PdfRecord,
    PersonnelSection,
    RawRecord,
    ValidationRuleSet,
)
from mod_personnel_db.normalizers.normalizer import Normalizer
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.sections.parser import SectionParser
from mod_personnel_db.validators.rule_engine import RuleEngine
from mod_personnel_db.validators.validator import Validator

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAYOUTS_ROOT = _REPO_ROOT / "layouts"
_KNOWLEDGE_ROOT = _REPO_ROOT / "knowledge"
_SAMPLE_PDFS_DIR = _REPO_ROOT / "tests" / "golden" / "sample_pdfs"
_SAMPLE_OUTPUTS_DIR = _REPO_ROOT / "tests" / "golden" / "sample_outputs"
_AS_OF = date(2026, 7, 1)


def _sample_pdf_paths() -> list[Path]:
    return sorted(_SAMPLE_PDFS_DIR.glob("*.pdf"))


def _expected_output_path(pdf_path: Path) -> Path:
    return _SAMPLE_OUTPUTS_DIR / f"{pdf_path.stem}.json"


def _build_pdf_record(pdf_path: Path) -> PdfRecord:
    return PdfRecord(
        id=PdfId(1),
        content_hash="0" * 64,
        source_url="https://example.mod.go.jp/golden-test-fixture.pdf",
        published_date=_AS_OF,
        fetched_at=datetime.now(UTC),
        file_path=str(pdf_path),
        file_size_bytes=pdf_path.stat().st_size,
        status="fetched",
    )


def _build_context() -> PipelineContext:
    return PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="golden-test",
        started_at=datetime.now(UTC),
    )


def _serialize_layout_detection(artifact: LayoutArtifact) -> dict[str, Any]:
    detection = artifact.detection
    return {
        "layout_id": detection.layout_id,
        "layout_version": detection.layout_version,
        "confidence": {
            "score": detection.confidence.score,
            "band": str(detection.confidence.band),
        },
        "warnings": [str(warning) for warning in detection.warnings],
    }


def _serialize_record(
    raw_record: RawRecord,
    snapshot: KnowledgeSnapshot,
    validation_rules: ValidationRuleSet,
) -> dict[str, Any]:
    context = _build_context()
    norm_result = Normalizer(snapshot).run(context, raw_record)
    if not norm_result.records:
        return {
            "record_index": raw_record.record_index,
            "raw_fields": dict(raw_record.raw_fields),
            "normalized_fields": {},
            "normalization_confidence": {
                "score": norm_result.confidence.score,
                "band": str(norm_result.confidence.band),
            },
            "validation_status": "skipped_below_normalization_threshold",
            "validation_error_count": 0,
            "validation_warning_count": 0,
            "validation_warnings": [],
        }
    normalized = norm_result.records[0]
    validator = Validator(rules=validation_rules, knowledge=snapshot, engine=RuleEngine())
    validation_result = validator.run(context, normalized)
    candidate = validation_result.candidates[0]
    return {
        "record_index": raw_record.record_index,
        "raw_fields": dict(raw_record.raw_fields),
        "normalized_fields": {
            name: {"value": value.value, "raw": value.raw}
            for name, value in normalized.normalized_fields.items()
        },
        "normalization_confidence": {
            "score": norm_result.confidence.score,
            "band": str(norm_result.confidence.band),
        },
        "validation_status": validation_result.status,
        "validation_error_count": len(candidate.errors),
        "validation_warning_count": len(candidate.warnings),
        "validation_warnings": [
            {"rule_id": warning.rule_id, "message": warning.message}
            for warning in candidate.warnings
        ],
    }


def _extract_and_serialize_section_records(
    section: PersonnelSection,
    snapshot: KnowledgeSnapshot,
    validation_rules: ValidationRuleSet,
) -> list[dict[str, Any]]:
    context = _build_context()
    extraction_result = FieldExtractor().run(context, section)
    return [
        _serialize_record(raw_record, snapshot, validation_rules)
        for raw_record in extraction_result.records
    ]


def _load_layout_definitions() -> tuple[LayoutDefinition, ...]:
    return load_layout_definitions(_LAYOUTS_ROOT)


def _run_pipeline(pdf_path: Path) -> dict[str, Any]:
    """`pdf_path`を中核パイプラインへ実際に入力し、Golden比較用のdictを返す。"""
    context = _build_context()
    layout_definitions = _load_layout_definitions()
    knowledge_service = FileKnowledgeService(_KNOWLEDGE_ROOT)
    snapshot = knowledge_service.load_snapshot(as_of=_AS_OF)
    validation_rules = knowledge_service.load_validation_rules(as_of=_AS_OF)

    document = DocumentAnalyzer().run(context, _build_pdf_record(pdf_path))
    assert document.analysis.statistics.page_count > 0, "PDFが実際に読み込まれていない"

    artifact = LayoutDetector(layout_definitions=layout_definitions).run(context, document)
    section_result = SectionParser().run(context, artifact)

    records: list[dict[str, Any]] = []
    for section in section_result.sections:
        records.extend(_extract_and_serialize_section_records(section, snapshot, validation_rules))

    return {
        "source_pdf": pdf_path.name,
        "layout_detection": _serialize_layout_detection(artifact),
        "section_count": len(section_result.sections),
        "records": records,
    }


def _without_comment_keys(data: dict[str, Any]) -> dict[str, Any]:
    """`$`で始まるキー（`$comment`等、ドキュメント用のメタデータ）を比較対象から除く。"""
    return {key: value for key, value in data.items() if not key.startswith("$")}


def _load_expected(pdf_path: Path) -> dict[str, Any]:
    expected_path = _expected_output_path(pdf_path)
    assert expected_path.is_file(), f"期待結果が見つからない: {expected_path}"
    raw: dict[str, Any] = json.loads(expected_path.read_text(encoding="utf-8"))
    return _without_comment_keys(raw)


def test_sample_pdfs_directory_is_not_empty() -> None:
    assert _sample_pdf_paths(), "tests/golden/sample_pdfs/にPDFが存在しない"


@pytest.mark.parametrize("pdf_path", _sample_pdf_paths(), ids=lambda p: p.stem)
def test_golden_pipeline_output_matches_expected(pdf_path: Path) -> None:
    actual = _run_pipeline(pdf_path)
    expected = _load_expected(pdf_path)
    assert actual == expected
