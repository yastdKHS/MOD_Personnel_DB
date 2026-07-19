"""テスト用の合成PDFバイト列を生成するヘルパー。実在の発令PDFは一切使用しない。"""

import io

from pypdf import PdfWriter


def normal_pdf_bytes(page_count: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=210, height=297)
    return _write(writer)


def empty_pdf_bytes() -> bytes:
    """ページ数0の、構造としては正常なPDF。"""
    return _write(PdfWriter())


def broken_pdf_bytes() -> bytes:
    """PDFとして解釈できない破損データ。"""
    return b"%PDF-1.7\nthis is not a valid pdf body at all"


def rotated_pdf_bytes() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=210, height=297)
    page.rotate(90)
    return _write(writer)


def encrypted_pdf_bytes(user_password: str = "secret") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=210, height=297)
    writer.encrypt(user_password=user_password, owner_password="owner-secret")
    return _write(writer)


def _write(writer: PdfWriter) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
