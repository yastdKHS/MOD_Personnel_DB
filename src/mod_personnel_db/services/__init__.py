"""JobOrchestrator契約（Protocol）と実装。Phase7 Task16-4に対応する。

docs/api/package-design.md のservices/節（Phase7 Task16-0で設計確定）が
定める「単一の中核パイプライン実行に閉じない、横断的な運用オーケストレーション」
を実装する。`fetch/`によるPDF取得・`JobRunner`によるパイプライン実行・
`review/`・`export/`（および`ftp/`経由の公開）を束ねる。

`services/`は`fetch/`・`ftp/`・`pipeline/`・`review/`・`export/`の
具象実装を自ら生成しない（[architecture-contract.md 保証15]）。`cli/`
（合成ルート）が構築済みのインスタンスを本パッケージへ注入する想定であり、
`cli/`自体は本パッケージから一切変更していない（本Task16-4では`cli/`との
配線は行わない。将来`cli/bootstrap.py`が`services/`層経由に置き換わる
際は、別タスクでADRを起票した上で実施する）。

具象実装（`DefaultJobOrchestrator`）は`services.orchestrator`から提供する。

`Scheduler`（Phase7 Task17-3）は「いつ`JobOrchestrator`を呼び出すか」の
決定にのみ責務を持つ別契約であり（docs/phase7-integration-design.md
「12. Scheduler導入予定位置」）、`JobOrchestrator`をSchedulerへ統合する
ものではない。標準実装`DefaultScheduler`は`services.scheduler`から提供する。
"""

from datetime import date
from pathlib import Path
from typing import Protocol

from mod_personnel_db.fetch import FetchRequest
from mod_personnel_db.models import (
    ExportArtifact,
    ExportFormat,
    JobId,
    LearningRecord,
    PdfId,
    PdfRecord,
)
from mod_personnel_db.pipeline import PipelineResult
from mod_personnel_db.services.messages import FetchWorkflowError, FetchWorkItem, WorkflowResult
from mod_personnel_db.services.orchestrator import DefaultJobOrchestrator, OrchestratorDependencies
from mod_personnel_db.services.scheduler import (
    RUN_PENDING_JOB_TYPE,
    DefaultScheduler,
    JobSchedule,
    NoPendingJobError,
    SchedulerError,
    UnknownJobTypeError,
)


class JobOrchestrator(Protocol):
    """`fetch/`・`ftp/`・`pipeline/`・`review/`・`export/`を横断的に調整する。"""

    def fetch_and_stage(
        self, request: FetchRequest, *, destination_path: str, published_date: date
    ) -> PdfId | None:
        """PDFを取得し保存する。`content_hash`が既存レコードと重複する場合は`None`を返す。"""
        ...

    def run_job(self, pdf: PdfRecord) -> PipelineResult:
        """指定した1件のPDFを中核パイプラインで処理する。"""
        ...

    def run_pending_pipeline(self) -> tuple[PipelineResult, ...]:
        """未処理PDF（`status='fetched'`）を中核パイプラインで一括処理する。"""
        ...

    def list_pending_reviews(self) -> tuple[LearningRecord, ...]:
        """レビュー待ちのLearning Datasetエントリを返す。"""
        ...

    def export_and_publish(
        self,
        export_format: ExportFormat,
        destination: str | Path,
        *,
        remote_path: str | None = None,
    ) -> ExportArtifact:
        """エクスポートを生成する。`remote_path`が指定されていればFTPでアップロードする。"""
        ...

    def run_workflow(
        self,
        fetch_items: list[FetchWorkItem],
        export_format: ExportFormat,
        export_destination: str | Path,
        *,
        remote_path: str | None = None,
    ) -> WorkflowResult:
        """Fetch→Pipeline→Review→Exportの一連のワークフローを実行する。"""
        ...


class Scheduler(Protocol):
    """パイプライン実行のトリガーを管理する（ADR-0019、docs/api/interfaces.md#scheduler）。"""

    def trigger_now(self, job_type: str) -> JobId: ...
    def list_upcoming(self) -> tuple[str, ...]:
        """今後の予定実行（次回実行時刻等）を返す。"""
        ...


__all__ = [
    "RUN_PENDING_JOB_TYPE",
    "DefaultJobOrchestrator",
    "DefaultScheduler",
    "FetchWorkItem",
    "FetchWorkflowError",
    "JobOrchestrator",
    "JobSchedule",
    "NoPendingJobError",
    "OrchestratorDependencies",
    "Scheduler",
    "SchedulerError",
    "UnknownJobTypeError",
    "WorkflowResult",
]
