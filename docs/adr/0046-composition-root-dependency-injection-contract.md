# 0046. Composition Root（CLI）の依存注入契約

## ステータス
Accepted

## コンテキスト（Context）

Phase3 Task11-0（Architecture Review）は、Task10で完成した中核パイプライン（`PipelineRunner`, `JobRunner`, ADR-0044/0045）を実際に起動するComposition Rootの設計を検証した。

`docs/api/package-design.md`・`docs/api/dependency-rule.md`は、Phase2 Task8-1の時点で既に`cli/`をComposition Root（「誰も`repositories/sqlite/`を直接importしない」原則の唯一の例外）と定めていたが、この決定は`JobRunner`の実装（Task10-1/10-4）より前に確立されたものであり、以下の点で実装済みのコードと文書の記述にドリフトが生じていることが判明した。

1. `dependency-rule.md`の合成ルート節は「`UnitOfWork`を組み立てて`pipeline/`...に渡す」と述べるが、実装済み`JobRunner.__init__`（`pipeline/job_runner.py`）は`UnitOfWork`（`repositories.md`が定める8リポジトリ集約Protocol）を受け取らず、`JobRunnerRepositories`（`pdfs`/`jobs`/`candidates`の3フィールドのみを持つ狭いdataclass）と、個別の`KnowledgeService`・`LearningService`・`ParserVersionId`・`layout_definitions`を受け取る。
2. Review（ADR-0021）は人手・対話的なCLI操作として設計されており、`run_pending()`実行や将来のExportと同一プロセス内で自動的に連続実行される性質のものではないが、この点はどの設計文書にも明記されていなかった。
3. `KnowledgeService`/`LearningService`の具象実装、および`repositories/sqlite/`の各具象実装を、Composition Root以外の箇所（`services/`, `pipeline/`, `repositories/`自身等）が生成してはならないという制約が、既存の「`cli/`のみが`repositories/sqlite/`をimportできる」という依存関係グラフ上の制約からは自明であるものの、`KnowledgeService`/`LearningService`の**具象実装**についても同じ制約が及ぶことは明文化されていなかった。

Task11-0は複数の代替案（CLI直接生成・Composition Root分離・Service Locator・DI Container・Factory集約）を比較し、既存の「`cli/`=合成ルート」という決定を維持しつつ、上記のドリフトを解消する形でComposition Rootの依存注入契約を確定することを推奨した。本ADRはその結論を正式決定する。

## 決定（Decision）

### 1. Composition Rootは`cli/`配下のみとする

`config/`・`services/`・`pipeline/`・`repositories/`のいずれも、具象実装（`repositories/sqlite/`の各クラス、`KnowledgeService`/`LearningService`の具象実装）を生成しない。生成（インスタンス化）は`cli/`配下のコードのみが行う。

- `config/`は設定値の提供のみを行い、いかなる具象実装も参照しない（既存決定、`dependency-rule.md`）。
- `services/`（Scheduler等）は、生成済みの依存を受け取って利用する側であり、自ら`repositories/sqlite/`や`KnowledgeService`/`LearningService`の具象実装を生成しない。
- `pipeline/`（`PipelineRunner`/`JobRunner`）は、ADR-0044が定めるとおり、`JobRunner`もStage・Contextを生成する責務は持つが、Repository・KnowledgeService・LearningServiceの**具象実装**を生成する責務は持たない（`JobRunner`はこれらをコンストラクタ注入で受け取るのみ）。
- `repositories/`（抽象）は、Protocolの定義のみを行い、いかなる具象クラスも含まない（既存決定）。

### 2. Composition Rootの責務チェーン

`cli/`配下のComposition Rootは、以下の順序で依存を構築する。

1. **Repository具象生成**: `config/`から接続情報を取得し、`repositories/sqlite/`の各具象クラス（`SqlitePDFRepository`, `SqliteJobRepository`, `SqliteCandidateRepository`等）を構築する。
2. **KnowledgeService生成**: `KnowledgeRepository`（前段で生成した具象）等を用いて、`KnowledgeService`の具象実装を構築する。
3. **LearningService生成**: `LearningRepository`（前段で生成した具象）等を用いて、`LearningService`の具象実装を構築する。
4. **JobRunner生成**: 前段で生成した`KnowledgeService`・`LearningService`・Repository群を、後述の注入契約（決定3）に従い`JobRunner`へ注入して構築する。
5. **CLI Command生成**: 構築済みの`JobRunner`等を、各CLIサブコマンド（`run`, `review`, `export`等）のハンドラへ渡す。

この順序は依存の前後関係（`KnowledgeService`/`LearningService`は対応するRepositoryを必要とし、`JobRunner`は`KnowledgeService`/`LearningService`を必要とする）から導かれる自然な順序であり、実装時の生成コードもこの順序に従う。

### 3. JobRunnerへの注入契約

`JobRunner`のコンストラクタ（`pipeline/job_runner.py`、Task10-1/10-4で確定済み、本ADRはこの既存シグネチャを変更しない）が受け取る依存は、以下の個別の値・Protocol型のみである。

- `repositories: JobRunnerRepositories`（`pdfs: PDFRepository`, `jobs: JobRepository`, `candidates: CandidateRepository`を束ねるdataclass）
- `knowledge: KnowledgeService`
- `learning: LearningService`
- `parser_version_id: ParserVersionId`
- `layout_definitions: tuple[LayoutDefinition, ...]`

**`UnitOfWork`（`repositories.md`が定める8リポジトリ集約Protocol）は`JobRunner`へ注入しない。** `UnitOfWork`は、複数Repositoryにまたがる原子性が必要な操作（例: `ReviewService.promote_to_gold`、`repositories.md`参照）のための抽象であり、`JobRunner`はそのような操作を行わないため、必要とする3つのRepository（`pdfs`/`jobs`/`candidates`）のみを`JobRunnerRepositories`として個別に受け取る設計が、実際の依存関係を過不足なく表現している。

