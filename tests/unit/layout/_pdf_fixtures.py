"""テスト用の合成PDFバイト列を生成するヘルパー。実在の発令PDFは一切使用しない。

`document/`の`_pdf_fixtures.py`と異なり、Layout Detectorはページ本文・Fontへ
アクセスするため、テキスト・Font情報を含むPDFを合成する。
"""

import io

from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def text_pdf_bytes(
    *,
    header: str = "MOD PERSONNEL ORDER FORMAT A",
    footer: str = "END OF DOCUMENT",
    page_count: int = 2,
    font_name: str = "Helvetica",
) -> bytes:
    writer = PdfWriter()
    for index in range(page_count):
        body = header if index == 0 else f"body line {index}"
        _add_text_page(writer, first_line=body, last_line=footer, font_name=font_name)
    return _write(writer)


def broken_pdf_bytes() -> bytes:
    """PDFとして解釈できない破損データ。"""
    return b"%PDF-1.7\nthis is not a valid pdf body at all"


def rotated_text_pdf_bytes(*, rotation: int = 90) -> bytes:
    writer = PdfWriter()
    page = _add_text_page(writer, first_line="rotated header", last_line="rotated footer")
    page.rotate(rotation)
    return _write(writer)


def blank_pdf_bytes(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=210, height=297)
    return _write(writer)


def _add_text_page(
    writer: PdfWriter, *, first_line: str, last_line: str, font_name: str = "Helvetica"
) -> PageObject:
    page = writer.add_blank_page(width=210, height=297)
    font_ref = writer._add_object(_font_dict(font_name))
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font_ref
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources

    content = DecodedStreamObject()
    stream = (
        f"BT /F1 12 Tf 50 700 Td ({_escape(first_line)}) Tj ET\n"
        f"BT /F1 12 Tf 50 50 Td ({_escape(last_line)}) Tj ET"
    )
    content.set_data(stream.encode("utf-8"))
    content_ref = writer._add_object(content)
    page[NameObject("/Contents")] = content_ref
    return page


def _font_dict(font_name: str) -> DictionaryObject:
    font_dict = DictionaryObject()
    font_dict[NameObject("/Type")] = NameObject("/Font")
    font_dict[NameObject("/Subtype")] = NameObject("/Type1")
    font_dict[NameObject("/BaseFont")] = NameObject(f"/{font_name}")
    return font_dict


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _write(writer: PdfWriter) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
