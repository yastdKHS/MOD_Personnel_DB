"""`JobOrchestrator`の入出力値オブジェクト。

`services/`パッケージ自身のローカルな値オブジェクトであり、`models/`の
ドメインモデルではない（`FetchWorkItem`は`fetch.FetchRequest`と、
実際にPDFを保存・登録するために必要な追加情報（保存先パス・発令日）を
束ねる、オーケストレーション専用の入力である）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from mod_personnel_db.fetch import FetchRequest
from mod_personnel_db.models import ExportArtifact, PdfId
from mod_personnel_db.pipeline import PipelineResult


@dataclass(frozen=True, slots=True)
class FetchWorkItem:
    """1件のPDF取得依頼（取得元・保存先・発令日）。"""

    request: FetchRequest
    destination_path: str
    published_date: date


@dataclass(frozen=True, slots=True)
class FetchWorkflowError:
    """`run_workflow()`のFetchフェーズで発生した、個別URLの取得失敗。"""

    url: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """`run_workflow()`の集計結果。"""

    fetched_pdf_ids: tuple[PdfId, ...]
    fetch_errors: tuple[FetchWorkflowError, ...]
    pipeline_results: tuple[PipelineResult, ...]
    pending_review_count: int
    export_artifact: ExportArtifact


__all__ = ["FetchWorkItem", "FetchWorkflowError", "WorkflowResult"]
