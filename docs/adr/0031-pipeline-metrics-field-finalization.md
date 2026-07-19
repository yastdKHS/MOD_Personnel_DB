# 0031. PipelineMetricsのフィールド構成を確定する

## ステータス
Accepted

## コンテキスト

[`docs/api/pipeline.md`](../api/pipeline.md#pipelinemetrics)は、設計フェーズ（Task8-5）当初、`PipelineMetrics`を以下の4フィールドで定義していた。

```python
@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    stage_durations_ms: dict[str, float]
    processed_count: int
    failed_count: int
    skipped_count: int
```

Phase2 Task3（Pipeline Skeleton Implementation）の実装指示は、`PipelineMetrics`の責務を「経過時間・開始時刻・終了時刻・成功フラグ・警告件数・エラー件数の6項目を保持するだけ」と明示的に定めており、これは上記ドラフトと異なるフィールド構成だった。Task3では実装指示を優先して以下の6フィールドで実装し（`src/mod_personnel_db/pipeline/metrics.py`）、乖離をTask3完了報告のTODOとして明記した。

```python
@dataclass(frozen=True, slots=True)
class PipelineMetrics:
    elapsed_ms: float
    started_at: datetime
    finished_at: datetime
    succeeded: bool
    warning_count: int
    error_count: int
```

Phase2 Task4-0（Design Synchronization）で、`docs/api/pipeline.md`・`src/mod_personnel_db/pipeline/metrics.py`・[`docs/operations/observability.md`](../operations/observability.md)・[Architecture Review Package](../architecture-review-package.md)を確認したところ、正式仕様が実装（6項目）と設計ドラフト（4項目）の2箇所に分かれて存在する状態であり、Single Source of Truthの原則（`CLAUDE.md`「正しさより先に、間違いに気づける設計」・`docs/constitution.md`）に反していることが判明した。

なお、`docs/api/pipeline.md`の4項目ドラフトは、いずれのADRによっても正式決定されたものではなかった（設計フェーズのドキュメント作成時にADRを起票せず記述されていた）。

## 決定

- `PipelineMetrics`の正式仕様を、**Phase2 Task3で実装した6フィールド版**（`elapsed_ms` / `started_at` / `finished_at` / `succeeded` / `warning_count` / `error_count`）に統一する。設計ドラフトの4フィールド版は廃止する。
- 単一の正式仕様（Single Source of Truth）は[`docs/api/pipeline.md`](../api/pipeline.md#pipelinemetrics)とし、`src/mod_personnel_db/pipeline/metrics.py`の実装はこれと完全に一致させる（既に一致しているため実装コードの変更はない）。
- 旧ドラフトが担っていた2つの観測要件は、以下のように別の型・別の運用に委譲する。
  - **Stage別処理時間**（旧`stage_durations_ms`）: `PipelineMetrics`が保持する集計値としては廃止し、`PipelineEvent`列（各Stageの`started`/`completed`イベントの`timestamp`差分）から導出する運用とする（[`docs/operations/observability.md`](../operations/observability.md#metrics)を更新）。
  - **レコード件数の内訳**（旧`processed_count` / `failed_count` / `skipped_count`）: `PipelineRunner`の1回の実行は1レコード分の処理であり、複数レコードにまたがる集計とは粒度が異なるため`PipelineMetrics`からは廃止する。複数レコードにまたがる集計は既存の`Job.processed_count` / `Job.failed_count`（[`docs/api/models.md`](../api/models.md#job)）が引き続き担う。
- 本ADRと同一PRで、[`docs/api/pipeline.md`](../api/pipeline.md#pipelinemetrics)・[`docs/operations/observability.md`](../operations/observability.md)・[`docs/adr/index.md`](index.md)・[`docs/adr/dependency-map.md`](dependency-map.md)・[`docs/adr/README.md`](README.md)を同期更新し、変更を[`CHANGELOG.md`](../../CHANGELOG.md)に記録する（[ADR-0014](0014-development-discipline.md)の1PR1責務の例外として、「同じ決定の二重表現の同期」は1つの責務とみなす）。

## 検討した代替案

- **実装（6フィールド版）を設計ドラフト（4フィールド版）に合わせて書き戻す**: `stage_durations_ms`のようなStage別内訳を`PipelineMetrics`自身に持たせる設計は、`PipelineRunner`が実行のたびに`dict[str, float]`を構築する責務を負うことになり、[`docs/api/pipeline.md`](../api/pipeline.md#pipelinestage)が定める「各Stageは`run()`のみを公開する純粋な変換」という設計原則との整合は取れるものの、`PipelineMetrics`自体の責務（Phase2 Task3で「集計値の保持のみ」と定義済み）を超える集計ロジックをRunnerに追加する必要が生じる。また、`processed_count`等のレコード単位の集計は、実装時点で「1回の実行=1レコード」という粒度で確定しており、これを`PipelineMetrics`に持たせると`Job`側の同種フィールドと責務が重複する。以上より、実装を書き戻す案は採用しなかった。
- **両方のフィールド構成を併存させる（`PipelineMetrics`を拡張して10フィールドにする）**: Single Source of Truthの原則に反し、どちらが正式かが再び曖昧になるため採用しなかった。

## 結果（トレードオフ）

- `docs/api/pipeline.md`と実装が完全に一致し、Design Synchronizationの目的（Single Source of Truthの回復）を達成する。
- Stage別処理時間は、以後`PipelineMetrics`の型定義からは直接読み取れず、`PipelineEvent`列から都度導出する実装（ログ集計・ダッシュボード生成側の責務）が必要になる。この導出ロジックは本ADRの時点では未実装であり、将来の観測基盤実装時のTODOとして残る。
- 本ADRは`docs/api/pipeline.md`が設計フェーズ時点でADRなしに記述されていたフィールド定義を、実装経験を踏まえて正式にADR管理下に置く最初の事例である。今後`pipeline.md`の型定義を変更する場合は、本ADRと同様にADRを起票してから変更する。

## 関連ADR
- [ADR-0006](0006-pipeline-provenance.md) — パイプライン段階分割と来歴管理。`PipelineEvent`による来歴記録の前提。
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。Stage別処理時間の観測対象。
- [ADR-0014](0014-development-discipline.md) — 開発規律。Single Source of Truthの同期規律の根拠。
- [ADR-0019](0019-workflow-orchestration.md) — 実行オーケストレーション戦略。`Job`集計フィールドとの責務分担の前提。
