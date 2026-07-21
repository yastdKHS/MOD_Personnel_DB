# MOD Personnel DB（防衛省人事発令データベース）

> ステータス: **実装フェーズ（Phase5、リリース準備中）**。10年以上の運用に耐える設計corpus（ディレクトリ構成・規約・46本のADR・`docs/`配下の全設計文書）が[`docs/design-freeze.md`](docs/design-freeze.md)のレビューを経て確定し、[`docs/implementation.md`](docs/implementation.md)以下のImplementation Standardsに従って実装した。現時点で、中核パイプライン6段階（Document Analyzer〜Validator）・Repository層（SQLite実装）・JobRunner（Coordinator）・KnowledgeService/LearningService/ReviewService/ExportService・Composition Root（`cli/`）・CLIエントリポイントが実装済みである。詳細な実装状況の監査結果は[`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md)を参照。

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

## アーキテクチャ概要

中核パイプラインは6段階に固定されている（[ADR-0011](docs/adr/0011-fixed-core-pipeline.md)）。各段階は`run()`のみを公開する純粋な変換ステージであり、互いの存在・Repository・Knowledge/Learningサービスを知らない（[Architecture Contract](docs/architecture/architecture-contract.md)の分離保証）。

```
Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator
```

この中核パイプラインの外側に、以下のレイヤーが存在する。

- **`pipeline/`（`JobRunner`）**: 中核6段階を1PDF・1セクション・1レコード単位で反復呼び出しし、`PipelineContext`生成・Repository永続化・Learning記録を担うCoordinator（[ADR-0044](docs/adr/0044-pipelinerunner-jobrunner-boundary.md), [ADR-0045](docs/adr/0045-job-runner-aggregate-artifact-coordinator.md)）。
- **`repositories/`**: 永続化の抽象契約（Protocol）と、そのSQLite実装（`repositories/sqlite/`）。8種のRepository Protocolを持つ。
- **`knowledge/`・`learning/`**: ドメイン知識（階級名・組織名の表記ゆれ等）とLearning Dataset（誤りの学習資産化、[ADR-0013](docs/adr/0013-learning-dataset-not-correction-log.md)）を管理するサービス。
- **`review/`・`export/`**: 人手レビューとGold Database読み出しを担うサービス。現時点の実装は、それぞれLearning Dataset固有のレビューとGold Database読み出しに責務を限定した狭い契約であり、[`docs/api/review.md`](docs/api/review.md)・[`docs/api/interfaces.md`](docs/api/interfaces.md)が定めるより広範な設計とは異なる（詳細は[`docs/api/package-design.md`](docs/api/package-design.md)の`review/`・`export/`節を参照）。
- **`cli/`（Composition Root）**: 上記すべての具象実装を組み立てる唯一の合成ルート（[ADR-0046](docs/adr/0046-composition-root-dependency-injection-contract.md)）であり、かつCLIエントリポイントを兼ねる。

パッケージ間の依存方向は[`docs/api/dependency-rule.md`](docs/api/dependency-rule.md)が定め、各パッケージの責務・実装状況は[`docs/api/package-design.md`](docs/api/package-design.md)を正とする。`config/`・`features/`・`ftp/`・`fetch/`・`services/`は設計のみで未実装である。

## インストール方法

Python 3.13を対象とする（[ADR-0042](docs/adr/0042-python-version-target-realignment.md)）。標準の`pip`でインストールできる状態を維持する（[ADR-0001](docs/adr/0001-python-packaging.md)、[uv](https://docs.astral.sh/uv/)等の高速ツールは任意選択）。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## CLI使用方法

CLIエントリポイントは`python -m mod_personnel_db.cli`である（`src/mod_personnel_db/cli/__main__.py`）。すべてのコマンドは`--db-path`・`--knowledge-root`・`--layouts-root`の3つの共通オプションを要求する（`help`コマンドを除く）。

```bash
# DBスキーマを初期化する
python -m mod_personnel_db.cli \
  --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge \
  --layouts-root ./layouts \
  init-db

# 未処理PDFを一括処理する
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts run-pending

# 指定したPDF（PdfRecord.id）のみを処理する
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts run-job 42

# 現在のParserVersion/KnowledgeSnapshotを表示する
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts version

# レビュー待ちのLearning Datasetエントリを一覧・処理する
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts review list
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts review start <record_id>
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts review approve <record_id>
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts review reject <record_id>

# Gold Databaseを出力する
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts export all
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts export person <person_key>
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts export since 2026-01-01T00:00:00+00:00

# コマンド一覧
python -m mod_personnel_db.cli help
```

`review`・`export`コマンドの現在の責務範囲は上記「アーキテクチャ概要」の注記を参照。

## ディレクトリ構成

| パス | 責務 |
|---|---|
| `README.md` | プロジェクト概要（本ファイル） |
| `CLAUDE.md` | Claude Code（AIコーディングエージェント）向けの作業規約 |
| `AGENTS.md` | 任意のAIエージェント向けの汎用運用規約 |
| `CONTRIBUTING.md` | 人間の開発者向けの開発フロー・規約 |
| [`CHANGELOG.md`](CHANGELOG.md) | Phase1〜Phase5の変更履歴（Keep a Changelog形式） |
| `LICENSE` | ライセンス条項 |
| `CODEOWNERS` | パスごとのレビュー担当者定義 |
| `.gitignore` | Git管理除外ルール |
| `pyproject.toml` | Pythonプロジェクトの唯一の設定源（依存関係・ビルド・lint・型・テスト設定） |
| `.pre-commit-config.yaml` | コミット前静的チェックの定義 |
| `.github/` | CI/CDワークフロー・Issue/PRテンプレート |
| `docs/` | アーキテクチャ・データモデル・ADR・運用手順書 |
| `knowledge/` | 階級名・組織名・表記ゆれ等のドメイン知識（人手管理データ、8カテゴリ。現時点ではREADMEのみで実データは未投入） |
| `layouts/` | PDFフォーマット（時代・様式）ごとのレイアウト定義（現時点ではREADMEのみで実データは未投入） |
| `src/mod_personnel_db/` | 本体実装（Pythonパッケージ）。下記「主要パッケージ」を参照 |
| `tests/unit/` | 単体テスト（53ファイル、対象パッケージ全域） |
| `tests/integration/` | 結合テスト（`cli/`配下、CLI全体のE2Eテスト） |
| `tests/golden/` | ゴールデンファイルテスト（[ADR-0007](docs/adr/0007-golden-file-testing.md)、未整備） |
| `scripts/` | 定型化されていない運用・保守スクリプト |
| `sample_pdfs/` | テスト用の代表的なサンプルPDF（現時点では未投入） |
| `sample_outputs/` | `sample_pdfs/` に対応する期待出力・ゴールデンファイル（現時点では未投入） |
| `logs/` | 実行時ログの出力先（Git管理対象外） |
| `tmp/` | 一時作業領域（Git管理対象外） |

### `src/mod_personnel_db/` 主要パッケージ

| パッケージ | 責務 |
|---|---|
| `models/` | パイプライン全体で受け渡しされるドメインモデル（値オブジェクト） |
| `document/` | Document Analyzer（PDFメタデータ・健全性・基本統計の取得） |
| `layout/` | Layout Detector（様式判定・PDF本文の再読込） |
| `sections/` | Section Parser（対象セクションの切り出し） |
| `extractors/` | Field Extractor（フィールドの構造的抽出） |
| `normalizers/` | Normalizer（knowledgeによる正規化） |
| `validators/` | Validator（ドメイン制約による検証） |
| `pipeline/` | `PipelineRunner`（純粋なStage実行機）と`JobRunner`（Coordinator） |
| `repositories/` | Repository Protocol（8種）と、そのSQLite実装（`repositories/sqlite/`） |
| `knowledge/` | `KnowledgeService`（`FileKnowledgeService`具象実装） |
| `learning/` | `LearningService`（Learning Datasetのライフサイクル管理） |
| `review/` | `ReviewService`（Learning Datasetの人手レビュー、限定スコープ） |
| `export/` | `ExportService`（Gold Databaseの読み出し、限定スコープ） |
| `cli/` | Composition Root（`bootstrap.py`）とCLIエントリポイント（`app.py`, `commands.py`） |
| `utils/` | ドメイン知識を持たない汎用ヘルパー |

各パッケージの詳細な責務・依存関係・実装状況は[`docs/api/package-design.md`](docs/api/package-design.md)を正とする。

## ドキュメント目次

- [`docs/constitution.md`](docs/constitution.md) — **Project Constitution**（プロジェクト憲法）。ADR・Architecture Contractを含む全設計文書の最上位に位置する統治文書
- [`docs/design-freeze.md`](docs/design-freeze.md) — **Design Freeze Review**。全設計領域の横断レビューと設計完了宣言
- [`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md) — **Phase5最終監査レポート**。ADR・Architecture Contract・Dependency Rule・Package Design・Protocol・Composition Root・CLI・Testの整合性監査結果
- [`docs/implementation.md`](docs/implementation.md) — **Implementation Guide**。実装フェーズの最上位ガイドライン（Constitution → ADR → Architecture Contract → Implementation Guideの順で従う）
- [`docs/coding-style.md`](docs/coding-style.md) — Coding Style Guide（命名規則・関数長・型ヒント方針・構文選択等）
- [`docs/testing/test-policy.md`](docs/testing/test-policy.md) — Test Policy（Unit/Integration/Golden/Regression/Performance/Acceptance/Benchmark/Mutation Testの定義）
- [`docs/parser-guidelines.md`](docs/parser-guidelines.md) — Parser Development Guidelines（本プロジェクト専用のParser開発規約）
- [`docs/implementation-checklist.md`](docs/implementation-checklist.md) — Implementation Checklist
- [`docs/developer-workflow.md`](docs/developer-workflow.md) — Developer Workflow（Issue作成からDeploymentまでのフロー、Mermaid可視化）
- [`docs/architecture.md`](docs/architecture.md) — システム全体のパイプライン設計
- [`docs/configuration.md`](docs/configuration.md) — Configuration Architecture
- [`docs/security.md`](docs/security.md) — Security Architecture
- [`docs/architecture/learning_dataset.md`](docs/architecture/learning_dataset.md) — Learning Dataset設計（フィールド仕様・ライフサイクル）
- [`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md) — Architecture Contract（コンポーネント間の分離保証、15 Guarantee）
- [`docs/data_model.md`](docs/data_model.md) — データモデル（概念設計）
- [`docs/database/schema.md`](docs/database/schema.md) — SQLite物理スキーマ（ER図・テーブル定義・Migration方針）
- [`docs/database/json_schema.md`](docs/database/json_schema.md) — 公開JSON仕様（JSON Schema Draft 2020-12、未実装の設計目標）
- [`docs/knowledge/schema.md`](docs/knowledge/schema.md) — Knowledge Baseスキーマ（8カテゴリのYAML定義）
- [`docs/api/`](docs/api/) — Interface & Package設計（パッケージ構成・公開API・Repository Pattern・モデル・Pipeline Interface・依存ルール・コーディング規約）
- [`docs/review/`](docs/review/) — Review Domain（ライフサイクル・ドメインモデル・ポリシー・キュー・メトリクス、未実装の広範な設計）
- [`docs/workflow/`](docs/workflow/) — Workflow State Machine（Queued〜Archivedのライフサイクル）
- [`docs/operations/observability.md`](docs/operations/observability.md) — Observability設計
- [`docs/operations/release.md`](docs/operations/release.md) — 運用設計（Release Flow/Rollback/Migration/Backfill/Disaster Recovery等）
- [`docs/glossary.md`](docs/glossary.md) — ドメイン用語集
- [`docs/adr/`](docs/adr/) — Architecture Decision Records（全46本）
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開発への参加方法
- [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) — AIエージェント運用規約

## 開発方法

1. 上記「インストール方法」に従って環境を構築し、`pre-commit install`を実行する。
2. ブランチ戦略・コミットメッセージ規約・Pull Requestプロセスは[`CONTRIBUTING.md`](CONTRIBUTING.md)を参照する。
3. データモデル・パイプライン段階・技術選定に関わる変更は、実装前に[`docs/adr/`](docs/adr/)へ新規ADRを追加する（[`docs/adr/README.md`](docs/adr/README.md#いつadrを書くか作成ルール)）。中核パイプライン（[ADR-0011](docs/adr/0011-fixed-core-pipeline.md)）を変更する提案は、通常のADR追加に加えて必ず事前にユーザーへ確認する。
4. コーディング規約は[`docs/coding-style.md`](docs/coding-style.md)、実装チェックリストは[`docs/implementation-checklist.md`](docs/implementation-checklist.md)を参照する。
5. PDFレイアウト依存の値（座標・列位置・見出し文字列）は`src/`に直接埋め込まず`layouts/`のレイアウト定義を経由し、階級名の表記ゆれ・組織名の改称履歴等のドメイン知識は`src/`のロジックではなく`knowledge/`のデータとして表現する（[ADR-0003](docs/adr/0003-layout-definition-strategy.md), [ADR-0005](docs/adr/0005-knowledge-base-normalization.md)）。

## テスト方法

```bash
# 静的解析（lint / format / 型チェック）
ruff check src/ tests/
ruff format --check src/ tests/
mypy --strict src/ tests/

# テスト（Unit + Integration、Coverage付き）
pytest --cov
```

`pyproject.toml`の`[tool.coverage.report]`が定めるCoverage閾値（`fail_under = 80`）を満たす必要がある。現在の実測値は`docs/reports/phase5-final-audit.md`のTest Summaryを参照。テスト種別ごとの目的・実行タイミング・Coverage目標は[`docs/testing/test-policy.md`](docs/testing/test-policy.md)が定める8種別（Unit/Integration/Golden/Regression/Performance/Acceptance/Benchmark/Mutation）を正とする。Golden/Regression/Performance/Acceptance/Benchmark Testは未着手である。

## データの出典と利用方針

本プロジェクトが扱うのは、防衛省が公務として一般に公表した人事発令情報に限られます。取り扱い方針の詳細は [ADR-0008](docs/adr/0008-data-ethics-policy.md) を参照してください。

## ライセンス

[`LICENSE`](LICENSE)を参照。本プロジェクトはAll Rights Reserved（全著作権留保）とし、ソースコードの再利用・改変・再配布を許可しない。
