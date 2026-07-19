# Component Interfaces（公開API定義）

> **本ドキュメントに実装はない。** すべてのコードブロックは`typing.Protocol`による**型シグネチャのみ**（メソッド本体は`...`）であり、`.pyi`スタブファイルと同等の位置づけである。ロジックは一切含まない。実際の実装は将来のタスクで別途行う。
>
> 型は[`models.md`](models.md)で定義するモデル・値オブジェクトを用いる。パッケージ境界は[`package-design.md`](package-design.md)、依存ルールは[`dependency-rule.md`](dependency-rule.md)を参照。Protocol/ABC使い分けの方針は[`python-contract.md`](python-contract.md)を参照。

## 対象コンポーネント

中核パイプライン6段階（`run()`のみ公開、[`pipeline.md`](pipeline.md)参照）: `DocumentAnalyzer`, `LayoutDetector`, `SectionParser`, `FieldExtractor`, `Normalizer`, `Validator`

永続化: `Repository`（総称）

サービス層: `ReviewService`, `ExportService`, `FTPService`, `KnowledgeService`, `LearningService`, `FeatureStore`, `Scheduler`, `JobRunner`

---

## 中核パイプライン6段階

すべて`PipelineStage[TIn, TOut]`（[`pipeline.md`](pipeline.md)）に準拠し、公開メソッドは`run()`のみとする。

```python
from typing import Protocol
from mod_personnel_db.models import (
    Document, LayoutArtifact, SectionParseResult, PersonnelSection,
    RawRecord, NormalizedRecord, KnowledgeSnapshot, ValidationResult,
    ValidationRuleSet, PdfRecord,
)
from mod_personnel_db.pipeline import PipelineContext


class DocumentAnalyzer(Protocol):
    """取得済みPDFのメタデータ・健全性・基本統計を取得する（中核パイプライン段階1）。

    Version 2.0（ADR-0032）: PDF解析（構造抽出）・OCR・文字抽出・様式判定は行わない。
    戻り値`Document`はページ単位の抽出済みテキストを保持しない「Document Identity」
    （id/source_pdf_id/analysis/analyzed_at/analyzer_version）である。
    """

    def run(self, context: PipelineContext, source: PdfRecord) -> Document: ...


class LayoutDetector(Protocol):
    """Documentから該当する様式（era_id）を判定する（段階2）。

    **PDF本文アクセスの独占（ADR-0035）**: Layout Detectorは、`document.file_path`
    を用いてPDFファイルを自ら再読込する、**PDF本文（文字列・Font・Bounding Box・
    Drawing・Rotation・画像・Annotation）へアクセスできる唯一のPipeline Stage**
    である。Document Analyzer（段階1）はこれらにアクセスせず（ADR-0032）、
    Section Parser以降（段階3〜）も直接アクセスしない。戻り値`LayoutArtifact`
    （[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）は、
    判定結果（`.detection: LayoutDetectionResult`）に加え、再読込した各ページの
    生テキスト（`.pages`）を保持する——これがSection ParserがPDF本文を得る
    唯一の経路となる。
    """

    def run(self, context: PipelineContext, document: Document) -> LayoutArtifact: ...


class SectionParser(Protocol):
    """LayoutArtifactからPersonnel Sectionを切り出す（段階3）。

    **LayoutArtifact経由でのみPDFのテキストを得る（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)）**:
    Section ParserはPDFファイルを直接読み込まず、`pypdf`等のPDF解析ライブラリにも
    依存しない。利用できるPDF由来のテキストは、入力`LayoutArtifact.pages`のみで
    ある。`LayoutArtifact.detection.layout_id`が`None`（未知様式）の場合、
    例外は送出せず`SectionParseResult.sections`を空で返す
    （[`models.md`](models.md#sectionparseresult)参照）。
    """

    def run(self, context: PipelineContext, artifact: LayoutArtifact) -> SectionParseResult: ...


class FieldExtractor(Protocol):
    """セクションから正規化前のフィールドを抽出する（段階4）。"""

    def run(self, context: PipelineContext, section: PersonnelSection) -> tuple[RawRecord, ...]: ...


class Normalizer(Protocol):
    """抽出値をKnowledge Baseで正規化する（段階5）。knowledgeは呼び出し元が注入する。"""

    def run(
        self, context: PipelineContext, record: RawRecord, knowledge: KnowledgeSnapshot
    ) -> NormalizedRecord: ...


class Validator(Protocol):
    """正規化後のデータを検証する（段階6）。レコードの値は変更しない。"""

    def run(
        self, context: PipelineContext, record: NormalizedRecord, rules: ValidationRuleSet
    ) -> ValidationResult: ...
```

各段階の入出力型・パッケージ境界の詳細は[`package-design.md`](package-design.md)の該当節を参照。

---

## `Repository`（総称インターフェース）

個々の8リポジトリ（`CandidateRepository`等）は[`repositories.md`](repositories.md)で定義する。ここでは全リポジトリが従う総称形だけを示す。

```python
from typing import Protocol, TypeVar

TEntity = TypeVar("TEntity")
TId = TypeVar("TId")


class Repository(Protocol[TEntity, TId]):
    """全Repositoryが実装する最小共通契約。個々のRepositoryはこれを拡張する。"""

    def get(self, entity_id: TId) -> TEntity | None: ...
    def add(self, entity: TEntity) -> TId: ...
```

---

## `ReviewService`

