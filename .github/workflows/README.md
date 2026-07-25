# .github/workflows/

## 責務

GitHub Actions によるCI（継続的インテグレーション）・リリースゲート・定期実行の定義。

## 現状の方針（4ワークフロー、Phase8 Task18-3時点）

`ci.yml`・`release.yml`・`nightly.yml`の3ワークフローはいずれもruffのlint/format check・mypy strict・pytest（Coverage付き）という同一の品質ゲートを実行する。トリガー（いつ実行するか）が異なるのみで、チェック内容自体に差はない。`scheduler.yml`（Task18-3で追加）のみ、品質ゲートではなく実際のCLIコマンド（`schedule-now`）を起動する運用ワークフローである。

| ワークフロー | トリガー | 役割 | インストール方法 |
|---|---|---|---|
| `ci.yml` | `pull_request`・`main`へのpush | 通常開発時の品質ゲート（[ADR-0010](../../docs/adr/0010-ci-cd-and-publish-strategy.md)） | `pip install -e ".[dev]"` |
| `release.yml` | `workflow_dispatch`・`v*`タグのpush | 明示的なリリース操作（[ADR-0010](../../docs/adr/0010-ci-cd-and-publish-strategy.md)が定める「自動マージによる即時公開はしない」方針に基づく起点）での品質ゲート再確認 | Poetry（`pip install poetry` → `poetry install --extras dev`） |
| `nightly.yml` | `schedule`（cron、毎日）・`workflow_dispatch` | 依存ライブラリの更新等による突発的な壊れを毎日検知する定期実行（[ADR-0019](../../docs/adr/0019-workflow-orchestration.md)） | `pip install -e ".[dev]"` |
| `scheduler.yml` | `schedule`（cron、毎日17:45 JST）・`workflow_dispatch` | 既存CLI（`schedule-now run_pending_pipeline`）を定期的に起動し、未処理PDFの中核パイプライン処理をトリガーする（[ADR-0019](../../docs/adr/0019-workflow-orchestration.md)、[`docs/phase8-integration-design.md`](../../docs/phase8-integration-design.md)、Task18-3）。詳細な運用手順は[`README.md`](../../README.md#scheduler運用github-actions)・[`docs/operations/release.md`](../../docs/operations/release.md)を参照 | `pip install -e .`（devエクストラなし） |

`release.yml`・`nightly.yml`とも、実際のデータベース公開ステップ（FTP送信等）は含まない。`scheduler.yml`が起動する`schedule-now`も、現時点では`run_pending_pipeline`（中核パイプライン処理のみ）に限定され、Fetch（新規PDF取得）・Export・FTP Publishを含む`run_workflow`系の自動化はまだ対象外である（`docs/phase8-integration-design.md#4-production-workflow設計`の未解決事項を参照）。

## 今後追加予定のワークフロー

- `layout-validation.yml`: `layouts/` 追加時に `sample_pdfs/` / `sample_outputs/` との整合を検証する専用ジョブ（未実装。`layouts/`・`sample_pdfs/`・`sample_outputs/`に実データが投入されるまでは着手しない）
- 依存脆弱性スキャン（`pip-audit`等）: [ADR-0026](../../docs/adr/0026-security-policy.md)が求めるが未実装
- Fetch（新規PDF取得）・Export・FTP Publishを含む`run_workflow`系の自動定期実行: `scheduler.yml`の`schedule-now`（`run_pending_pipeline`のみ）とは別に、Fetch対象の自動決定方法（`docs/phase8-integration-design.md#4-production-workflow設計`が未解決のまま残す設計課題）が具体化した後に追加する
