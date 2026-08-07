# バックアップ・リストア（Runbook）

## 目的

DBのバックアップ取得・復元を、運用担当者が実施する順番で示す。単なるコマンド一覧ではなく、`Backup → Restore → DB Audit → Pipeline Resume確認 → 正常確認`という一連の流れとして構成する。既存の設計・詳細手順（FTP `.bak`のAtomic upload復旧、Backup/Disaster Recoveryのポリシー）は本ドキュメントでは繰り返さず、[`release.md`](release.md)を参照する。

## 対象読者

システム管理者（FTP Secretsへのアクセス、DBファイルの取得・書き戻しを伴うため）。

## 実施タイミング

定期バックアップ取得時、または障害復旧時。

## 事前条件

- FTP関連Secrets（`MOD_PERSONNEL_DB_FTP__*`等）にアクセスできる、または対応する環境変数を設定できること。
- `--db-path`・`--knowledge-root`・`--layouts-root`を把握していること（構文は[`README.md`「CLI使用方法」](../../README.md#cli使用方法)を参照）。

---

## 運用フロー全体図

```
Backup
  ↓
Restore
  ↓
DB Audit
  ↓
Pipeline Resume確認
  ↓
正常確認
```

---

## 1. Backup

**実施手順**:
1. `download-db`で本番DBを取得する。

   ```bash
   python -m mod_personnel_db.cli \
     --db-path <db-path> --knowledge-root <knowledge-root> --layouts-root <layouts-root> \
     download-db <remote_path>
   ```
2. 取得した`<db-path>`のファイルを、任意の保管場所（バージョン管理された保管庫等）へコピーし、取得日時が分かる形で保存する。

**既知の制限（正直に明記）**: 自動バックアップは、`upload-db`実行時にFTPサーバ側で作成される`.bak`（1世代のみ、[`release.md`「Backup方針」](release.md#production-ftp運用)を参照）に限られる。複数世代の恒久的な自動バックアップは未実装（[`release.md`「Backup」](release.md#backup)節が「保持世代: 実装時に確定」としたまま）。本ドキュメントはこの設計を変更しないため、恒久的な保管が必要な場合は、上記手順による定期的な手動取得を運用担当者が実施する。

**正常終了条件**: `download-db`が終了コード0で完了し、保存先にファイルが存在すること。

**異常時対応**: FTP接続に失敗する場合は[`incident_response.md`「7. GitHub Actions失敗」](incident_response.md#7-github-actions失敗)、または[`release.md`「障害時の確認項目」](release.md#障害時の確認項目)を参照する。

## 2. Restore

### ケースA: FTPサーバ側`.bak`からの復旧

Atomic upload障害等で正式DBファイルに問題があり、直近の`.bak`から復旧する場合。手順は[`release.md`「Atomic upload障害時の復旧手順」](release.md#atomic-upload障害時の復旧手順task19-7)（3ケース）を参照し、本ドキュメントでは複製しない。

### ケースB: 手動保存したバックアップからの復旧

上記「1. Backup」で保存しておいたDBファイルから復元する場合。

**実施手順**:
1. 保管しておいたDBファイルを、復元先の`<db-path>`に配置する。
2. `upload-db`でFTPサーバへ書き戻す。

   ```bash
   python -m mod_personnel_db.cli \
     --db-path <db-path> --knowledge-root <knowledge-root> --layouts-root <layouts-root> \
     upload-db <remote_path>
   ```

   `upload-db`はアップロード前に`PRAGMA integrity_check`でローカルDBの健全性を検証し、異常があればFTP通信自体を行わない（詳細は[`release.md`「Production FTP運用」](release.md#production-ftp運用)の「Atomic upload方式」節を参照）。

**正常終了条件**: `upload-db`が終了コード0で完了すること。

**異常時対応**: `integrity_check`で異常が検出された場合は、別世代のバックアップを試す。FTP転送自体の失敗は「1. Backup」の異常時対応を参照。

## 3. DB Audit

**実施手順**: 復元したDBに対し、[`daily_operation.md`「5. DB Audit実行・確認」](daily_operation.md#5-db-audit実行確認)の手順で`db_audit.yml`を`workflow_dispatch`実行し、ExitCodeを確認する。

**正常終了条件**: ExitCode 0または1（Warningのみ）。

**異常時対応**: ExitCode 2（Error）の場合は、次の「4. Pipeline Resume確認」へ進まず、[`incident_response.md`「6. DB Audit Error」](incident_response.md#6-db-audit-error)の手順に従う。

## 4. Pipeline Resume確認

**実施手順**: 復元後のDBに対し、`run-pending`または`schedule-now run_pending_pipeline`を実行し、エラーなく完了することを確認する（[`daily_operation.md`「2. Resume動作の確認」](daily_operation.md#2-resume動作の確認)と同じ考え方を、復元直後に適用する）。

**正常終了条件**: 実行が終了コード0で完了すること。

**異常時対応**: 同じ失敗を繰り返す場合は[`incident_response.md`「2. Resume失敗」](incident_response.md#2-resume失敗)を参照する。

## 5. 正常確認

**総合チェックリスト**:
- [ ] DB Auditを再実行し、ExitCode 0または1であること。
- [ ] `jobs`テーブルの直近実行が`succeeded`であること。
- [ ] 復元前後で想定した対象範囲のデータが一致していること（必要に応じてゴールデンファイルテスト等で確認する）。

---

## 関連ドキュメント

- [`release.md`](release.md) — Backup/Disaster Recoveryのポリシー、Atomic upload障害時の復旧手順
- [`README.md`](../../README.md) — `download-db`/`upload-db`のCLI構文、FTP DB同期フロー
- [`daily_operation.md`](daily_operation.md) — DB Audit実行・確認方法、Resume動作の確認
- [`incident_response.md`](incident_response.md) — 障害対応
- [`db_repair_procedures.md`](db_repair_procedures.md) — DB内容レベルの修復手順
