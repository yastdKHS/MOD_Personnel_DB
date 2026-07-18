# MOD Personnel DB（防衛省人事発令データベース）

> ステータス: **設計完了（Design Freeze）・実装未着手**。10年以上の運用に耐える設計corpus（ディレクトリ構成・規約・29本のADR・`docs/`配下の全設計文書）が[`docs/design-freeze.md`](docs/design-freeze.md)のレビューを経て確定しました。実装コードはまだ含まれていません。次のマイルストーンは実装フェーズの開始です。

## これは何か

防衛省・自衛隊が公表する人事発令（辞令）PDFを継続的に収集し、構造化された人事データベースとして整備・公開するための長期運用プロジェクトです。

- **入力**: 防衛省が公表する人事発令PDF（既に一般公開されている公務上の情報）
- **出力**: 検索・分析・再利用可能な構造化データ（人物・階級・補職・組織・発令日等の関係を持つDB）
- **時間軸**: 単発のスクリプトではなく、**10年以上にわたりPDFフォーマットの変化・組織改編・担当者交代を乗り越えて保守され続けるシステム**を前提に設計する

このプロジェクトのゴールは「Pythonコードを書くこと」ではなく、「変化に耐え、間違いに気づける、引き継ぎ可能なデータ基盤を作ること」です。

## 設計思想（詳細は `docs/` を参照）

1. **PDFフォーマットは変わる前提で設計する** — パースロジックをハードコードせず、`layouts/` にレイアウト定義を外出しする（[ADR-0003](docs/adr/0003-layout-definition-strategy.md)）。
2. **正しさより先に、間違いに気づける仕組みを作る** — ゴールデンファイルテスト・来歴（provenance）管理・検証ステージを必須にする。
3. **枯れた技術を選ぶ** — 流行より「10年後も動く」を優先する（[ADR-0001](docs/adr/0001-python-packaging.md), [ADR-0004](docs/adr/0004-sqlite-as-datastore.md)）。
4. **人が入れ替わっても回る** — ドキュメント・ADR・CODEOWNERS・CONTRIBUTING.mdで属人化を防ぐ。
5. **公開データの節度ある取り扱い** — 対象は公務としての公表情報に限定し、目的外利用・過剰な個人情報付与を行わない（[ADR-0008](docs/adr/0008-data-ethics-policy.md)）。
6. **中核パイプラインは固定し、変化はデータで吸収する** — Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator の6段階を変更禁止とし、新様式・新表記への対応は `layouts/` / `knowledge/` の追加のみで行う（[ADR-0011](docs/adr/0011-fixed-core-pipeline.md)）。
7. **例外処理より先にデータ追加を検討する** — 未知パターンへの対応は Knowledge Base追加 > Layout追加 > 例外処理、の優先順位で行う（[ADR-0012](docs/adr/0012-error-handling-priority-order.md)）。
8. **誤りは学習資産として蓄積する** — 修正情報は単なるログではなく、システム改善に還元できるLearning Datasetとして設計する（[ADR-0013](docs/adr/0013-learning-dataset-not-correction-log.md)）。
9. **実装速度より設計品質を優先する** — 1PR1責務、大きな関数の禁止など、開発規律を明文化し機械的に強制する（[ADR-0014](docs/adr/0014-development-discipline.md)）。

## リポジトリ構成

| パス | 責務 |
|---|---|
| `README.md` | プロジェクト概要（本ファイル） |
| `CLAUDE.md` | Claude Code（AIコーディングエージェント）向けの作業規約 |
| `AGENTS.md` | 任意のAIエージェント向けの汎用運用規約 |
| `CONTRIBUTING.md` | 人間の開発者向けの開発フロー・規約 |
| `CODEOWNERS` | パスごとのレビュー担当者定義 |
| `.gitignore` | Git管理除外ルール |
| `pyproject.toml` | Pythonプロジェクトの唯一の設定源（依存関係・ビルド・lint・型・テスト設定） |
| `.pre-commit-config.yaml` | コミット前静的チェックの定義 |
| `.github/` | CI/CDワークフロー・Issue/PRテンプレート |
| `docs/` | アーキテクチャ・データモデル・ADR・運用手順書 |
| `knowledge/` | 階級名・組織名・表記ゆれ等のドメイン知識（人手管理データ） |
| `layouts/` | PDFフォーマット（時代・様式）ごとのレイアウト定義 |
| `src/` | 本体実装（Pythonパッケージ） |
| `tests/` | テストスイート（unit / integration / golden） |
| `scripts/` | 定型化されていない運用・保守スクリプト |
| `sample_pdfs/` | テスト用の代表的なサンプルPDF |
| `sample_outputs/` | `sample_pdfs/` に対応する期待出力（ゴールデンファイル） |
| `logs/` | 実行時ログの出力先（Git管理対象外） |
| `tmp/` | 一時作業領域（Git管理対象外） |

