"""`DefaultJobOrchestrator`の単体テスト（Phase7 Task16-4）。"""

import dataclasses
import hashlib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from mod_personnel_db.fetch import FetchRequest, FetchResult, FetchTimeoutError
from mod_personnel_db.models import (
    ErrorCategory,
    ExportArtifact,
    Job,
    JobId,
    LearningRecord,
    LearningStatus,
    ParserVersionId,
    PdfId,
    PdfRecord,
    PipelineStageName,
    RegressionStatus,
)
from mod_personnel_db.pipeline.context import PipelineContext
from mod_personnel_db.pipeline.exceptions import PipelineException
from mod_personnel_db.pipeline.metrics import PipelineMetrics
from mod_personnel_db.pipeline.result import PipelineResult
from mod_personnel_db.services import FetchWorkItem, JobOrchestrator, WorkflowResult
from mod_personnel_db.services.orchestrator import DefaultJobOrchestrator, OrchestratorDependencies

from ._stubs import (
    StubExportService,
    StubFetchClient,
    StubFTPClient,
    StubJobRunner,
    StubPDFRepository,
    StubReviewService,
)


def _pipeline_result(*, succeeded: bool = True) -> PipelineResult:
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    finished_at = datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC)
    job = Job(
        id=JobId(1),
        job_type="core_pipeline",
        pdf_id=PdfId(1),
        parser_version_id=ParserVersionId(1),
        status="succeeded" if succeeded else "failed",
        started_at=started_at,
        finished_at=finished_at,
        processed_count=1 if succeeded else 0,
        failed_count=0 if succeeded else 1,
        error_summary=None,
    )
    context = PipelineContext(
        job_id=JobId(1),
        parser_version_id=ParserVersionId(1),
        correlation_id="job-1",
        started_at=started_at,
    )
    metrics = PipelineMetrics(
        elapsed_ms=1000.0,
        started_at=started_at,
        finished_at=finished_at,
        succeeded=succeeded,
        warning_count=0,
        error_count=0 if succeeded else 1,
    )
    error = PipelineException("validator", context, "boom") if not succeeded else None
    return PipelineResult(context=context, job=job, events=(), metrics=metrics, error=error)


def _export_artifact() -> ExportArtifact:
    return ExportArtifact(
        export_id="export-1",
        exported_at=datetime(2026, 1, 1, tzinfo=UTC),
        format="json",
        record_count=0,
        sha256="a" * 64,
    )


def _default_dependencies() -> OrchestratorDependencies:
    job_runner = StubJobRunner()
    return OrchestratorDependencies(
        fetch_client=StubFetchClient({}),
        ftp_client=StubFTPClient(),
        pdf_repository=StubPDFRepository(),
        job_runner=job_runner,  # type: ignore[arg-type]
        review_service=StubReviewService(),
        export_service=StubExportService(_export_artifact()),
    )


def _dependencies(**overrides: Any) -> OrchestratorDependencies:
    return dataclasses.replace(_default_dependencies(), **overrides)


def test_orchestrator_satisfies_job_orchestrator_protocol() -> None:
    orchestrator: JobOrchestrator = DefaultJobOrchestrator(_dependencies())
    assert isinstance(orchestrator, DefaultJobOrchestrator)


