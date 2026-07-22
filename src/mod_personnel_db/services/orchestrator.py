"""`JobOrchestrator`の標準実装。docs/api/package-design.md のservices/節
（Phase7 Task16-0で設計確定）に対応する。

`fetch/`・`ftp/`・`pipeline/`（`JobRunner`）・`review/`・`export/`の
既に構築済みのインスタンスをコンストラクタ注入で受け取り、それらを
呼び出す順序・タイミングのみを制御する（`services/`自身は具象実装を
一切生成しない、architecture-contract.md 保証15）。

**エラー伝播・ロールバック方針**:

- **Fetchフェーズ（`fetch_and_stage`のバッチ実行）**: `fetch.FetchError`
  （個別URLのタイムアウト・HTTPステータス異常等）は`run_workflow()`内で
  捕捉し、`FetchWorkflowError`として収集して処理を継続する。1件のURLの
  不備がバッチ全体を止めないようにするための意図的な設計判断である。
- **永続化（`PDFRepository.add`）**: `RepositoryError`はここでは捕捉せず
  そのまま伝播させる（インフラ層の異常はフェイルファストとする）。
  `add()`は単一PDFに対する単一の原子的操作であり、失敗しても他の既に
  登録済みのPDFレコードには影響しない（アプリケーションレベルの
  ロールバック処理は不要）。
- **Pipelineフェーズ**: `JobRunner.run_pending()`は個々のPDFの失敗を
  `PipelineResult.error`に閉じ込め、例外を送出しない（`pipeline/`自身の
  既存設計）。本パッケージはこれをそのまま呼び出し元へ返す。
- **Export/FTP公開フェーズ**: `export_and_publish()`は`ExportService`・
  `FTPClient`が送出する例外を捕捉せずそのまま伝播させる（フェイルファスト）。
  公開の失敗は運用者が即座に把握すべき事象であり、既に完了している
  Fetch/Pipelineの結果を巻き戻す処理は行わない（各フェーズの成果は
  独立して有効であり、後続フェーズの失敗によって無効化されない）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mod_personnel_db.export import ExportService
from mod_personnel_db.fetch import FetchClient, FetchError, FetchRequest
from mod_personnel_db.ftp import FTPClient
from mod_personnel_db.models import ExportArtifact, ExportFormat, LearningRecord, PdfId, PdfRecord
from mod_personnel_db.pipeline import PipelineResult
from mod_personnel_db.pipeline.job_runner import JobRunner
from mod_personnel_db.repositories import PDFRepository
from mod_personnel_db.review import ReviewService
from mod_personnel_db.services.messages import FetchWorkflowError, FetchWorkItem, WorkflowResult


@dataclass(frozen=True, slots=True)
class OrchestratorDependencies:
    """`DefaultJobOrchestrator`が注入される依存の束（引数個数削減のための集約、
    `pipeline.job_runner.JobRunnerRepositories`と同じ設計判断）。
    """

    fetch_client: FetchClient
    ftp_client: FTPClient
    pdf_repository: PDFRepository
    job_runner: JobRunner
    review_service: ReviewService
    export_service: ExportService


class DefaultJobOrchestrator:
    """`fetch/`・`ftp/`・`pipeline/`・`review/`・`export/`を調整する`JobOrchestrator`実装。"""

    def __init__(self, dependencies: OrchestratorDependencies) -> None:
        self._fetch_client = dependencies.fetch_client
        self._ftp_client = dependencies.ftp_client
        self._pdf_repository = dependencies.pdf_repository
        self._job_runner = dependencies.job_runner
        self._review_service = dependencies.review_service
        self._export_service = dependencies.export_service

    def fetch_and_stage(
        self, request: FetchRequest, *, destination_path: str, published_date: date
    ) -> PdfId | None:
        """PDFを取得し保存する。`content_hash`が既存レコードと重複する場合は`None`を返す。"""
        result = self._fetch_client.fetch(request)
        content_hash = hashlib.sha256(result.body).hexdigest()
        if self._pdf_repository.get_by_hash(content_hash) is not None:
            return None

        Path(destination_path).write_bytes(result.body)
        record = PdfRecord(
            id=None,
            content_hash=content_hash,
            source_url=request.url,
            published_date=published_date,
            fetched_at=result.fetched_at,
            file_path=destination_path,
            file_size_bytes=len(result.body),
            status="fetched",
        )
        return self._pdf_repository.add(record)

    def run_job(self, pdf: PdfRecord) -> PipelineResult:
        """指定した1件のPDFを中核パイプラインで処理する。"""
        return self._job_runner.run_for_pdf(pdf)

    def run_pending_pipeline(self) -> tuple[PipelineResult, ...]:
        """未処理PDF（`status='fetched'`）を中核パイプラインで一括処理する。"""
        return self._job_runner.run_pending()

    def list_pending_reviews(self) -> tuple[LearningRecord, ...]:
        """レビュー待ち（`status='open'`）のLearning Datasetエントリを返す。"""
        return self._review_service.list_pending()

    def export_and_publish(
        self,
        export_format: ExportFormat,
        destination: str | Path,
        *,
        remote_path: str | None = None,
    ) -> ExportArtifact:
        """エクスポートを生成する。`remote_path`が指定されていればFTPでアップロードする。"""
        artifact = self._export_service.export_all_with_metadata(export_format, destination)
        if remote_path is not None:
            self._ftp_client.connect()
            try:
                self._ftp_client.upload(str(destination), remote_path)
            finally:
                self._ftp_client.disconnect()
        return artifact

    def run_workflow(
        self,
        fetch_items: list[FetchWorkItem],
        export_format: ExportFormat,
        export_destination: str | Path,
        *,
        remote_path: str | None = None,
    ) -> WorkflowResult:
        """Fetch→Pipeline→Review→Exportの一連のワークフローを実行する。"""
        fetched_ids, fetch_errors = self._fetch_all(fetch_items)
        pipeline_results = self.run_pending_pipeline()
        pending_reviews = self.list_pending_reviews()
        export_artifact = self.export_and_publish(
            export_format, export_destination, remote_path=remote_path
        )

        return WorkflowResult(
            fetched_pdf_ids=tuple(fetched_ids),
            fetch_errors=tuple(fetch_errors),
            pipeline_results=pipeline_results,
            pending_review_count=len(pending_reviews),
            export_artifact=export_artifact,
        )

    def _fetch_all(
        self, fetch_items: list[FetchWorkItem]
    ) -> tuple[list[PdfId], list[FetchWorkflowError]]:
        fetched_ids: list[PdfId] = []
        fetch_errors: list[FetchWorkflowError] = []
        for item in fetch_items:
            try:
                pdf_id = self.fetch_and_stage(
                    item.request,
                    destination_path=item.destination_path,
                    published_date=item.published_date,
                )
            except FetchError as exc:
                fetch_errors.append(FetchWorkflowError(url=item.request.url, message=str(exc)))
                continue
            if pdf_id is not None:
                fetched_ids.append(pdf_id)
        return fetched_ids, fetch_errors


__all__ = ["DefaultJobOrchestrator", "OrchestratorDependencies"]
