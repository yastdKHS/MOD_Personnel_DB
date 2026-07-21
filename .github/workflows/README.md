# .github/workflows/

## 責務

GitHub Actions によるCI（継続的インテグレーション）の定義。

## 現状の方針

`src/` および `tests/` に実装コードが存在するため、`ci.yml` はPRごと・`main`へのpushごとにruffのlint/format check・mypy strict・pytest（Coverage付き）を実行する（[`docs/reports/phase5-final-audit.md`](../../docs/reports/phase5-final-audit.md)のTest Summary参照）。

## 今後追加予定のワークフロー

- `release.yml`: データベースのバージョン付き公開（[`docs/adr/0010-ci-cd-and-publish-strategy.md`](../../docs/adr/0010-ci-cd-and-publish-strategy.md) 参照、未実装）
- `layout-validation.yml`: `layouts/` 追加時に `sample_pdfs/` / `sample_outputs/` との整合を検証する専用ジョブ（未実装。`layouts/`・`sample_pdfs/`・`sample_outputs/`に実データが投入されるまでは着手しない）
- 依存脆弱性スキャン（`pip-audit`等）: [ADR-0026](../../docs/adr/0026-security-policy.md)が求めるが未実装
- スケジュール実行ワークフロー: [ADR-0019](../../docs/adr/0019-workflow-orchestration.md)が定めるcron起動の定期実行だが未実装
