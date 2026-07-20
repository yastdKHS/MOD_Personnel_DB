# 0044. PipelineRunner / JobRunner Boundary

## ステータス
Accepted

## コンテキスト（Context）

Phase3 Task10-0（Architecture Review）は、Phase2で実装完了した中核パイプライン6段階（Document Analyzer→Layout Detector→Section Parser→Field Extractor→Normalizer→Validator）を統合する`PipelineRunner`（`src/mod_personnel_db/pipeline/runner.py`、Phase2 Task3で実装済み）と、未実装の`JobRunner`（[`docs/api/interfaces.md`](../api/interfaces.md#jobrunner)にProtocol定義のみ存在）の責務境界を検証した。

検証の結果、以下が判明した。

- **実装済み`PipelineRunner`はコード上既にクリーン**である。`repositories/`・`knowledge/`・`learning/`・`review/`・`export/`のいずれもimportせず、Stage生成（`Normalizer(knowledge, ...)`等のコンストラクタ注入）も`PipelineContext`生成も行わない。`run(context, job, initial_input)`は登録済みStage列を順に呼び出し、各Stageの出力を`object`型で不透明に次段へ渡すのみである。
- 一方、**設計文書側はこの層構造を反映していない**。`docs/api/pipeline.md`の「`JobRunner`との関係」節は「`JobRunner`が`PipelineContext`を生成し、6段階の`run()`を順に呼び出し…`PipelineResult`を返す」と述べており、これは実装済み`PipelineRunner.run()`が既に行っている調整ロジックとほぼ同一の記述であるにもかかわらず、`PipelineRunner`という語が`pipeline.md`・`docs/api/interfaces.md`・`docs/api/package-design.md`のいずれにも登場しない。
- `docs/api/dependency-rule.md`のMermaid図は`pipeline/`パッケージを単一ノードとして扱い、`repositories/`（抽象）・`knowledge/`・`learning/`への依存エッジを`pipeline/`パッケージ全体に対して許可している。これは`JobRunner`（未実装）が正当に必要とする依存だが、`PipelineRunner`（実装済み、これらに依存しない）にも同じ依存が許可されているかのように読める。
- `runner.py`自身のモジュールdocstringは「将来Task（JobRunner本実装）で本クラスをラップする形になる想定」と明記しており、実装側は当初から「JobRunner → PipelineRunner → PipelineStage」という層構造を意図していた。

このまま設計文書を確定させずにJobRunner実装（Phase3 Task10想定）に着手すると、`pipeline/`パッケージ内だからという理由で`PipelineRunner`自身（またはそれに近いモジュール）にRepository/Knowledge依存が混入するリスクがある。これはPhase2でTask7-0/Task8-0/Task9-0が発見した「設計文書と実装意図の乖離」と同種の問題であり、実装着手前にADRで確定する。

## 問題（Problem）

1. `PipelineRunner`（実装済み）と`JobRunner`（未実装、Protocol定義のみ）の責務境界が、どの設計文書にも明示的に記述されていない。
2. `docs/api/dependency-rule.md`の依存関係図は`pipeline/`を単一ノードとして扱い、`JobRunner`が必要とする依存（`repositories/`・`knowledge/`・`learning/`）と`PipelineRunner`が禁止される依存の区別がつかない。
3. `docs/architecture/architecture-contract.md`の12の分離保証に、`PipelineRunner`自身の非依存を保証する項目が存在しない。

## 決定（Decision）

### 1. `PipelineRunner`は純粋なStage実行機とする

`PipelineRunner`（`pipeline/`パッケージ内、実装済み）は以下の責務のみを持つ。

- 登録済み`PipelineStage`列を、構築時に与えられた順序のまま呼び出す。
- 各Stageの出力を次のStageの入力としてそのまま渡す（Artifact受け渡し）。
- `PipelineException`を捕捉し、`PipelineEvent`・`PipelineResult`として記録する。

`PipelineRunner`は以下を**行わない**（Phase2 Task3実装時点で既に満たされており、本ADRはこれを正式な設計として確定する）。

- **Stage生成を行わない**: `Normalizer(knowledge, ...)`等のインスタンス化・コンストラクタ注入は`PipelineRunner`の責務外。呼び出し元（`JobRunner`）が生成済みStageを`PipelineBuilder.add_stage()`経由で登録する。
- **永続化を行わない**: `repositories/`（抽象・具象いずれも）への依存を持たない。
- **`PipelineContext`を生成しない**: `run()`は`context: PipelineContext`を引数として受け取るのみ。
- **`Repository` / `Knowledge` / `Learning` / `Review` / `Export`のいずれにも依存しない**。

### 2. `JobRunner`は`PipelineRunner`の呼び出し元とする

`JobRunner`（[`docs/api/interfaces.md`](../api/interfaces.md#jobrunner)、`pipeline/`パッケージ内、未実装）は以下の責務を持つ。

- **`PipelineContext`生成責務**: 1PDF・1レコード分の実行ごとに`PipelineContext`を構築する。
- **Stage生成責務**: `KnowledgeSnapshot`・`ValidationRuleSet`等を取得し、各Stage（`Normalizer`, `Validator`等）をコンストラクタ注入で構築し、`PipelineBuilder`経由で`PipelineRunner`へ登録する。
- **PipelineRunner呼び出し責務**: 構築した`PipelineRunner`の`run()`を呼び出す。
- **Repository永続化責務**: `PipelineRunner`が返す`PipelineResult`（および中間で得られる各Stage出力）を`repositories/`（抽象）経由で永続化する。
- **`KnowledgeSnapshot` / `ValidationRuleSet`取得責務**: `knowledge/`から取得し、対応するStageへ注入する。
- **Learning記録責務**: 検証NG等の情報を`learning/`へ記録する（呼び出し元が担う、[ADR-0013](0013-learning-dataset-not-correction-log.md)）。

`JobRunner`は`review/`・`export/`には直接依存しない（[`docs/api/dependency-rule.md`](../api/dependency-rule.md)の既存方針どおり、`services/`が`pipeline/`・`review/`・`export/`を束ねる）。

### 3. 両者は同一パッケージ（`pipeline/`）内の別モジュールとして共存する

パッケージ分割は行わない。`PipelineRunner`は`pipeline/runner.py`（既存）、`JobRunner`は`pipeline/job_runner.py`（想定、未実装）という別モジュールとして共存させる。これは以下の理由による。

- `docs/api/package-design.md`が既に`pipeline/`を「中核パイプライン6段階の実行を調整する」単一パッケージとして位置づけており、パッケージ分割は既存の依存関係図（`document/`〜`validators/`, `repositories/`, `knowledge/`, `learning/`との関係）を大きく書き換える破壊的変更になる。
- モジュール単位での責務分離は、`architecture-contract.md`の他の保証（例: 保証5「Normalizerは正規表現を持たない」）が「パッケージ全体ではなくコード内容に対する規律」として運用されているのと同型であり、本ADRが新設する保証13（下記）とコードレビュー慣行によって担保する。

## Architecture Contract

以下を[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証13として追加する（詳細は同ファイルを正とする）。

> **保証13: PipelineRunnerはRepository・Knowledge・Learning・Review・Exportを知らない。**
> `pipeline/`パッケージは`repositories/`・`knowledge/`・`learning/`への依存を許可されている（`JobRunner`が必要とするため）が、`PipelineRunner`（`pipeline/runner.py`）自身のコードはこれらのいずれもimportしない。この区別は`pipeline/`パッケージ内のモジュール単位の規律であり、パッケージレベルの依存関係図（[`dependency-rule.md`](../api/dependency-rule.md)）だけでは表現しきれないため、本保証で明文化する。

## 検討した代替案

- **`PipelineRunner`と`JobRunner`を別パッケージに分割する（例: `pipeline/`と`jobs/`）**: 依存関係図・`package-design.md`の全面的な書き換えを要する破壊的変更であり、Phase2で確立済みの`pipeline/`パッケージの位置づけ（`document/`〜`validators/`を束ねる中核パイプライン実行パッケージ）を覆す。現時点で具体的な分割の必要性（例: 独立したデプロイ単位にする要求）がないため、YAGNI（[ADR-0014](0014-development-discipline.md)）に照らし採用しなかった。将来、実際にパッケージ分割の必要性が生じた場合は新規ADRで検討する。
- **`docs/api/dependency-rule.md`のMermaid図で`pipeline/`ノードを`PipelineRunner`ノードと`JobRunner`ノードに分割する**: パッケージ単位の依存関係図の粒度をモジュール単位まで細分化することになり、他のパッケージ（`repositories/`, `knowledge/`等）には適用していない粒度を`pipeline/`にだけ適用する非一貫性を生む。図のノードはパッケージ単位のまま維持し、注記による補足に留める（下記Migration参照）。

## 結果（トレードオフ, Consequences）

- `PipelineRunner`（既存実装）はいずれの決定にも既に適合しており、コード変更は不要。
- `JobRunner`実装タスク（Phase3 Task10想定）は、本ADRが定める責務（Context生成・Stage生成・永続化・Knowledge取得・Learning記録）に従って`pipeline/job_runner.py`を新設する。
- `docs/api/dependency-rule.md`のMermaid図における`pipeline/`ノードの粒度は変更しない（モジュール単位への分割は見送り）。パッケージレベルの依存許可（`pipeline/` → `repositories/`, `knowledge/`, `learning/`）は`JobRunner`の必要から生じるものであり、`PipelineRunner`自身への適用は保証13（コードレビュー慣行）で防止する。

## Migration

1. `docs/architecture/architecture-contract.md`に保証13を追加する（本ADRの内容をそのまま反映）。
2. `docs/api/pipeline.md`の「`JobRunner`との関係」節を更新し、「`JobRunner` → `PipelineRunner` → `PipelineStage`」という層構造、および既存実装（`PipelineRunner`/`PipelineBuilder`/`PipelineFactory`）への言及を追加する。
3. `docs/api/package-design.md`の`pipeline/`節を更新し、`PipelineRunner`と`JobRunner`の責務を分離して記載する。
4. `docs/api/dependency-rule.md`に、`pipeline/`ノードの依存（`repositories/`・`knowledge/`・`learning/`）が`JobRunner`の責務であり`PipelineRunner`自身の責務ではないことを示す注記を追加する（ノード分割は行わない）。
5. コード変更は行わない（`src/mod_personnel_db/pipeline/runner.py`は本ADRの決定に既に適合している）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証13を新設 |
| [`docs/api/pipeline.md`](../api/pipeline.md) | 「`JobRunner`との関係」節に`PipelineRunner`層を追記 |
| [`docs/api/package-design.md`](../api/package-design.md) | `pipeline/`節をPipelineRunner/JobRunnerの責務分離で更新 |
| [`docs/api/dependency-rule.md`](../api/dependency-rule.md) | `pipeline/`ノードの依存主体に関する注記を追加 |

## 関連ADR
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0013](0013-learning-dataset-not-correction-log.md) — Learning Dataset方針。JobRunnerのLearning記録責務の前提。
- [ADR-0014](0014-development-discipline.md) — 開発規律。パッケージ分割を見送るYAGNI判断の根拠。
- [ADR-0019](0019-workflow-orchestration.md) — 実行オーケストレーション戦略。JobRunnerがPDF単位で失敗を独立させる方針の前提。
- [ADR-0037](0037-layout-detector-produces-layout-artifact.md) — 単一入力`run()`パターンの先例。
- [ADR-0040](0040-normalizer-produces-normalization-result.md) — コンストラクタ注入パターンの先例。JobRunnerがStage生成時に適用する。
- [ADR-0041](0041-validator-constructor-injects-validation-rule-set.md) — 同上。

（本ADRはADR-0011/0013/0014/0019/0037/0040/0041のいずれの核心決定も変更しないため、Supersededにはしない。）
