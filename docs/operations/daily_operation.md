# 日常運用（Runbook）

## 目的

運用担当者が日次・定期で行う確認作業（Pipeline実行状況・Resume・Scheduler・GitHub Actions・DB監査）をまとめる。個々の機構の設計根拠・実装詳細は本ドキュメントでは繰り返さず、既存資料をリンクする。

## 対象読者

運用担当者。

## 実施タイミング

毎営業日、または定期保守（週次・月次）のタイミング。

## 事前条件

- GitHub Actionsの実行結果を閲覧できるリポジトリアクセス権を持つこと。
- CLI操作を行う場合は`--db-path`・`--knowledge-root`・`--layouts-root`を実行環境に応じて把握していること（構文は[`README.md`「CLI使用方法」](../../README.md#cli使用方法)を参照）。

---

## 1. Pipeline実行状況の確認

**実施手順**:
1. GitHub Actionsの「Actions」タブ →「Scheduler」ワークフローを開き、直近の実行（`schedule: cron`による自動実行、毎日08:45 UTC）が成功しているかを確認する。
2. 待たずに確認したい場合は「Run workflow」（`workflow_dispatch`）から即時実行できる（詳細は[`README.md`「手動実行方法」](../../README.md#手動実行方法)を参照）。

**正常終了条件**: 対象Runが緑（Success）で完了していること。

**異常時対応**: 赤（Failure）の場合は[`incident_response.md`「1. Pipeline失敗」](incident_response.md#1-pipeline失敗)を参照する。

## 2. Resume動作の確認

Resume（同一parser_version内での再開: Case A/B、parser_version更新後の再解析: Case C）は`JobRunner`内部で透過的に動作する仕組みであり、「Resumeが今回発生したかどうか」を直接表示する専用のCLI・画面は存在しない。以下を間接的な確認手段とする。

**実施手順**:
1. 同一PDFに対する再実行（`run-pending`や`schedule-now run_pending_pipeline`の再起動）がエラーなく完了することを確認する。
2. `tools/db_audit.py`のQ1（`personnel_sections`の複数parsed検出）が0件であることを確認する（実行方法は下記「5. DB Audit実行・確認」を参照）。これは、Resumeの前提となる不変条件（`(pdf_id, section_index)`ごとに`status='parsed'`は高々1件）が保たれていることの確認である。

**正常終了条件**: 再実行がエラーなく完了し、Q1が0件であること。

**異常時対応**: 同じ失敗を繰り返す場合は[`incident_response.md`「2. Resume失敗」](incident_response.md#2-resume失敗)を参照する。Resumeの設計根拠（Case A/B/C）は[ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md)を参照。

## 3. Scheduler確認

**実施手順**: cron実行結果の確認・手動実行方法は[`README.md`「Scheduler運用（GitHub Actions）」](../../README.md#scheduler運用github-actions)、運用フロー全体（GitHub Actions → `schedule-now` → `Scheduler` → `JobOrchestrator`）は[`release.md`「Scheduler運用フロー」](release.md#scheduler運用フローgithub-actions--schedule-now--scheduler--joborchestrator)を参照する（本ドキュメントでは重複記載しない）。

**正常終了条件・異常時対応**: 上記リンク先を参照。

## 4. GitHub Actions確認

**実施手順**: 「Actions」タブで、以下5ワークフローの直近の実行結果を確認する（トリガー・役割の一覧は[`.github/workflows/README.md`](../../.github/workflows/README.md)を参照）。

| ワークフロー | 確認頻度の目安 |
|---|---|
| `ci.yml` | PRごと（自動） |
| `nightly.yml` | 毎日 |
| `release.yml` | リリース時 |
| `scheduler.yml` | 毎日 |
| `db_audit.yml` | 毎日（下記「5. DB Audit実行・確認」参照） |

**正常終了条件**: いずれも緑（Success）。

**異常時対応**: 赤（Failure）の場合は[`incident_response.md`「7. GitHub Actions失敗」](incident_response.md#7-github-actions失敗)を参照する。

## 5. DB Audit実行・確認

Task35で追加した`db_audit.yml`の運用担当者向け利用方法。監査項目・SQLの設計根拠は[`db_audit.md`](db_audit.md)を参照し、本節では繰り返さない。

**実施手順**:
1. 「Actionsタブ →「DB Audit」ワークフロー →「Run workflow」」で即時実行できる（`schedule`により毎日09:15 UTCにも自動実行される）。
2. **Job Summaryの確認**: 対象のRunを開くと、画面上部に監査対象DB・実行日時・ExitCode・判定・Error/Warning件数・検出項目一覧がMarkdown表として表示される。
3. **Artifactの確認**: 対象のRunを開き、画面下部の「Artifacts」欄から`db-audit-result`（`db_audit_result.json`、保存期間30日）をダウンロードして詳細な検出内容（該当行）を確認できる。

**正常終了条件・異常時対応（ExitCode別）**:

| ExitCode | Job判定 | 対応 |
|---|---|---|
| 0 | Success | 対応不要 |
| 1 | Success（Warningのみ） | Job Summaryの内容を確認し、内容によっては次回定期保守まで様子見でよい（[`faq.md`](faq.md)「DB AuditがWarningになった」も参照） |
| 2 | Failure | 直ちに[`incident_response.md`「6. DB Audit Error」](incident_response.md#6-db-audit-error)を参照し対応する |

## 6. 定期保守チェックリスト

| 頻度 | 確認項目 |
|---|---|
| 週次 | DB Audit結果の傾向確認（Warningの頻発有無） |
| 月次 | Artifact保持状況（retention-days 30、古いArtifactは自動削除される）、GitHub Actions実行履歴に異常な傾向がないかの確認 |

---

## 関連ドキュメント

- [`README.md`](../../README.md) — CLI使用方法・Scheduler運用（GitHub Actions）
- [`release.md`](release.md) — Scheduler運用フロー・Production FTP運用
- [`db_audit.md`](db_audit.md) — DB監査項目・整合性チェックSQLの設計根拠
- [`db_repair_procedures.md`](db_repair_procedures.md) — 異常検知時の手動修復手順
- [`.github/workflows/README.md`](../../.github/workflows/README.md) — 5ワークフローの一覧・トリガー
- [`incident_response.md`](incident_response.md) — 障害対応
- [ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md) — Resume（Case A/B/C）・TOCTOU対応の設計根拠