### 4. Review・Export・run_pendingは独立したCLIエントリポイントとする

`run_pending()`（パイプライン実行、ADR-0019のスケジュール実行が主な起動契機）・Review（ADR-0021の対話的CLI操作）・Export（`ExportService.generate()`）は、それぞれ独立したCLIサブコマンド（エントリポイント）として提供する。Composition Rootがこれらを1つのプロセス内で自動的に直列実行することはない。

理由は、Reviewが人手を介する対話的操作である（ADR-0021）ため、`run_pending()`の完了を待って自動的に開始できる性質のものではないこと、また、Export・Review・パイプライン実行はそれぞれ異なる契機（スケジュール実行、人手によるレビュー作業、公開タイミング）で起動される独立した関心事であるためである。

### 5. Composition Root以外からの具象生成を禁止する

`repositories/sqlite/`の各クラス、`KnowledgeService`の具象実装、`LearningService`の具象実装は、`cli/`配下のComposition Root以外のいかなる箇所からも生成（インスタンス化）してはならない。これは既存の依存関係グラフ上の制約（`repositories/sqlite/`は`cli/`以外からimportされない）の自然な拡張であり、`KnowledgeService`/`LearningService`の具象実装についても同じ制約が及ぶことを本ADRで明文化する。

## Architecture Contract

以下を[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)の保証15として追加する（詳細は同ファイルを正とする）。

> **保証15: 依存生成責務はComposition Root（`cli/`）に一本化される。** `repositories/sqlite/`の各具象クラス、`KnowledgeService`の具象実装、`LearningService`の具象実装は、`cli/`配下のComposition Root以外のいかなる箇所からも生成されない。

## 検討した代替案

Task11-0で比較した代替案（詳細はTask11-0 Architecture Review Reportを参照）。

- **CLIが直接JobRunnerを生成する案**: コマンドごとに生成ロジックが重複し、将来のGUI/API対応時に再利用できないため不採用。
- **Service Locator案**: グローバル可変状態を持ち込み、`dependency-rule.md`が徹底する明示的な依存関係グラフという設計方針と相容れないため不採用。
- **DI Containerライブラリ導入案**: 新規外部ライブラリへの依存を要し、現状の規模に見合わない複雑さを持ち込むため不採用（YAGNI）。
- **Factory集約案**: 単体の対案としてではなく、Composition Root内部の実装手段として採用可能なため、独立した案としては扱わない。

いずれの代替案も、既存の「`cli/`=合成ルート」という決定（Phase2 Task8-1）を維持する結論を変えるものではなかった。

## 結果（トレードオフ, Consequences）

- `dependency-rule.md`の合成ルート節・Mermaid図における「`UnitOfWorkとして`pipeline/`へ注入」という記述は、`JobRunner`の実装済みシグネチャと一致するよう修正が必要になる（Migration参照）。`UnitOfWork`自体は`repositories/`パッケージの正式な抽象として引き続き有効であり、将来`review/`・`export/`等が複数Repositoryにまたがる原子性を必要とする場合に利用されうる。
- Composition Rootの実装（Task11-2以降を想定）は、本ADRが定める生成順序・注入契約に従う。
- `run_pending()`/Review/Exportが独立エントリポイントであることを明文化したことで、将来のCLIコマンド設計（`cli run`, `cli review`, `cli export`等のサブコマンド分割）の指針が確定する。

## Migration

1. `docs/architecture/architecture-contract.md`に保証15を追加する。
2. `docs/api/package-design.md`の`cli/`節を、`JobRunner`への個別注入（`UnitOfWork`ではない）を反映する形に修正する。
3. `docs/api/dependency-rule.md`の合成ルート節・Mermaid図を、`pipeline/`（`JobRunner`）への注入が`UnitOfWork`ではなく個別の型であることを反映する形に修正する。
4. `docs/api/interfaces.md`の`JobRunner`節に、本ADRへの参照とDI契約の要約を追記する。
5. コード変更は行わない（`src/mod_personnel_db/pipeline/job_runner.py`は本ADRの決定に既に適合している）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 保証15を新設 |
| [`docs/api/package-design.md`](../api/package-design.md) | `cli/`節をJobRunnerへの個別注入契約に整合させる |
| [`docs/api/dependency-rule.md`](../api/dependency-rule.md) | 合成ルート節・Mermaid図の`pipeline/`向け注入記述を修正 |
| [`docs/api/interfaces.md`](../api/interfaces.md) | `JobRunner`節にDI契約の参照を追記 |

## 関連ADR
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。本ADRはComposition Rootの配線契約のみを扱い、パイプライン構成自体は変更しない。
- [ADR-0019](0019-workflow-orchestration.md) — Workflow Orchestration。`run_pending()`の起動契機（スケジュール実行）の前提。
- [ADR-0021](0021-review-ui-strategy.md) — Review UI戦略。ReviewがCLIの対話的操作であり、自動直列実行の対象でないことの根拠。
- [ADR-0044](0044-pipelinerunner-jobrunner-boundary.md) — PipelineRunner / JobRunner Boundary。`JobRunner`のStage生成・Repository永続化責務の前提。
- [ADR-0045](0045-job-runner-aggregate-artifact-coordinator.md) — JobRunnerによる集約Artifact展開モデル。`JobRunnerRepositories`等の実際のコンストラクタ形状の根拠。

（本ADRはADR-0011/0019/0021/0044/0045のいずれの核心決定も変更しないため、Supersededにはしない。）
