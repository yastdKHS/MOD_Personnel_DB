# 運用担当者向けFAQ

## 目的

運用担当者が日常的に抱きやすい疑問への一次回答をまとめる。詳細手順は各リンク先を参照する。

## 対象読者

運用担当者。

---

| よくある質問 | 原因 | 対応 |
|---|---|---|
| DB AuditがWarningになった | `personnel_sections`の新旧逆転、`candidate_records`のpending取り残され、`jobs`のdangling running job等、即対応不要な項目が検出された | [`incident_response.md`](incident_response.md)の該当項目を確認する。多くは次回定期保守まで様子見でよい（[`daily_operation.md`「5. DB Audit実行・確認」](daily_operation.md#5-db-audit実行確認)参照） |
| DB AuditがErrorになった | `personnel_sections`の複数parsed存在、`gold_records`のis_current重複・循環、FK整合性違反等、データ整合性に関わる項目が検出された | 直ちに[`incident_response.md`「6. DB Audit Error」](incident_response.md#6-db-audit-error)を確認し、[`db_repair_procedures.md`](db_repair_procedures.md)の該当手順で対応する |
| Pipelineが止まった | `jobs.status='running'`のまま残留している（プロセスクラッシュ等） | [`incident_response.md`「3. Job stuck」](incident_response.md#3-job-stuck)を参照する |
| Resumeとは何か | — | 既に成功した処理を再実行時に重複させず、既存の成果物を再利用する仕組み（Case A: Section単位、Case B: Record単位、Case C: parser_version更新時）。設計根拠は[ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md)、確認方法は[`daily_operation.md`「2. Resume動作の確認」](daily_operation.md#2-resume動作の確認)を参照 |
| Artifactはどこにあるか | — | GitHub Actions実行結果画面（対象のRun）の下部「Artifacts」欄に`db-audit-result`（`db_audit_result.json`）として保存される（保存期間30日）。詳細は[`daily_operation.md`「5. DB Audit実行・確認」](daily_operation.md#5-db-audit実行確認)を参照 |
| Summaryはどこで見るか | — | GitHub Actions実行結果画面（対象のRun）の上部に、監査対象DB・実行日時・ExitCode・判定・Error/Warning件数・検出項目一覧がMarkdown表として表示される |
| Backupは必要か | 自動バックアップは、アップロード時にFTPサーバ側で作成される`.bak`（1世代のみ）に限られ、複数世代の恒久保存は未実装 | 恒久的な保管が必要な場合は、[`backup_restore.md`「1. Backup」](backup_restore.md#1-backup)の手順で定期的に手動取得・保管することを推奨する |
| `workflow_dispatch`が実行できない | GitHub Actionsの仕様により、`workflow_dispatch`はデフォルトブランチ（`main`）上に存在するワークフローに対してのみ実行できる。feature branch上にのみ存在するワークフローファイルは対象にならない（Task35 Step4で確認済み） | `main`へのマージ後に実行可能になる。ワークフロー一覧・トリガーは[`.github/workflows/README.md`](../../.github/workflows/README.md)を参照 |

---

## 関連ドキュメント

- [`daily_operation.md`](daily_operation.md) — 日常運用
- [`incident_response.md`](incident_response.md) — 障害対応
- [`backup_restore.md`](backup_restore.md) — バックアップ・リストア
