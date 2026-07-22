# .github/workflows/

## 責務

GitHub Actions によるCI（継続的インテグレーション）・リリースゲート・定期実行の定義。

## 現状の方針（3ワークフロー、Phase6 Task14-6時点）

`src/` および `tests/` に実装コードが存在するため、3ワークフローはいずれもruffのlint/format check・mypy strict・pytest（Coverage付き）という同一の品質ゲートを実行する。トリガー（いつ実行するか）が異なるのみで、チェック内容自体に差はない。

| ワークフロー | トリガー | 役割 | インストール方法 |
|---|---|---|---|
| `ci.yml` | `pull_request`・`main`へのpush | 通常開発時の品質ゲート（[ADR-0010](../../docs/adr/0010-ci-cd-and-publish-strategy.md)） | `pip install -e ".[dev]"` |
| `release.yml` | `workflow_dispatch`・`v*`タグのpush | 明示的なリリース操作（[ADR-0010](../../docs/adr/0010-ci-cd-and-publish-strategy.md)が定める「自動マージによる即時公開はしない」方針に基づく起点）での品質ゲート再確認 | Poetry（`pip install poetry` → `poetry install --extras dev`） |
| `nightly.yml` | `schedule`（cron、毎日）・`workflow_dispatch` | 依存ライブラリの更新等による突発的な壊れを毎日検知する定期実行（[ADR-0019](../../docs/adr/0019-workflow-orchestration.md)） | `pip install -e ".[dev]"` |

`release.yml`・`nightly.yml`とも、実際のデータベース公開ステップ（FTP送信等）やパイプラインの定期実行（PDF取得・処理）自体は含まない。それらは`ftp/`・`fetch/`（未実装、[`docs/api/package-design.md`](../../docs/api/package-design.md)参照）の実装後に別途追加する。

## 今後追加予定のワークフロー

- `layout-validation.yml`: `layouts/` 追加時に `sample_pdfs/` / `sample_outputs/` との整合を検証する専用ジョブ（未実装。`layouts/`・`sample_pdfs/`・`sample_outputs/`に実データが投入されるまでは着手しない）
- 依存脆弱性スキャン（`pip-audit`等）: [ADR-0026](../../docs/adr/0026-security-policy.md)が求めるが未実装
- 実際のデータベース公開ステップ（FTP送信等）・パイプライン定期実行: `release.yml`/`nightly.yml`の品質ゲートとは別に、`ftp/`・`fetch/`実装後に追加する
