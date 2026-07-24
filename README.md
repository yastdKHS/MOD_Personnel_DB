# MOD Personnel DB（防衛省人事発令データベース）

> ステータス: **v1.0.0 Release Candidate（Phase7完了、CLI統合済み）**。10年以上の運用に耐える設計corpus（ディレクトリ構成・規約・46本のADR・`docs/`配下の全設計文書）が[`docs/design-freeze.md`](docs/design-freeze.md)のレビューを経て確定し、[`docs/implementation.md`](docs/implementation.md)以下のImplementation Standardsに従って実装した。現時点で、中核パイプライン6段階（Document Analyzer〜Validator）・Repository層（SQLite実装）・JobRunner（Coordinator）・KnowledgeService/LearningService/ReviewService/ExportService（JSON/CSV/Parquet・完全性情報を含む）・`config/`（Pydantic Settings）・Composition Root（`cli/`）・CLIエントリポイント・GitHub Actions 3ワークフロー（`ci.yml`/`release.yml`/`nightly.yml`）に加え、Phase7で`ftp/`（FTPClient）・`features/`（FeatureStore）・`fetch/`（FetchClient）・`services/`（JobOrchestrator・Scheduler）の4パッケージが実装済みである。このうち`ftp/`・`fetch/`・`services/`はTask17-1〜17-4でComposition Root（`cli/`）へ配線され、`fetch-stage`/`run-workflow`/`schedule-now`/`list-schedule`の4コマンドとしてCLIから利用できる。`features/`のみ、実装済みだが`JobRunner`への統合が未実装のため未接続のまま残る（詳細は「アーキテクチャ概要」・[`RELEASE_STATUS.md`](RELEASE_STATUS.md)を参照）。Phase5時点の詳細な実装状況の監査結果は[`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md)を、Phase7完了時点の監査結果は[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)を、リリース判定（Release Decision/Known Limitations/Remaining Work等）は[`RELEASE_STATUS.md`](RELEASE_STATUS.md)を参照。まだGitタグは打たれていない（`pyproject.toml`の`version`は`0.0.0`のまま）。タグ運用は「[リリースタグ運用](#リリースタグ運用)」を参照。

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
- **`ftp/`・`features/`・`fetch/`・`services/`（Phase7）**: `ftp/`はFTP/SFTPファイル転送を抽象化する`FTPClient`（`StandardFTPClient`/`InMemoryFTPClient`）、`features/`はConfidence算出等に使う派生特徴量を都度計算する`FeatureStore`、`fetch/`はHTTP経由でのPDF取得に限定した`FetchClient`（`HTTPFetchClient`/`MockFetchClient`）、`services/`は`fetch/`・`ftp/`・`pipeline/`・`review/`・`export/`を横断的に調整するアプリケーションサービス層`JobOrchestrator`（`DefaultJobOrchestrator`）、および「いつ`JobOrchestrator`を呼ぶか」の決定にのみ責務を持つ`Scheduler`（`DefaultScheduler`、`JobOrchestrator`のみに依存）である。いずれもPhase7（Task16-1〜16-4）で実装済みであり、このうち`ftp/`・`fetch/`・`services/`はPhase7 Task17-1〜17-4で`cli/`（Composition Root）へ配線され、`fetch-stage`・`run-workflow`・`schedule-now`・`list-schedule`の4コマンドとして公開されている。統合設計は[`docs/phase7-integration-design.md`](docs/phase7-integration-design.md)（Task17-0）、実装は[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)を参照。`features/`のみ`pipeline/`（`JobRunner`）から呼び出されておらず、独立した未接続のパッケージのまま残る。

パッケージ間の依存方向は[`docs/api/dependency-rule.md`](docs/api/dependency-rule.md)が定め、各パッケージの責務・実装状況は[`docs/api/package-design.md`](docs/api/package-design.md)を正とする。`config/`はPhase6 Task14-5で実装済み（[ADR-0028](docs/adr/0028-pydantic-settings-for-configuration.md)）。

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

# PDFをURLから取得し保存する（JobOrchestrator経由）
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts \
  fetch-stage https://example.mod.go.jp/order.pdf ./staged/order.pdf 2026-01-01

# Pipeline→Review→Exportを一括実行する（JobOrchestrator経由。Fetchフェーズは対象外）
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts \
  run-workflow json ./export.json

# 未処理PDFの処理を即座にトリガーする（Scheduler経由、job_typeはrun_pending_pipelineのみ対応）
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts \
  schedule-now run_pending_pipeline

# 登録済み周期実行対象の次回実行予定を表示する（Scheduler経由。CLIからの周期定義設定は未実装のため現時点では常に0件）
python -m mod_personnel_db.cli --db-path ./mod_personnel.sqlite3 \
  --knowledge-root ./knowledge --layouts-root ./layouts list-schedule

# コマンド一覧
python -m mod_personnel_db.cli help
```

`review`・`export`コマンドの現在の責務範囲は上記「アーキテクチャ概要」の注記を参照。`fetch-stage`・`run-workflow`はPhase7 Task17-2、`schedule-now`・`list-schedule`はPhase7 Task17-4で追加した（詳細は[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)を参照）。

## ディレクトリ構成

| パス | 責務 |
|---|---|
| `README.md` | プロジェクト概要（本ファイル） |
| `CLAUDE.md` | Claude Code（AIコーディングエージェント）向けの作業規約 |
| `AGENTS.md` | 任意のAIエージェント向けの汎用運用規約 |
| `CONTRIBUTING.md` | 人間の開発者向けの開発フロー・規約 |
| [`CHANGELOG.md`](CHANGELOG.md) | Phase1〜Phase6の変更履歴（Keep a Changelog形式） |
| [`RELEASE_STATUS.md`](RELEASE_STATUS.md) | v1.0.0 Release Candidateのリリース判定記録（Version/Current Status/Release Decision/Architecture Contract/ADR Status/Test Summary/Coverage/CI Status/Known Limitations/Remaining Work/Release Recommendation） |
| `LICENSE` | ライセンス条項 |
| `CODEOWNERS` | パスごとのレビュー担当者定義 |
| `.gitignore` | Git管理除外ルール |
| `pyproject.toml` | Pythonプロジェクトの唯一の設定源（依存関係・ビルド・lint・型・テスト設定） |
| `.pre-commit-config.yaml` | コミット前静的チェックの定義 |
| `.github/` | GitHub Actionsワークフロー（`ci.yml`／`release.yml`／`nightly.yml`、詳細は[`.github/workflows/README.md`](.github/workflows/README.md)）・Issue/PRテンプレート |
| `docs/` | アーキテクチャ・データモデル・ADR・運用手順書 |
| `knowledge/` | 階級名・組織名・表記ゆれ等のドメイン知識（人手管理データ、8カテゴリ。現時点ではREADMEのみで実データは未投入） |
| `layouts/` | PDFフォーマット（時代・様式）ごとのレイアウト定義（現時点ではREADMEのみで実データは未投入） |
| `src/mod_personnel_db/` | 本体実装（Pythonパッケージ）。下記「主要パッケージ」を参照 |
| `tests/unit/` | 単体テスト（64ファイル、対象パッケージ全域） |
| `tests/integration/` | 結合テスト（`cli/`/`config/`/`export/`/`golden/`配下、6ファイル） |
| `tests/golden/` | ゴールデンファイルテスト用フィクスチャ（[ADR-0007](docs/adr/0007-golden-file-testing.md)、合成PDF1件。テストコードは`tests/integration/golden/test_golden.py`） |
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
| `ftp/` | `FTPClient`（FTP/SFTPファイル転送、Phase7 Task16-1、Task17-1で`cli/`配線済み） |
| `features/` | `FeatureStore`（Confidence派生特徴量の都度計算、Phase7 Task16-2、`pipeline/`未接続） |
| `fetch/` | `FetchClient`（HTTP経由のPDF取得、Phase7 Task16-3、Task17-1で`cli/`配線済み） |
| `services/` | `JobOrchestrator`（fetch/ftp/pipeline/review/exportの横断調整）・`Scheduler`（実行トリガー管理、Phase7 Task16-4、Task17-1/17-4で`cli/`配線済み） |
| `cli/` | Composition Root（`bootstrap.py`）とCLIエントリポイント（`app.py`, `commands.py`） |
| `utils/` | ドメイン知識を持たない汎用ヘルパー |

各パッケージの詳細な責務・依存関係・実装状況は[`docs/api/package-design.md`](docs/api/package-design.md)を正とする。

## ドキュメント目次

- [`docs/constitution.md`](docs/constitution.md) — **Project Constitution**（プロジェクト憲法）。ADR・Architecture Contractを含む全設計文書の最上位に位置する統治文書
- [`docs/design-freeze.md`](docs/design-freeze.md) — **Design Freeze Review**。全設計領域の横断レビューと設計完了宣言
- [`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md) — **Phase5最終監査レポート**。ADR・Architecture Contract・Dependency Rule・Package Design・Protocol・Composition Root・CLI・Testの整合性監査結果
- [`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md) — **Phase7最終監査レポート**（Task17-5）。`ftp/`・`fetch/`・`features/`・`services/`・`Scheduler`・CLI統合・Composition Root・Dependency Rule・Package Design・Architecture Contract・Public API後方互換性・Release Readinessの監査結果
- [`RELEASE_STATUS.md`](RELEASE_STATUS.md) — **v1.0.0 Release Candidateリリース判定**。Release Decision・Known Limitations・Remaining Work等
- [`docs/phase7-implementation-roadmap.md`](docs/phase7-implementation-roadmap.md) — **Phase7 Implementation Roadmap**。`features/`・`fetch/`・`ftp/`・`services/`の設計方針・依存方向・実装順序（Task16-0で設計確定。4パッケージともTask16-1〜16-4で実装済み、実装状況の詳細は[`docs/api/package-design.md`](docs/api/package-design.md)を参照）
- [`docs/phase7-integration-design.md`](docs/phase7-integration-design.md) — **Phase7 Integration Design**。Phase7実装済み4パッケージをComposition Root（`cli/`）へ統合するための設計（Task17-0で設計確定。`ftp/`・`fetch/`・`services/`はTask17-1〜17-4で実装済み、`features/`統合のみ未着手のまま残る）
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

`pyproject.toml`の`[tool.coverage.report]`が定めるCoverage閾値（`fail_under = 80`）を満たす必要がある。Phase7完了時点（Task17-5監査時点）の実測値は816件成功・Coverage 98.98%（Phase6完了時点は634件成功・Coverage 98.99%、Phase5時点の実測値は`docs/reports/phase5-final-audit.md`のTest Summaryを参照、528件成功時点のスナップショット）。テスト種別ごとの目的・実行タイミング・Coverage目標は[`docs/testing/test-policy.md`](docs/testing/test-policy.md)が定める8種別（Unit/Integration/Golden/Regression/Performance/Acceptance/Benchmark/Mutation）を正とする。Golden Testは`tests/integration/golden/test_golden.py`（Phase6 Task14-1）として実装済み。Regression/Performance/Acceptance/Benchmark Testは未着手である。

## リリースタグ運用

本プロジェクトはまだリリースタグを打っていない（`pyproject.toml`の`version`は`0.0.0`のまま）。最初のリリースタグ`v1.0.0`（SemVer形式、[ADR-0023](docs/adr/0023-parser-versioning-policy.md)）を`main`へ付与すると、[`.github/workflows/release.yml`](.github/workflows/release.yml)（`push: tags: v*`）が起動し、`ci.yml`と同じ品質ゲート（Poetry経由でのruff lint・ruff format check・mypy・pytest）を再実行する（`workflow_dispatch`による手動起動も可能）。

ADR-0023が定める「タグ付与をトリガーに`parser_versions`テーブルへ新しい行を自動記録する」処理、および[`docs/operations/release.md`](docs/operations/release.md#release-flow)のRelease Flowが定めるstaging/production環境分離・データ公開（Human Review後のExport/FTP送信）は、`ftp/`・`fetch/`パッケージ自体はPhase7で実装済みでありCLI経由（`fetch-stage`/`run-workflow --remote-path`）で手動実行可能になったものの、対応する自動化（バージョン記録・環境分離・CI/CDワークフローからの定期呼び出し）が未実装のため、現時点の`release.yml`には含まれない。詳細は[`docs/operations/release.md`](docs/operations/release.md#release-flow)の実装状況注記を参照。

## Scheduler運用（GitHub Actions）

[`.github/workflows/scheduler.yml`](.github/workflows/scheduler.yml)（Phase8 Task18-3）が、既存CLIの`schedule-now run_pending_pipeline`コマンドを定期的に起動する。`Scheduler`・`JobOrchestrator`等のPythonコードをワークフローが直接importすることはなく、常にCLIコマンド経由でのみ実行する。運用フロー全体（GitHub Actions → `schedule-now` → `Scheduler` → `JobOrchestrator`）は[`docs/operations/release.md`](docs/operations/release.md#scheduler運用フローgithub-actions--schedule-now--scheduler--joborchestrator)を参照。

### 手動実行方法

GitHub Actions画面の「Actions」タブ →「Scheduler」ワークフロー →「Run workflow」（`workflow_dispatch`）から、cronを待たずに即座に実行できる。

### Secrets一覧

以下3件をリポジトリ（またはEnvironment）のGitHub Secretsとして登録する。いずれも`schedule-now`が要求する`--db-path`/`--knowledge-root`/`--layouts-root`（`help`コマンド以外の全コマンド共通の必須オプション、上記「CLI使用方法」参照）に対応する。

| Secret名 | 対応するCLIオプション |
|---|---|
| `MOD_PERSONNEL_DB_DB_PATH` | `--db-path` |
| `MOD_PERSONNEL_DB_KNOWLEDGE_ROOT` | `--knowledge-root` |
| `MOD_PERSONNEL_DB_LAYOUTS_ROOT` | `--layouts-root` |

FTP接続情報（[`FtpSettings`](docs/phase8-integration-design.md#2-ftpsettings導入設計)）は`schedule-now`（`run_pending_pipeline`のみ）が呼び出す経路では使用しないため、本ワークフローには含めない。

### cron運用方法

`schedule: cron: "45 8 * * *"`（UTC）= 毎日17:45 JST（UTC+9）に自動起動する。`concurrency`グループ（`mod-personnel-db-scheduler`）により、cron起動と手動起動が重なった場合でも同時実行はされず、先行する実行の完了を待って後続が実行される（[ADR-0025](docs/adr/0025-deployment-strategy.md)が要求するワークフロー側の排他制御）。cronの一時停止・恒久的な廃止の手順は[`docs/operations/release.md`](docs/operations/release.md#maintenance-window)を参照。

## 既知の制限事項（v1.0 Release Candidate）

v1.0.0 Release Candidateとしての最終監査（Phase6 Task15-0、Phase7完了時点は[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)、Task17-5）で確認された、主要な既知の制限事項を示す。完全な一覧・リリース判定は[`RELEASE_STATUS.md`](RELEASE_STATUS.md)のKnown Limitations/Release Decisionを正とする。

- `layouts/`（1様式）・`knowledge/`（8カテゴリ各1件）・Golden Testフィクスチャ（1件）とも実運用規模のデータには未到達であり、複数様式・表記ゆれを網羅したパイプライン実データ検証はできない。
- `ftp/`・`fetch/`・`services/`（`JobOrchestrator`・`Scheduler`）パッケージはPhase7 Task16-1〜16-4で実装され、Task17-1〜17-4で`cli/`（Composition Root）へ配線済みである（`fetch-stage`/`run-workflow`/`schedule-now`/`list-schedule`の4コマンド）。ただし（1）`ftp/`の実接続情報（`FtpSettings`、`config/`未実装）は依然プレースホルダ（`FTPConnectionConfig(host="")`）のままであり実FTPサーバへ接続できない、（2）`schedule-now`/`list-schedule`はCLIから手動でトリガーする経路のみであり、cron等による自動的な定期実行（`JobSchedule`の登録経路）は未実装である（`list-schedule`は現時点で常に0件を返す）、という2点が実運用への到達を妨げている。`features/`は`pipeline/`（`JobRunner`）からも呼び出されておらず、独立した未接続のパッケージのまま残る（詳細は[`docs/api/package-design.md`](docs/api/package-design.md)、[`docs/reports/phase7-final-audit.md`](docs/reports/phase7-final-audit.md)）。
- ADR-0029が求めるEd25519署名・GitHub Actionsの`GITHUB_TOKEN`最小権限設定（`permissions:`ブロック）・サードパーティActionsのコミットSHAピン留めが未実装。Exportの完全性情報はSHA-256チェックサム（`ExportArtifact`、Phase6 Task14-4）のみ。
- ADR-0026が求める依存脆弱性スキャン（`pip-audit`等）が3ワークフロー（`ci.yml`/`release.yml`/`nightly.yml`）いずれにも存在しない。
- `export/`の新機能（`PersonnelRecord`/CSV/Parquet/完全性メタデータ、Phase6 Task14-2〜14-4）はCLIコマンドとして未公開であり、`ExportService`の内部APIとしてのみ利用できる。
- 上記「リリースタグ運用」節のとおり、`parser_versions`自動記録・staging/production環境分離・データ公開の自動化は未実装。
- Golden Test以外のテスト層（Regression/Performance/Acceptance/Benchmark/Mutation）は未着手。

## データの出典と利用方針

本プロジェクトが扱うのは、防衛省が公務として一般に公表した人事発令情報に限られます。取り扱い方針の詳細は [ADR-0008](docs/adr/0008-data-ethics-policy.md) を参照してください。

## ライセンス

[`LICENSE`](LICENSE)を参照。本プロジェクトはAll Rights Reserved（全著作権留保）とし、ソースコードの再利用・改変・再配布を許可しない。
