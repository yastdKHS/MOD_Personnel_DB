"""テスト専用のStub実装。具象実装はsrc/には置かない（tests/unit/knowledge/_stubs.pyと同じ方針）。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mod_personnel_db.fetch import FetchRequest, FetchResult
from mod_personnel_db.models import (
    ExportArtifact,
    ExportFormat,
    GoldRecord,
    LearningRecord,
    LearningRecordId,
    PdfId,
    PdfRecord,
    PersonnelRecord,
)
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.review import GoldPromotion


class StubFetchClient:
    """URLごとに事前設定した`FetchResult`または例外を返すStub。"""

    def __init__(self, outcomes: dict[str, FetchResult | Exception]) -> None:
        self._outcomes = outcomes
        self.requests: list[FetchRequest] = []

    def fetch(self, request: FetchRequest) -> FetchResult:
        self.requests.append(request)
        outcome = self._outcomes[request.url]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class StubFTPClient:
    """呼び出し順序のみを記録するStub。"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.uploaded: list[tuple[str, str]] = []

    def connect(self) -> None:
        self.calls.append("connect")

    def upload(self, local_path: str, remote_path: str) -> None:
        self.calls.append("upload")
        self.uploaded.append((local_path, remote_path))

    def download(self, remote_path: str, local_path: str) -> None:
        self.calls.append("download")

    def list_remote(self, remote_dir: str) -> tuple[str, ...]:
        self.calls.append("list_remote")
        return ()

    def disconnect(self) -> None:
        self.calls.append("disconnect")


class StubPDFRepository:
    """インメモリの辞書へ保存する`PDFRepository`Protocol実装。"""

    def __init__(self) -> None:
        self._by_id: dict[PdfId, PdfRecord] = {}
        self._by_hash: dict[str, PdfRecord] = {}
        self._next_id = 1

    def add(self, pdf: PdfRecord) -> PdfId:
        pdf_id = PdfId(self._next_id)
        self._next_id += 1
        stored = PdfRecord(
            id=pdf_id,
            content_hash=pdf.content_hash,
            source_url=pdf.source_url,
            published_date=pdf.published_date,
            fetched_at=pdf.fetched_at,
            file_path=pdf.file_path,
            file_size_bytes=pdf.file_size_bytes,
            status=pdf.status,
        )
        self._by_id[pdf_id] = stored
        self._by_hash[pdf.content_hash] = stored
        return pdf_id

    def get(self, pdf_id: PdfId) -> PdfRecord | None:
        return self._by_id.get(pdf_id)

    def get_by_hash(self, content_hash: str) -> PdfRecord | None:
        return self._by_hash.get(content_hash)

    def update_status(self, pdf_id: PdfId, status: str) -> None:
        raise NotImplementedError

    def list_by_status(self, status: str) -> tuple[PdfRecord, ...]:
        raise NotImplementedError


class StubJobRunner:
    """`run_for_pdf()`/`run_pending()`の呼び出しのみを記録するStub
    （`tests/unit/cli/test_commands.py`の`_StubJobRunner`と同じ方針）。
    """

    def __init__(self, results: tuple[PipelineResult, ...] = ()) -> None:
        self._results = results
        self.run_for_pdf_calls: list[PdfRecord] = []
        self.run_pending_called = False

    def run_for_pdf(self, pdf: PdfRecord) -> PipelineResult:
        self.run_for_pdf_calls.append(pdf)
        return self._results[0]

    def run_pending(self) -> tuple[PipelineResult, ...]:
        self.run_pending_called = True
        return self._results


class StubReviewService:
    """`list_pending()`のみ固定値を返すStub。"""

    def __init__(self, pending: tuple[LearningRecord, ...] = ()) -> None:
        self._pending = pending

    def list_pending(self) -> tuple[LearningRecord, ...]:
        return self._pending

    def start_review(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        raise NotImplementedError

    def approve(
        self,
        record_id: LearningRecordId,
        gold_promotion: GoldPromotion | None = None,
        **fields: object,
    ) -> LearningRecord:
        raise NotImplementedError

    def reject(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        raise NotImplementedError


class StubExportService:
    """`export_all_with_metadata()`のみ固定値を返すStub。"""

    def __init__(self, artifact: ExportArtifact) -> None:
        self._artifact = artifact
        self.calls: list[tuple[ExportFormat, str]] = []

    def export_all(self) -> tuple[GoldRecord, ...]:
        raise NotImplementedError

    def export_since(self, since: datetime) -> tuple[GoldRecord, ...]:
        raise NotImplementedError

    def export_person(self, person_id: str) -> tuple[GoldRecord, ...]:
        raise NotImplementedError

    def export_all_records(self) -> tuple[PersonnelRecord, ...]:
        raise NotImplementedError

    def export_since_records(self, since: datetime) -> tuple[PersonnelRecord, ...]:
        raise NotImplementedError

    def export_person_records(self, person_id: str) -> tuple[PersonnelRecord, ...]:
        raise NotImplementedError

    def export_all_csv(self, destination: str | Path) -> None:
        raise NotImplementedError

    def export_all_parquet(self, destination: str | Path) -> None:
        raise NotImplementedError

    def export_all_with_metadata(
        self, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        self.calls.append((export_format, str(destination)))
        return self._artifact

    def export_since_with_metadata(
        self, since: datetime, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        raise NotImplementedError

    def export_person_with_metadata(
        self, person_id: str, export_format: ExportFormat, destination: str | Path
    ) -> ExportArtifact:
        raise NotImplementedError


__all__ = [
    "StubExportService",
    "StubFTPClient",
    "StubFetchClient",
    "StubJobRunner",
    "StubPDFRepository",
    "StubReviewService",
]
