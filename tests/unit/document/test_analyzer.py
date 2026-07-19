import hashlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PageObject
from pypdf.errors import PdfReadError

from mod_personnel_db.document import DocumentAnalyzer, DocumentAnalyzerError
from mod_personnel_db.models import DocumentWarning, PdfRecord
from mod_personnel_db.pipeline.context import PipelineContext

from ._pdf_fixtures import (
    broken_pdf_bytes,
    empty_pdf_bytes,
    encrypted_pdf_bytes,
    normal_pdf_bytes,
    rotated_pdf_bytes,
)


def test_analyzer_normal_pdf_produces_document_identity(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes(page_count=3))
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.source_pdf_id == record.id
    assert document.analyzer_version
    assert document.analysis.statistics.page_count == 3
    assert document.analysis.warnings == (DocumentWarning.IMAGE_ONLY,)
    assert document.analysis.metadata.filename == "normal.pdf"
    assert len(document.analysis.metadata.sha256) == 64


def test_analyzer_document_id_differs_across_runs(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes())
    record = make_pdf_record(path)
    analyzer = DocumentAnalyzer()

    first = analyzer.run(context, record)
    second = analyzer.run(context, record)

    assert first.id != second.id


def test_analyzer_metadata_sha256_matches_file_content(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    content = normal_pdf_bytes()
    path = write_pdf("normal.pdf", content)
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.metadata.sha256 == hashlib.sha256(content).hexdigest()
    assert document.analysis.metadata.file_size == len(content)


def test_analyzer_rejects_missing_file(
    context: PipelineContext,
    make_pdf_record: Callable[[Path], PdfRecord],
    tmp_path: Path,
) -> None:
    missing = tmp_path / "does-not-exist.pdf"
    record = make_pdf_record(missing)

    with pytest.raises(DocumentAnalyzerError):
        DocumentAnalyzer().run(context, record)


def test_analyzer_rejects_record_without_id(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes())
    record = replace(make_pdf_record(path), id=None)

    with pytest.raises(DocumentAnalyzerError):
        DocumentAnalyzer().run(context, record)


# --- 異常系: 空PDF ---


def test_analyzer_empty_pdf_has_zero_pages_and_no_crash(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("empty.pdf", empty_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.statistics.page_count == 0
    assert DocumentWarning.BROKEN_PDF not in document.analysis.warnings
    assert DocumentWarning.IMAGE_ONLY not in document.analysis.warnings


# --- 異常系: 破損PDF ---


def test_analyzer_broken_pdf_produces_warning_not_exception(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("broken.pdf", broken_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert DocumentWarning.BROKEN_PDF in document.analysis.warnings
    assert document.analysis.statistics.page_count == 0
    assert document.analysis.statistics.text_length is None


def test_analyzer_broken_pdf_yields_low_confidence(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("broken.pdf", broken_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.confidence.score == 0.0


# --- 異常系: 暗号化PDF ---


def test_analyzer_encrypted_pdf_sets_encrypted_metadata_and_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("encrypted.pdf", encrypted_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.metadata.encrypted is True
    assert DocumentWarning.ENCRYPTED in document.analysis.warnings


def test_analyzer_encrypted_pdf_does_not_raise(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("encrypted.pdf", encrypted_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.statistics.text_length is None


# --- 異常系: 画像PDF（テキスト抽出不可） ---


def test_analyzer_textless_pdf_produces_image_only_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("image_only.pdf", normal_pdf_bytes(page_count=1))
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert DocumentWarning.IMAGE_ONLY in document.analysis.warnings
    assert document.analysis.statistics.text_length == 0


# --- 異常系: 巨大PDF ---


def test_analyzer_large_pdf_produces_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    content = normal_pdf_bytes()
    path = write_pdf("large.pdf", content)
    record = make_pdf_record(path)
    analyzer = DocumentAnalyzer(large_pdf_threshold_bytes=1)

    document = analyzer.run(context, record)

    assert DocumentWarning.LARGE_PDF in document.analysis.warnings


def test_analyzer_default_threshold_does_not_flag_small_pdf(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert DocumentWarning.LARGE_PDF not in document.analysis.warnings


# --- Warning生成: 回転 ---


def test_analyzer_rotated_page_is_counted_in_statistics(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("rotated.pdf", rotated_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.statistics.rotation_count == 1


# --- Warning生成: 未対応バージョン ---


def test_analyzer_unrecognized_pdf_version_produces_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    content = normal_pdf_bytes().replace(b"%PDF-1.3", b"%PDF-9.9")
    path = write_pdf("weird_version.pdf", content)
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert DocumentWarning.UNSUPPORTED_VERSION in document.analysis.warnings
    assert document.analysis.metadata.pdf_version == "9.9"


# --- 境界値 ---


def test_analyzer_analysis_time_ms_is_non_negative(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes())
    record = make_pdf_record(path)

    document = DocumentAnalyzer().run(context, record)

    assert document.analysis.statistics.analysis_time_ms >= 0.0


# --- 異常系: I/O・エンコーディング（ライブラリ固有例外の隔離を検証） ---


def test_analyzer_wraps_os_error_on_read(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes())
    record = make_pdf_record(path)

    with (
        patch("pathlib.Path.read_bytes", side_effect=OSError("simulated I/O failure")),
        pytest.raises(DocumentAnalyzerError),
    ):
        DocumentAnalyzer().run(context, record)


def test_analyzer_page_pypdf_error_produces_unknown_encoding_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes(page_count=1))
    record = make_pdf_record(path)

    with patch.object(PageObject, "extract_text", side_effect=PdfReadError("simulated")):
        document = DocumentAnalyzer().run(context, record)

    assert DocumentWarning.UNKNOWN_ENCODING in document.analysis.warnings


def test_analyzer_page_encoding_error_produces_unknown_encoding_warning(
    context: PipelineContext,
    write_pdf: Callable[[str, bytes], Path],
    make_pdf_record: Callable[[Path], PdfRecord],
) -> None:
    path = write_pdf("normal.pdf", normal_pdf_bytes(page_count=1))
    record = make_pdf_record(path)

    with patch.object(
        PageObject, "extract_text", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "boom")
    ):
        document = DocumentAnalyzer().run(context, record)

    assert DocumentWarning.UNKNOWN_ENCODING in document.analysis.warnings
    assert document.analysis.statistics.text_length is None