def test_fetch_and_stage_registers_new_pdf(tmp_path: Path) -> None:
    body = b"%PDF-1.4 order body"
    fetch_client = StubFetchClient(
        {
            "https://example.mod.go.jp/order.pdf": FetchResult(
                url="https://example.mod.go.jp/order.pdf",
                status_code=200,
                content_type="application/pdf",
                body=body,
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        }
    )
    pdf_repository = StubPDFRepository()
    orchestrator = DefaultJobOrchestrator(
        _dependencies(fetch_client=fetch_client, pdf_repository=pdf_repository)
    )
    destination = str(tmp_path / "order.pdf")

    pdf_id = orchestrator.fetch_and_stage(
        FetchRequest(url="https://example.mod.go.jp/order.pdf"),
        destination_path=destination,
        published_date=date(2026, 1, 1),
    )

    assert pdf_id is not None
    assert Path(destination).read_bytes() == body
    stored = pdf_repository.get(pdf_id)
    assert stored is not None
    assert stored.content_hash == hashlib.sha256(body).hexdigest()
    assert stored.status == "fetched"


def test_fetch_and_stage_returns_none_for_duplicate_content_hash(tmp_path: Path) -> None:
    body = b"%PDF-1.4 duplicate body"
    content_hash = hashlib.sha256(body).hexdigest()
    pdf_repository = StubPDFRepository()
    pdf_repository.add(
        PdfRecord(
            id=None,
            content_hash=content_hash,
            source_url="https://example.mod.go.jp/existing.pdf",
            published_date=date(2026, 1, 1),
            fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            file_path="existing/path.pdf",
            file_size_bytes=len(body),
            status="fetched",
        )
    )
    fetch_client = StubFetchClient(
        {
            "https://example.mod.go.jp/order.pdf": FetchResult(
                url="https://example.mod.go.jp/order.pdf",
                status_code=200,
                content_type="application/pdf",
                body=body,
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        }
    )
    orchestrator = DefaultJobOrchestrator(
        _dependencies(fetch_client=fetch_client, pdf_repository=pdf_repository)
    )
    destination = str(tmp_path / "order.pdf")

    pdf_id = orchestrator.fetch_and_stage(
        FetchRequest(url="https://example.mod.go.jp/order.pdf"),
        destination_path=destination,
        published_date=date(2026, 1, 1),
    )

    assert pdf_id is None
    assert not Path(destination).exists()


def test_run_job_delegates_to_job_runner() -> None:
    result = _pipeline_result()
    job_runner = StubJobRunner(results=(result,))
    orchestrator = DefaultJobOrchestrator(_dependencies(job_runner=job_runner))
    pdf = PdfRecord(
        id=PdfId(1),
        content_hash="x" * 64,
        source_url="https://example.mod.go.jp/order.pdf",
        published_date=date(2026, 1, 1),
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        file_path="a/b.pdf",
        file_size_bytes=10,
        status="fetched",
    )

    outcome = orchestrator.run_job(pdf)

    assert outcome is result
    assert job_runner.run_for_pdf_calls == [pdf]


def test_run_pending_pipeline_delegates_to_job_runner() -> None:
    results = (_pipeline_result(), _pipeline_result(succeeded=False))
    job_runner = StubJobRunner(results=results)
    orchestrator = DefaultJobOrchestrator(_dependencies(job_runner=job_runner))

    outcome = orchestrator.run_pending_pipeline()

    assert outcome == results
    assert job_runner.run_pending_called is True


def test_list_pending_reviews_delegates_to_review_service() -> None:
    pending = (
        LearningRecord(
            id=None,
            source_candidate_id=None,
            source_review_item_id=None,
            pipeline_stage=PipelineStageName.VALIDATOR,
            error_category=ErrorCategory.KNOWLEDGE_GAP,
            field_name="rank",
            wrong_value="x",
            correct_value="y",
            correction_summary=None,
            reviewer_comment=None,
            parser_version_id=None,
            layout_id=None,
            confidence=None,
            status=LearningStatus.OPEN,
            reflected_in_knowledge_item_id=None,
            reflected_in_layout_id=None,
            git_commit_hash=None,
            pull_request_url=None,
            regression_status=RegressionStatus.NOT_RUN,
            regression_run_at=None,
            regression_details=None,
            improvement_candidate=None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            resolved_at=None,
        ),
    )
    review_service = StubReviewService(pending=pending)
    orchestrator = DefaultJobOrchestrator(_dependencies(review_service=review_service))

    outcome = orchestrator.list_pending_reviews()

    assert outcome == pending


def test_export_and_publish_without_remote_path_does_not_call_ftp(tmp_path: Path) -> None:
    artifact = _export_artifact()
    export_service = StubExportService(artifact)
    ftp_client = StubFTPClient()
    orchestrator = DefaultJobOrchestrator(
        _dependencies(export_service=export_service, ftp_client=ftp_client)
    )
    destination = tmp_path / "export.json"

    outcome = orchestrator.export_and_publish("json", destination)

    assert outcome is artifact
    assert ftp_client.calls == []
    assert export_service.calls == [("json", str(destination))]


def test_export_and_publish_with_remote_path_uploads_via_ftp(tmp_path: Path) -> None:
    artifact = _export_artifact()
    export_service = StubExportService(artifact)
    ftp_client = StubFTPClient()
    orchestrator = DefaultJobOrchestrator(
        _dependencies(export_service=export_service, ftp_client=ftp_client)
    )
    destination = tmp_path / "export.json"

    orchestrator.export_and_publish("json", destination, remote_path="remote/export.json")

    assert ftp_client.calls == ["connect", "upload", "disconnect"]
    assert ftp_client.uploaded == [(str(destination), "remote/export.json")]


def test_export_and_publish_disconnects_even_if_upload_fails(tmp_path: Path) -> None:
    class _FailingFTPClient(StubFTPClient):
        def upload(self, local_path: str, remote_path: str) -> None:
            self.calls.append("upload")
            raise RuntimeError("upload failed")

    ftp_client = _FailingFTPClient()
    orchestrator = DefaultJobOrchestrator(
        _dependencies(export_service=StubExportService(_export_artifact()), ftp_client=ftp_client)
    )
    destination = tmp_path / "export.json"

    with pytest.raises(RuntimeError):
        orchestrator.export_and_publish("json", destination, remote_path="remote/export.json")

    assert ftp_client.calls == ["connect", "upload", "disconnect"]


def test_run_workflow_aggregates_all_phases(tmp_path: Path) -> None:
    body = b"%PDF-1.4 order body"
    request = FetchRequest(url="https://example.mod.go.jp/order.pdf")
    fetch_client = StubFetchClient(
        {
            request.url: FetchResult(
                url=request.url,
                status_code=200,
                content_type="application/pdf",
                body=body,
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        }
    )
    pipeline_result = _pipeline_result()
    job_runner = StubJobRunner(results=(pipeline_result,))
    artifact = _export_artifact()
    export_service = StubExportService(artifact)
    ftp_client = StubFTPClient()
    orchestrator = DefaultJobOrchestrator(
        _dependencies(
            fetch_client=fetch_client,
            job_runner=job_runner,
            export_service=export_service,
            ftp_client=ftp_client,
        )
    )
    destination = tmp_path / "export.json"

    outcome = orchestrator.run_workflow(
        [
            FetchWorkItem(
                request=request,
                destination_path=str(tmp_path / "order.pdf"),
                published_date=date(2026, 1, 1),
            )
        ],
        "json",
        destination,
        remote_path="remote/export.json",
    )

    assert isinstance(outcome, WorkflowResult)
    assert len(outcome.fetched_pdf_ids) == 1
    assert outcome.fetch_errors == ()
    assert outcome.pipeline_results == (pipeline_result,)
    assert outcome.pending_review_count == 0
    assert outcome.export_artifact is artifact
    assert ftp_client.calls == ["connect", "upload", "disconnect"]


def test_run_workflow_collects_fetch_errors_and_continues(tmp_path: Path) -> None:
    ok_request = FetchRequest(url="https://example.mod.go.jp/ok.pdf")
    bad_request = FetchRequest(url="https://example.mod.go.jp/bad.pdf")
    body = b"%PDF-1.4 ok"
    fetch_client = StubFetchClient(
        {
            ok_request.url: FetchResult(
                url=ok_request.url,
                status_code=200,
                content_type="application/pdf",
                body=body,
                fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            bad_request.url: FetchTimeoutError("timed out"),
        }
    )
    job_runner = StubJobRunner(results=(_pipeline_result(),))
    orchestrator = DefaultJobOrchestrator(
        _dependencies(fetch_client=fetch_client, job_runner=job_runner)
    )

    items = [
        FetchWorkItem(
            request=ok_request,
            destination_path=str(tmp_path / "ok.pdf"),
            published_date=date(2026, 1, 1),
        ),
        FetchWorkItem(
            request=bad_request,
            destination_path=str(tmp_path / "bad.pdf"),
            published_date=date(2026, 1, 1),
        ),
    ]

    outcome = orchestrator.run_workflow(items, "json", tmp_path / "export.json")

    assert len(outcome.fetched_pdf_ids) == 1
    assert len(outcome.fetch_errors) == 1
    assert outcome.fetch_errors[0].url == bad_request.url
    assert not (tmp_path / "bad.pdf").exists()
