# Changelog

本プロジェクトの設計・実装上の重要な変更を記録する。[Keep a Changelog](https://keepachangelog.com/) の形式に準拠する。

本ファイルは実装フェーズ（Phase2）で発生した「複数ドキュメント・実装にまたがる仕様変更」の記録を目的として、Phase2 Task4-0（Design Synchronization）で新設した。それ以前の変更履歴（設計フェーズ全体、Phase2 Task1〜3）は、git履歴および各[ADR](docs/adr/)を正とする（本ファイルへの遡及的な再構築は行わない）。

新しいエントリを追加する際は、対応するADR・更新したドキュメントへのリンクを必ず含める（[CLAUDE.md](CLAUDE.md)の「Single Source of Truth」原則、[ADR-0014](docs/adr/0014-development-discipline.md)の開発規律）。

## [Unreleased]

### Changed

- **`PipelineMetrics`のフィールド構成を確定**（Phase2 Task4-0, [ADR-0031](docs/adr/0031-pipeline-metrics-field-finalization.md)）: 設計フェーズ当初の`docs/api/pipeline.md`ドラフト（`stage_durations_ms` / `processed_count` / `failed_count` / `skipped_count`の4項目）と、Phase2 Task3で実装した`src/mod_personnel_db/pipeline/metrics.py`（`elapsed_ms` / `started_at` / `finished_at` / `succeeded` / `warning_count` / `error_count`の6項目）が乖離していた状態を解消し、実装済みの6項目版を正式仕様として`docs/api/pipeline.md`に反映した。あわせて[`docs/operations/observability.md`](docs/operations/observability.md)のMetrics節を更新し、Stage別処理時間は`PipelineEvent`列から導出する運用に変更したことを明記した。
  - 更新ドキュメント: `docs/api/pipeline.md`, `docs/operations/observability.md`, `docs/adr/index.md`, `docs/adr/dependency-map.md`, `docs/adr/README.md`
  - 実装コードの変更: なし（`src/mod_personnel_db/pipeline/metrics.py`は既にADR-0031が定める仕様と一致していたため）

## Phase2 Task1〜3（本ファイル新設以前）

- Task1: Repository Skeleton（`repositories/`, `repositories/sqlite/`）実装。詳細は git履歴を参照。
- Task2: Domain Model Implementation（`models/`、13モデル全種）実装。詳細は git履歴を参照。
- Task3: Pipeline Skeleton Implementation（`pipeline/`）実装、およびEnum実装方針を`enum.StrEnum`に統一（[ADR-0030](docs/adr/0030-strenum-adoption.md)）。詳細は git履歴を参照。
