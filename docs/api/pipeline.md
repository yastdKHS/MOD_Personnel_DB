# Pipeline Interface

> **本ドキュメントに実装はない。** 型シグネチャのみ。中核パイプライン6段階（[ADR-0011](../adr/0011-fixed-core-pipeline.md)）はこの`PipelineStage`契約に従う。

## 設計原則: 各Stageは`run()`のみを公開する

`DocumentAnalyzer`, `LayoutDetector`, `SectionParser`, `FieldExtractor`, `Normalizer`, `Validator`（[`interfaces.md`](interfaces.md)）はすべて、公開メソッドを`run()`一つに限定する。これは以下を強制するための設計上の制約である。

- 各段階は**純粋な変換**（入力→出力）であり、副作用（DB書き込み・ファイルI/O・外部サービス呼び出し）を持たない。
- 副作用（Repositoryへの永続化）は、`run()`の呼び出し元である`pipeline/`（`JobRunner`）のみが行う。
- これにより、[`architecture-contract.md`](../architecture/architecture-contract.md)の「Field ExtractorはDBを知らない」等の分離保証が、`extractors/`パッケージが`repositories/`に一切依存しないという構造上の事実として担保される（[`dependency-rule.md`](dependency-rule.md)）。

`run()`が複数の引数を取ること自体は妨げない（例: `Normalizer.run(context, record, knowledge)`）。「公開APIが`run`という1つのメソッド名に限定される」ことが制約の本体であり、引数の数は制約しない。

---

## `PipelineContext`

パイプライン実行1回分を通じて各`run()`呼び出しに渡される、横断的な実行情報。Repositoryへの参照は**含まない**（各Stageがrepositoryにアクセスできてしまうことを防ぐため）。

```python
from dataclasses import dataclass
from datetime import datetime
from mod_personnel_db.models import JobId, ParserVersionId


@dataclass(frozen=True, slots=True)
class PipelineContext:
    job_id: JobId
    parser_version_id: ParserVersionId
    correlation_id: str
    started_at: datetime
```

- **属性**: `correlation_id`はログ相関用の一意識別子（[`python-contract.md`](python-contract.md#logging設計)のログ設計と対応）。
- **不変条件**: 生成後は不変。1回のパイプライン実行（1PDF分）につき1つの`PipelineContext`が生成され、全Stage呼び出しに使い回される。

## `PipelineStage`

全6段階が実装するジェネリックProtocol。

```python
from typing import Protocol, TypeVar

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class PipelineStage(Protocol[TIn, TOut]):
    """公開APIはrun()のみ。"""

    def run(self, context: PipelineContext, input: TIn) -> TOut: ...
```

各段階の`TIn`/`TOut`の具体化は[`interfaces.md`](interfaces.md#中核パイプライン6段階)を参照。

## `PipelineResult`

`JobRunner`が1件のPDF処理（またはその一部）の結果をまとめる型。

```python
from dataclasses import dataclass
from mod_personnel_db.models import Job


@dataclass(frozen=True, slots=True)
class PipelineResult:
    context: PipelineContext
    job: Job
    events: tuple["PipelineEvent", ...]
    metrics: "PipelineMetrics"
    error: "PipelineException | None"

    @property
    def succeeded(self) -> bool: ...
```

- **不変条件**: `error is not None`と`job.status == "failed"`は同値。`succeeded`は`error is None`と等価な派生プロパティ。

## `PipelineEvent`

観測可能性（[`docs/architecture.md`](../architecture.md#非機能要件長期運用の観点)の「可観測性」要件）のためのイベント記録。`logs/`への出力・`PipelineMetrics`集計の両方の入力になる。

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class PipelineEvent:
    stage_name: str
    event_type: Literal["started", "completed", "failed", "skipped"]
    timestamp: datetime
    detail: str | None
```

- **不変条件**: `stage_name`は`PipelineStage`実装クラスの正式名（`DocumentAnalyzer`, `LayoutDetector`等）のいずれか、または`JobRunner`自身（オーケストレーション全体のイベント）。

## `PipelineException`

パイプライン内で発生する例外の基底クラス。[`python-contract.md`](python-contract.md#例外設計)の例外階層の一部。

```python
class PipelineException(Exception):
    """パイプライン実行中に発生した例外の基底クラス。"""

    def __init__(self, stage_name: str, context: PipelineContext, message: str) -> None: ...

    @property
    def stage_name(self) -> str: ...

    @property
    def context(self) -> PipelineContext: ...
```

- **設計方針**: 特定Stageの失敗は、そのPDF・そのレコードの処理のみを失敗させ、他のPDF・他のレコードの処理には波及させない（[ADR-0019](../adr/0019-workflow-orchestration.md)）。`JobRunner`は`PipelineException`を捕捉し、`Job.failed_count`を増分した上で処理を継続する。

## `PipelineMetrics`

`PipelineRunner`による1回の実行（1PDF・1レコード分）についての定量的なサマリ。`Job`（DB永続化される軽量なサマリ）より詳細な、実行時観測用の集計値。

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    elapsed_ms: float
    started_at: datetime
    finished_at: datetime
    succeeded: bool
    warning_count: int
    error_count: int
```

- **不変条件**: `finished_at >= started_at`。`elapsed_ms >= 0`。`warning_count >= 0`、`error_count >= 0`。`succeeded == (error_count == 0)`。
- **フィールド構成の経緯**: 本フィールド構成（`elapsed_ms` / `started_at` / `finished_at` / `succeeded` / `warning_count` / `error_count`）は、Phase2 Task3（Pipeline Skeleton Implementation）の実装指示に基づき確定した正式仕様である。設計フェーズ当初のドラフト（`stage_durations_ms: dict[str, float]` / `processed_count: int` / `failed_count: int` / `skipped_count: int`）から変更した経緯・理由は[ADR-0031](../adr/0031-pipeline-metrics-field-finalization.md)を参照。本ドキュメントが唯一の正式仕様（Single Source of Truth）であり、他ドキュメントは本節を参照する。
- **Stage別処理時間の扱い**: 旧ドラフトの`stage_durations_ms`が担っていた「Stage別の所要時間の内訳」は、`PipelineMetrics`が保持する集計値ではなく、`PipelineEvent`列（各Stageの`started`/`completed`イベントの`timestamp`差分）から導出する運用に変更した（[`docs/operations/observability.md`](../operations/observability.md#metrics)のMetrics節を参照）。
- **レコード件数集計の扱い**: 旧ドラフトの`processed_count`/`failed_count`/`skipped_count`（複数レコードにまたがる件数の内訳）は、`PipelineRunner`の1回の実行が1レコード分の処理であるという実装上の粒度（[`PipelineStage`](#pipelinestage)の`run()`は1入力→1出力の純粋な変換）とは異なる集約レベルの指標だったため、`PipelineMetrics`からは廃止した。複数レコードにまたがる集計は`Job.processed_count`/`Job.failed_count`（[`models.md`](models.md#job)）が担う。

---

## `JobRunner`との関係

`JobRunner`（[`interfaces.md`](interfaces.md#jobrunner)）は`pipeline/`パッケージの公開窓口であり、`PipelineContext`を生成し、6段階の`run()`を順に呼び出し、各段階の出力を次段階の入力として渡しながら、`PipelineEvent`を記録し、最終的に`PipelineResult`を返す。この一連の調整ロジックこそが`pipeline/`の責務であり、個々の`PipelineStage`実装は互いの存在を知らない（[`architecture-contract.md`](../architecture/architecture-contract.md)）。