> **本節は簡略版である。** Review Domain（[`docs/review/`](../review/)）の設計に伴い、`ReviewService`の完全な契約（キュー・割当・差戻し・再レビュー等を含む）は [`docs/api/review.md`](review.md#reviewservice) を正とする。以下は最小限のコア操作のみを示す。

```python
from typing import Protocol
from mod_personnel_db.models import ReviewItem, GoldRecordId, CandidateId, ReviewSessionId


class ReviewService(Protocol):
    """人手レビューのワークフローを提供する（ADR-0021）。"""

    def open_session(self, reviewer: str, reason: str) -> ReviewSessionId: ...

    def list_pending(self, session_id: ReviewSessionId | None = None) -> tuple[CandidateId, ...]:
        """検証NG・未レビューの候補一覧を返す。"""
        ...

    def submit_change(
        self, session_id: ReviewSessionId, item: ReviewItem
    ) -> None:
        """1件のフィールド修正を記録する。gold_recordsへの反映は行わない。"""
        ...

    def promote_to_gold(
        self, session_id: ReviewSessionId, candidate_id: CandidateId
    ) -> GoldRecordId:
        """レビュー確定済みの候補をGold Databaseへ昇格する。gold_recordsへの書き込みはこのメソッド経由のみ。"""
        ...

    def close_session(self, session_id: ReviewSessionId) -> None: ...
```

---

## `ExportService`

```python
from typing import Protocol
from datetime import datetime
from mod_personnel_db.models import ExportRecord, ExportId


class ExportService(Protocol):
    """公開用エクスポート（JSON/CSV/Parquet）を生成する（ADR-0016, ADR-0022）。"""

    def generate(self, format: str, as_of: datetime | None = None) -> ExportRecord: ...
    def get(self, export_id: ExportId) -> ExportRecord | None: ...
    def list_recent(self, limit: int = 10) -> tuple[ExportRecord, ...]: ...
```

---

## `FTPService`

```python
from typing import Protocol


class FTPService(Protocol):
    """FTP/SFTP経由のファイル転送（プロトコル層。ドメインモデルを扱わない）。"""

    def upload(self, local_path: str, remote_path: str) -> None: ...
    def download(self, remote_path: str, local_path: str) -> None: ...
    def list_remote(self, remote_dir: str) -> tuple[str, ...]: ...
```

---

## `KnowledgeService`

```python
from typing import Protocol
from datetime import date
from mod_personnel_db.models import KnowledgeSnapshot, KnowledgeItem


class KnowledgeService(Protocol):
    """knowledge/ 配下のYAMLを読み込み、正規化・検証に使うスナップショットを提供する（ADR-0005）。"""

    def load_snapshot(self, as_of: date | None = None) -> KnowledgeSnapshot: ...
    def get_item(self, category: str, item_key: str) -> KnowledgeItem | None: ...
    def reload(self) -> KnowledgeSnapshot:
        """knowledge/ ディレクトリを再読み込みし、KnowledgeRepositoryへ反映する。"""
        ...
```

---

## `LearningService`

```python
from typing import Protocol
from mod_personnel_db.models import LearningRecord, LearningRecordId, LearningStatus


class LearningService(Protocol):
    """Learning Dataset（ADR-0013, ADR-0017）のライフサイクルを管理する。"""

    def record_error(self, entry: LearningRecord) -> LearningRecordId: ...

    def transition(
        self, record_id: LearningRecordId, new_status: LearningStatus, **fields: object
    ) -> LearningRecord:
        """状態遷移（open→in_review→reflected→verified/wontfix）を1段階進める。"""
        ...

    def list_open(self) -> tuple[LearningRecord, ...]: ...
    def summarize_by_error_category(self) -> dict[str, int]: ...
```

---

## `FeatureStore`

```python
from typing import Protocol
from mod_personnel_db.models import FeatureVector, RawRecord, NormalizedRecord


class FeatureStore(Protocol):
    """Confidence算出等に使う派生特徴量を計算する（V2.0時点では永続化せず都度計算、package-design.md参照）。"""

    def compute(
        self, subject: RawRecord | NormalizedRecord
    ) -> FeatureVector: ...
```

---

## `Scheduler`

```python
from typing import Protocol
from mod_personnel_db.models import JobId


class Scheduler(Protocol):
    """パイプライン実行のトリガーを管理する（ADR-0019）。"""

    def trigger_now(self, job_type: str) -> JobId: ...
    def list_upcoming(self) -> tuple[str, ...]:
        """今後の予定実行（cron定義に基づく次回実行時刻等）を返す。"""
        ...
```

---

## `JobRunner`

```python
from typing import Protocol
from mod_personnel_db.models import Job, JobId, PdfRecord
from mod_personnel_db.pipeline import PipelineResult


class JobRunner(Protocol):
    """中核パイプラインの実行を調整する（pipeline/の主要な公開窓口）。"""

    def run_for_pdf(self, pdf: PdfRecord) -> PipelineResult: ...
    def run_pending(self) -> tuple[PipelineResult, ...]:
        """未処理のPDF（PDFRepository経由で取得）をすべて処理する。"""
        ...
    def get_job(self, job_id: JobId) -> Job | None: ...
```

---

## 命名・型に関する注意

- 引数・戻り値の型はすべて[`models.md`](models.md)で定義するモデル、または本ドキュメントで補助的に使う軽量なID型（`CandidateId`, `GoldRecordId`, `JobId`等、`models.md`の「補助的な値オブジェクト」節に定義）である。
- 全メソッドが型ヒント必須（[`python-contract.md`](python-contract.md)）。
- `Protocol`を用いる理由（`ABC`ではなく）は[`python-contract.md`](python-contract.md#protocol利用方針)を参照。