各ディレクトリの詳細な責務は、そのディレクトリ直下の `README.md`、および [`docs/architecture.md`](docs/architecture.md) を参照してください。

## ドキュメント目次

- [`docs/constitution.md`](docs/constitution.md) — **Project Constitution**（プロジェクト憲法）。ADR・Architecture Contractを含む全設計文書の最上位に位置する統治文書
- [`docs/design-freeze.md`](docs/design-freeze.md) — **Design Freeze Review**。全設計領域の横断レビューと設計完了宣言。実装フェーズへ進む前に最初に読むべき全体像
- [`docs/implementation.md`](docs/implementation.md) — **Implementation Guide**。実装フェーズの最上位ガイドライン（Constitution → ADR → Architecture Contract → Implementation Guideの順で従う）
- [`docs/coding-style.md`](docs/coding-style.md) — Coding Style Guide（命名規則・関数長・型ヒント方針・構文選択等）
- [`docs/testing/test-policy.md`](docs/testing/test-policy.md) — Test Policy（Unit/Integration/Golden/Regression/Performance/Acceptance/Benchmark/Mutation Testの定義）
- [`docs/parser-guidelines.md`](docs/parser-guidelines.md) — Parser Development Guidelines（本プロジェクト専用のParser開発規約）
- [`docs/implementation-checklist.md`](docs/implementation-checklist.md) — Implementation Checklist（実装開始前チェックリスト）
- [`docs/developer-workflow.md`](docs/developer-workflow.md) — Developer Workflow（Issue作成からDeploymentまでのフロー、Mermaid可視化）
- [`docs/architecture.md`](docs/architecture.md) — システム全体のパイプライン設計
- [`docs/configuration.md`](docs/configuration.md) — Configuration Architecture（Environment/Pydantic Settings/Secret管理/Validation Rule/設定Version/Migration/Hot Reload可否）
- [`docs/security.md`](docs/security.md) — Security Architecture（Threat Model/Secret/Supply Chain/GitHub Actions/Dependency/JSON改ざん/FTP/Checksum・Hash・署名/Audit Log/最小権限/Security Review）
- [`docs/architecture/learning_dataset.md`](docs/architecture/learning_dataset.md) — Learning Dataset設計（フィールド仕様・ライフサイクル）
- [`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md) — Architecture Contract（コンポーネント間の分離保証）
- [`docs/data_model.md`](docs/data_model.md) — データモデル（概念設計）
- [`docs/database/schema.md`](docs/database/schema.md) — SQLite物理スキーマ（ER図・テーブル定義・Migration方針）
- [`docs/database/json_schema.md`](docs/database/json_schema.md) — 公開JSON仕様（JSON Schema Draft 2020-12）
- [`docs/knowledge/schema.md`](docs/knowledge/schema.md) — Knowledge Baseスキーマ（8カテゴリのYAML定義）
- [`docs/api/`](docs/api/) — Interface & Package設計（パッケージ構成・公開API・Repository Pattern・モデル・Pipeline Interface・依存ルール・コーディング規約）
- [`docs/review/`](docs/review/) — Review Domain（ライフサイクル・ドメインモデル・ポリシー・キュー・メトリクス）
- [`docs/workflow/`](docs/workflow/) — Workflow State Machine（Queued〜Archivedのライフサイクル）
- [`docs/operations/observability.md`](docs/operations/observability.md) — Observability設計（Logging/Metrics/Tracing/Health Check/Alert/Dashboard/SLO/SLI/Error Budget/OpenTelemetry対応方針）
- [`docs/operations/release.md`](docs/operations/release.md) — 運用設計（Release Flow/Rollback/Parser Upgrade/Knowledge Upgrade/Migration/Backfill/Recovery/Backup/Disaster Recovery/Maintenance Window）
- [`docs/glossary.md`](docs/glossary.md) — ドメイン用語集
- [`docs/adr/`](docs/adr/) — Architecture Decision Records
- [`docs/operations/`](docs/operations/) — 運用手順書（Runbook）
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開発への参加方法
- [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) — AIエージェント運用規約

## クイックスタート

実装が存在しないため、現時点では実行手順はありません。実装開始後、本セクションにセットアップ手順（`pip install -e .[dev]`、`pre-commit install`、`pytest` 等）を追記します。

## データの出典と利用方針

本プロジェクトが扱うのは、防衛省が公務として一般に公表した人事発令情報に限られます。取り扱い方針の詳細は [ADR-0008](docs/adr/0008-data-ethics-policy.md) を参照してください。

## ライセンス

未定（実装開始前に選定し、本セクションに明記する）。
