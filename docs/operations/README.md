# docs/operations/（運用手順書 / Runbook）

## 責務

システムが実装され本番運用に入った後、日々の運用・障害対応・定型作業の手順を記録する場所。「動かし方」を人が変わっても再現できるようにする。

## 現状（Task36時点）

Task34〜Task36で、DB監査・修復手順・運用担当者向けRunbookを追加した。未着手のまま残る想定runbook:

- `new_layout_rollout.md`: 新しいPDF様式に対応する際の詳細手順（`CONTRIBUTING.md` の概要版を実務レベルに具体化したもの）
- `data_correction.md`: 公開後に誤りが判明した場合の訂正・再公開フロー

当初`pipeline_run.md`・`incident_response.md`として想定していた内容は、下記「運用担当者向けRunbook（Task36）」の`daily_operation.md`・`incident_response.md`として作成済みである（`pipeline_run.md`というファイル名では作成していない）。

## 既存ドキュメント

- [`observability.md`](observability.md): Observability設計（Logging / Metrics / Tracing / Health Check / Alert / Dashboard / SLO / SLI / Error Budget / OpenTelemetry対応方針）。
- [`release.md`](release.md): 運用設計（Release Flow / Rollback / Parser Upgrade / Knowledge Upgrade / Migration / Backfill / Recovery / Backup / Disaster Recovery / Maintenance Window）。[ADR-0024](../adr/0024-knowledge-versioning-and-backfill.md)が本ディレクトリに委ねていたBackfill実行手順を含む。
- [`db_audit.md`](db_audit.md)（Task34/35）: DB監査項目・整合性チェックSQL・監査ツール（`tools/db_audit.py`）・GitHub Actions自動実行（`db_audit.yml`）の設計文書。
- [`db_repair_procedures.md`](db_repair_procedures.md)（Task34）: DB監査で異常検知した場合の手動修復手順（Repair Procedure）。

## 運用担当者向けRunbook（Task36）

開発者向けの設計文書（上記）とは別に、運用担当者・システム管理者がそのまま利用できる手順書を追加した。いずれも既存文書の内容を複製せず、リンクで参照する。

- [`daily_operation.md`](daily_operation.md): 日常運用（Pipeline実行/Resume/Scheduler/GitHub Actions/DB Audit実行・確認/定期保守）
- [`incident_response.md`](incident_response.md): 障害対応（Pipeline失敗/Resume失敗/Job stuck/SQLite Busy/RepositoryError/DB Audit Error/GitHub Actions失敗、優先度P1〜P3で分類）
- [`backup_restore.md`](backup_restore.md): バックアップ・リストア（Backup→Restore→DB Audit→Pipeline Resume確認→正常確認の一連の流れ）
- [`faq.md`](faq.md): 運用担当者向けFAQ
