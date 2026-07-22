# Changelog

本プロジェクトの設計・実装上の重要な変更を記録する。[Keep a Changelog](https://keepachangelog.com/) の形式に準拠する。

本プロジェクトはまだセマンティックバージョニングによるリリースタグを持たない（`pyproject.toml`の`version`は`0.0.0`のまま）。そのため、リリースバージョンの代わりに開発フェーズ（Phase1〜Phase6）ごとに変更履歴をグルーピングする。最初のリリースタグ（`v1.0.0`、[ADR-0023](docs/adr/0023-parser-versioning-policy.md)のSemVer規則）を打つ時点で、本ファイルの形式をバージョン番号ベースに移行する。

新しいエントリを追加する際は、対応するADR・更新したドキュメントへのリンクを必ず含める（[CLAUDE.md](CLAUDE.md)の「Single Source of Truth」原則、[ADR-0014](docs/adr/0014-development-discipline.md)の開発規律）。

## [Unreleased]

### Added

- Phase5 Task13-2: リリース準備（README.md全面更新、本CHANGELOG.mdの整理、`LICENSE`新設、`.github/`配下の初期フェーズ記述更新）。

## Phase6 — v1.0.0 Release Candidate

Phase5完了後、公開JSON契約・CSV/Parquetエクスポート・Export完全性保証・Pydantic Settings採用・GitHub Actions Workflow Orchestrationを実装し、v1.0.0 Release Candidateとしての最終監査・ドキュメント整備を行った。

### Added

- Task14-0: `layouts/`・`knowledge/`に最小限の実データ（様式1件、8カテゴリ各1件）を整備。
- Task14-1: Golden Test自動実行スイート（[`tests/integration/golden/test_golden.py`](tests/integration/golden/test_golden.py)、[ADR-0007](docs/adr/0007-golden-file-testing.md)）を追加。`tests/golden/`に合成PDF・期待結果JSONを1件配置。
- Task14-2: [ADR-0016](docs/adr/0016-public-json-format.md)が定める公開JSON契約に対応する`PersonnelRecord`/`Provenance`/`SourcePdf`（`models/export.py`）・`export/mapper.py`・`export/serialization.py`を実装。`ExportService`へ`export_all_records()`等を追加（既存API不変）。
- Task14-3: [ADR-0022](docs/adr/0022-export-policy.md)が定めるCSV/Parquetエクスポートを実装（`export/csv_writer.py`, `export/parquet_writer.py`, `export/tabular.py`）。依存に`pyarrow`を追加。
- Task14-4: [ADR-0029](docs/adr/0029-export-integrity-and-audit-log-policy.md)が定める完全性・監査情報（`ExportArtifact`: `export_id`/`exported_at`/`format`/`record_count`/`sha256`）を実装（`export/integrity.py`, `export/json_writer.py`）。`ExportService`へ`export_all_with_metadata()`等を追加。
- Task14-5: [ADR-0028](docs/adr/0028-pydantic-settings-for-configuration.md)が定めるPydantic Settings採用により`config/`パッケージを新設（`config/settings.py`の`AppSettings`）。`cli/bootstrap.py`の`CompositionSettings`を`AppSettings`の別名とし、環境変数・`.env`・コンストラクタ引数からの設定読み込みに対応（優先順位: コンストラクタ引数 > 環境変数 > `.env` > デフォルト値）。依存に`pydantic-settings`を追加。
- Task14-6: GitHub Actionsによる Workflow Orchestration（[ADR-0019](docs/adr/0019-workflow-orchestration.md)）を実装。`.github/workflows/release.yml`（`workflow_dispatch`・`v*`タグpushで起動する明示的リリース操作時の品質ゲート、[ADR-0010](docs/adr/0010-ci-cd-and-publish-strategy.md)）・`.github/workflows/nightly.yml`（`schedule`によるcron定期実行・`workflow_dispatch`）を新規追加。`.github/workflows/README.md`を3ワークフロー体制に合わせて更新。

### Changed

- Task15-0: v1.0.0 Release Candidateとしての最終監査を実施（読み取り専用、コード・テスト・ドキュメントの変更を伴わない）。
- Task15-1: Task15-0監査で検出したDocument Drift（`config/`実装状況・`ExportService`の実装状況注記・Golden Test配置説明）を是正（`docs/api/package-design.md`, `docs/api/dependency-rule.md`, `docs/api/interfaces.md`, `docs/testing/test-policy.md`, README.md）。
- Task15-2: v1.0.0 Release Candidateの最終ドキュメント整備。README/CHANGELOGのバージョン整合、Remaining Known LimitationsをREADMEへ反映、`docs/README.md`索引の到達性確保、`docs/operations/release.md`のRelease Flowを`release.yml`の実装範囲（品質ゲートのみ）に一致させた。
- Task15-4: [`RELEASE_STATUS.md`](RELEASE_STATUS.md)を新規作成し、v1.0.0 Release Candidateの最終リリース判定（Version/Date/Current Status/Release Decision/Completed Phases/Architecture Contract/ADR Status/Test Summary/Coverage/CI Status/Known Limitations/Remaining Work/Release Recommendation）を記録した。Known LimitationsはTask15-0監査結果と一致させている。README.mdから`RELEASE_STATUS.md`へのリンクを追加。`docs/operations/release.md`へ「Release Candidateからv1.0.0正式版までの残タスク」節を新設。

## Phase5 — 最終監査・ドキュメント同期・リリース準備

### Added

- Phase5 Task13-0: 全体最終監査レポートを追加（[`docs/reports/phase5-final-audit.md`](docs/reports/phase5-final-audit.md)）。ADR全46本・Architecture Contract Guarantee1〜15・Dependency Rule・Package Design・Protocol単一具象実装・Composition Root・CLI・Test(Unit/Integration/Coverage)の整合性を監査した。

### Changed

- Phase5 Task13-1: 監査結果に基づき`docs/`配下のドキュメントを実装に合わせて同期。
  - [`docs/api/package-design.md`](docs/api/package-design.md): 全パッケージに実装状況（実装済み/未実装/限定スコープ）を明記。`config/`・`features/`・`ftp/`・`fetch/`・`services/`が未実装であることを明示。`repositories/`の`UnitOfWork`記述を実装（未実装）に合わせて修正。`review/`・`export/`の責務を実装済みの狭い契約に書き換え。
  - [`docs/api/dependency-rule.md`](docs/api/dependency-rule.md): `document/`〜`validators/`が`pipeline/`（`PipelineContext`型のみ）に依存する構造を新設節として明文化し、Mermaid図に反映。合成ルート節を`cli/bootstrap.py`の実装に合わせて修正。
  - [`docs/architecture/architecture-contract.md`](docs/architecture/architecture-contract.md): 保証8/9の`promote_to_gold()`という記述と、実装済みの非公開メソッド`_promote_to_gold()`（`approve()`経由）との対応関係を明記。
  - [`docs/api/interfaces.md`](docs/api/interfaces.md)・[`docs/api/review.md`](docs/api/review.md): ReviewService/ExportServiceの各節が未実装の設計目標であることと、実装済みの狭い契約との違いを明記。
  - [`docs/database/schema.md`](docs/database/schema.md): 「コードはまだ実装していません」という記述を、12業務テーブルが実装済みであることを反映した記述に更新。`schema_migrations`管理テーブルが未実装であることを明記。

## Phase4 — Review/Export実装

Learning Datasetの人手レビューとGold Databaseの読み出しを、Composition Root経由でCLIから利用可能にした。

### Added

- Task12-0: `ReviewService`（Learning Dataset review）を実装。`RepositoryReviewService`（`review/service.py`）が`list_pending()`/`start_review()`/`approve()`/`reject()`を提供し、`approve()`は`GoldPromotion`を指定した場合のみ`GoldRepository.add_version()`への反映を行う。`docs/api/review.md`が定めるより広範な設計とは異なる、Learning Dataset固有の狭い契約であることをコード上明記。
- Task12-1: `ExportService`（Gold Database読み出し）を実装。`RepositoryExportService`（`export/service.py`）が`export_all()`/`export_since()`/`export_person()`を提供する。
- Task12-2: `ReviewService`/`ExportService`をComposition Root（`cli/bootstrap.py`）へ組み込み、`Application`の公開メンバとして公開。
- Task12-3: `review`（`list`/`start`/`approve`/`reject`）・`export`（`all`/`person`/`since`）サブコマンドをCLIへ追加（`cli/app.py`, `cli/commands.py`）。
- Task12-4: `tests/integration/cli/test_cli_e2e.py`を追加。`app.main()`のみを駆動し、Composition Rootを実際に動かして9シナリオ（init-db/run-pending/review×4/export×3）をend-to-endで検証する。

## Phase3 — JobRunner・Composition Root実装

中核パイプライン6段階を実際に協調動作させるCoordinatorと、依存生成を一箇所に集約するComposition Rootを実装した。

### Added

- Task10-0.1: [ADR-0044](docs/adr/0044-pipelinerunner-jobrunner-boundary.md)でPipelineRunner/JobRunnerの境界を設計文書に確定。
- Task10-0.2: `KnowledgeService`/`LearningService`/`LearningRepository`のProtocol契約を追加。
- Task10-1: `JobRunner`を実装（当初のスケルトン）。
- Task10-3.1: [ADR-0045](docs/adr/0045-job-runner-aggregate-artifact-coordinator.md)でJobRunnerによる集約Artifact展開モデル（Coordinatorパターン）を確定。
- Task10-4: ADR-0045に従い`JobRunner`をCoordinatorとして実装（`pipeline/job_runner.py`、1PDF・1セクション・1レコード単位の反復処理）。
- Task11-1: [ADR-0046](docs/adr/0046-composition-root-dependency-injection-contract.md)でComposition Root（CLI）の依存注入契約を確定。
- Task11-2: `KnowledgeService`のファイルベース具象実装（`FileKnowledgeService`）を追加。
- Task11-3: `LearningRepository`のSQLite具象実装（`SqliteLearningRepository`）を追加。
- Task11-4: `LearningService`のRepository委譲による具象実装（`RepositoryLearningService`）を追加。
- Task11-5: Composition Root（`cli/bootstrap.py`）を実装し、`JobRunner`の依存を実配線。
- Task11-6: CLI Entry Point（`argparse`ベース、`cli/app.py`）を実装。`init-db`/`run-pending`/`run-job`/`version`/`help`コマンドを提供。

### Fixed

- CIのPythonバージョン不整合を解消（`pyproject.toml`の`>=3.14`指定を、実地検証されてきた`>=3.13`へ統一、[ADR-0042](docs/adr/0042-python-version-target-realignment.md)）。

## Phase2 — 中核パイプライン実装

Version 2.0 Architecture（[ADR-0032](docs/adr/0032-redefine-document-analyzer-responsibility.md)）に基づき、Repository層・ドメインモデル・中核パイプライン6段階を実装した。

### Added

- Task0: Implementation Standards文書群を追加（`docs/coding-style.md`, `docs/testing/test-policy.md`等）。
- Task1: Repository Skeleton（`repositories/`抽象Protocol、`repositories/sqlite/`具象実装）を実装。
- Task2: Domain Model（`models/`、13種の値オブジェクト全種）を実装。
- Task3: `enum.StrEnum`への移行（[ADR-0030](docs/adr/0030-strenum-adoption.md)）とPipeline Framework骨格（`pipeline/context.py`, `pipeline/stage.py`, `pipeline/runner.py`等）を実装。
- Task4-0 + Task3.1: `PipelineMetrics`のフィールド構成確定（[ADR-0031](docs/adr/0031-pipeline-metrics-field-finalization.md)）とDocument Analyzer責務のDesign Synchronization。
- Task4: Document Analyzer実装（[ADR-0032](docs/adr/0032-redefine-document-analyzer-responsibility.md)〜[ADR-0034](docs/adr/0034-pypdf-for-document-analyzer.md)、`document/analyzer.py`、`pypdf`採用）。
- Task5.1: `Document.file_path`保持方式をArchitecture Documentationへ改善候補として記録。
- Task5: Layout Detector実装（[ADR-0035](docs/adr/0035-layout-detector-owns-pdf-content-access.md)〜[ADR-0037](docs/adr/0037-layout-detector-produces-layout-artifact.md)、`layout/detector.py`、PDF本文アクセスの独占）。
- Task6: Section Parser実装（`sections/parser.py`、`LayoutArtifact`のみを入力とする）。
- Task7-0 + Task7: Field Extractor Architecture Verificationおよび実装（[ADR-0038](docs/adr/0038-field-extractor-produces-field-extraction-result.md)、`extractors/extractor.py`）。
- Task8-0 + Task8: Normalizer着手前のField Mapping方針確定（[ADR-0039](docs/adr/0039-normalizer-field-mapping-via-extended-layout-knowledge.md)）およびNormalizer実装（[ADR-0040](docs/adr/0040-normalizer-produces-normalization-result.md)、`normalizers/normalizer.py`）。
- Task9-0 + Task9: Validator着手前のArchitecture Verification（[ADR-0041](docs/adr/0041-validator-constructor-injects-validation-rule-set.md)）およびValidator実装（[ADR-0043](docs/adr/0043-validator-produces-validation-result-with-rule-engine.md)、`validators/validator.py`, `validators/rule_engine.py`）。
- Task9.1: Task9 Review推奨事項をドキュメントへ反映。

## Phase1 — 設計フェーズ（Design Freeze以前）

コード実装に先立ち、リポジトリ構造・ADR・データモデル・API/Interface設計・Review Domain・運用設計を確定した。

### Added

- リポジトリの初期構造（`docs/`, `knowledge/`, `layouts/`, `src/`, `tests/`, `scripts/`, `sample_pdfs/`, `sample_outputs/`, `logs/`, `tmp/`）と各ディレクトリのREADMEを作成。
- 開発規律と中核パイプライン固定化のガバナンス（[ADR-0011](docs/adr/0011-fixed-core-pipeline.md), [ADR-0012](docs/adr/0012-error-handling-priority-order.md), [ADR-0013](docs/adr/0013-learning-dataset-not-correction-log.md), [ADR-0014](docs/adr/0014-development-discipline.md)）を追加。
- SQLiteの物理スキーマ設計（[`docs/database/schema.md`](docs/database/schema.md)、[ADR-0015](docs/adr/0015-sqlite-schema-finalization.md)）を追加。
- 公開JSON仕様（[`docs/database/json_schema.md`](docs/database/json_schema.md)、JSON Schema Draft 2020-12、[ADR-0016](docs/adr/0016-public-json-format.md)）を追加。
- Knowledge Baseを8カテゴリに分離するスキーマ（[`docs/knowledge/schema.md`](docs/knowledge/schema.md)）を追加。
- Correction LogをLearning Datasetへ拡張する設計（[`docs/architecture/learning_dataset.md`](docs/architecture/learning_dataset.md)、[ADR-0017](docs/adr/0017-learning-dataset-field-expansion.md)）を追加。
- ADR統治基盤（Inventory・依存関係図・Gap Analysis・品質チェック、[`docs/adr/`](docs/adr/)）を整備し、ADR-0018〜0026を追加。
- Interface & Package Design一式（[`docs/api/`](docs/api/)、実装なし・型シグネチャのみ）を追加。
- Package Import Graphを作成し循環参照バグ（`repositories/sqlite/ → config/ → repositories/sqlite/`）を検出・修正。
- Review DomainをHuman Reviewの中核として設計（[`docs/review/`](docs/review/)、[ADR-0027](docs/adr/0027-review-domain-elevation.md)）。
- Architecture Review Packageを作成。
- Workflow State Machineを設計（[`docs/workflow/`](docs/workflow/)）。
- Project Constitution（[`docs/constitution.md`](docs/constitution.md)）を追加。
- Observability設計（[`docs/operations/observability.md`](docs/operations/observability.md)）、Configuration Architecture（[`docs/configuration.md`](docs/configuration.md)、[ADR-0028](docs/adr/0028-pydantic-settings-for-configuration.md)）、Security Architecture（[`docs/security.md`](docs/security.md)、[ADR-0026](docs/adr/0026-security-policy.md), [ADR-0029](docs/adr/0029-export-integrity-and-audit-log-policy.md)）、運用設計（[`docs/operations/release.md`](docs/operations/release.md)）を追加。
- Design Freeze Reviewを作成し設計完了を宣言（[`docs/design-freeze.md`](docs/design-freeze.md)）。

## Phase2 Task1〜3（旧: 本ファイル新設以前のエントリ）

本CHANGELOG.mdはPhase2 Task4-0（Design Synchronization）で新設した。それ以前の変更履歴の詳細はgit履歴および各[ADR](docs/adr/)を正とする（本ファイルへの遡及的な再構築は行わない）。Phase5 Task13-2でPhase1〜Phase5全体を俯瞰する形に整理した際、上記各Phase節へ要約として統合した。
