# 障害対応（Runbook）

## 目的

運用担当者・管理者が、障害発生時に症状から原因候補・確認手順・復旧手順・エスカレーション基準を素早く参照できるようにする。個々の機構の設計根拠・修復SQLは本ドキュメントでは繰り返さず、既存資料をリンクする。

## 対象読者

運用担当者・管理者（P1はエスカレーション先として管理者の判断を要する）。

## 実施タイミング

障害発生時（GitHub Actionsの失敗通知、DB Audit Errorの検出、運用担当者からの報告等を契機とする）。

## 事前条件

[`daily_operation.md`](daily_operation.md)の日常確認を実施済みであること（多くの障害は日常確認の過程で発見される）。

---

## 優先度分類

| 優先度 | 基準 |
|---|---|
| **P1** | 公開データの正しさに関わる、またはPipeline全体が停止している。即対応・管理者へのエスカレーション必須 |
| **P2** | 影響範囲が限定的（一部PDF・一部ジョブ）。当日中の対応を目安とする |
| **P3** | 運用に支障はないが記録・監視すべき事象。次回定期保守での確認で足りる |

---

## 1. Pipeline失敗

**優先度**: P2（同時に多数のPDFが失敗する場合はP1へ格上げ）

- **症状**: `jobs.status='failed'`のジョブが存在する。
- **原因候補**: 個別PDFのパース失敗、一時的なリソース不足等。PDF単位で独立して失敗する設計のため、通常は他PDFへ波及しない。
- **確認手順**: 失敗したジョブの件数・対象PDFを確認する（多数のPDFが同時に失敗している場合はP1として扱う）。
- **復旧手順**: 再実行する（`run-pending`または`run-job <pdf_id>`）。Case A（Section単位Resume）により、既に成功した部分は再処理されない。
- **エスカレーション**: 同一PDFで再実行しても解消しない場合は「2. Resume失敗」へ。

## 2. Resume失敗

**優先度**: P2

- **症状**: PDFを再実行しても同じ失敗を繰り返す、または想定より処理件数が多い/少ない。
- **原因候補**: Case A/B/Cの前提（`(pdf_id, section_index)`ごとに`status='parsed'`は高々1件、[ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md)）が崩れている可能性。
- **確認手順**: `tools/db_audit.py`のQ1（複数parsed検出）・Q3（孤立superseded検出）を実行し、対象PDFに該当がないか確認する（実行方法は[`daily_operation.md`「5. DB Audit実行・確認」](daily_operation.md#5-db-audit実行確認)を参照）。
- **復旧手順**: 該当があれば「6. DB Audit Error」の手順に従い[`db_repair_procedures.md`](db_repair_procedures.md)の該当項目で修復する。
- **エスカレーション**: 原因が特定できない場合は管理者へ報告する。

## 3. Job stuck

**優先度**: P2

- **症状**: `jobs.status='running'`のまま長時間（既定24時間以上）経過している。
- **原因候補**: 実行プロセスの異常終了（クラッシュ、強制終了等）。
- **確認手順**: `tools/db_audit.py`のQ8（dangling running job検出）で検知する。
- **復旧手順**: [`db_repair_procedures.md`「4. jobs: dangling running job」](db_repair_procedures.md#4-jobs-dangling-running-jobq8--j-1)の手順に従う（実行基盤側で当該jobが本当に終了していることを確認してから対応する）。
- **エスカレーション**: 頻発する場合は管理者へ報告し、実行基盤側の安定性を確認する。

## 4. SQLite Busy

**優先度**: P3（頻発する場合はP2へ格上げ）

- **症状**: `sqlite3.OperationalError`（ロック競合によるタイムアウト）。
- **原因候補**: 異なるparser_versionによる並行Case C実行が、`transaction()`の`BEGIN IMMEDIATE`ロック取得で待機し、`busy_timeout`（5秒）を超えた。
- **確認手順**: 同時刻に複数の実行が重なっていないかをGitHub Actions実行履歴で確認する。
- **復旧手順**: 通常は一時的な競合であり、再実行で解消する。
- **エスカレーション**: 頻発する場合は管理者へ報告する。設計の詳細は[ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md)「TOCTOU競合について（Task33で解消）」を参照。

## 5. RepositoryError

**優先度**: P3（原因不明な頻発時はP2）

- **症状**: `RepositoryError`が発生する。
- **原因候補**: `UNIQUE`制約違反等、DB層で検出された整合性エラー。`JobRunner`の呼び出し境界で吸収され、クラッシュはしない設計になっている。
- **確認手順**: 対象PDF・Sectionを特定し、再実行で解消するか確認する。
- **復旧手順**: 通常は再実行（Resumeにより既存成果物を再利用）で解消する。
- **エスカレーション**: 同一箇所で繰り返し発生する場合は管理者へ報告する。

## 6. DB Audit Error

**優先度**: **P1**

- **症状**: `db_audit.yml`の実行結果がExitCode 2（Failure）。
- **原因候補**: `personnel_sections`の複数parsed存在・孤立superseded、`gold_records`のis_current重複・循環、`jobs`のstatus矛盾、FK整合性違反等（詳細は[`db_audit.md`「整合性チェックSQL」](db_audit.md#整合性チェックsqlstep2)を参照）。
- **確認手順**: Job Summaryで検出項目（Error件数・該当ID）を確認し、Artifact（`db_audit_result.json`）で該当行の詳細を確認する（[`daily_operation.md`「5. DB Audit実行・確認」](daily_operation.md#5-db-audit実行確認)参照）。
- **復旧手順**: [`db_repair_procedures.md`](db_repair_procedures.md)には、Errorに分類される検出項目（Q1・Q3・Q4・Q5・Q7・Q9・Q10・Q11・Q12・Q13・Q14・Q15）ごとの手順が1〜10の項目としてまとめられている。Job Summary・Artifactで確認したチェックIDに対応する項目に従い手動修復する。**自動修復ツールではない**ため、必ず修復前確認を行ってから実施する。
- **エスカレーション**: 修復方針の判断に迷う場合（どちらの行が正しいか等）は、修復を実施せず管理者へ確認する。

## 7. GitHub Actions失敗

**優先度**: `scheduler.yml`の失敗はP1〜P2、その他（`ci.yml`/`nightly.yml`/`release.yml`）はP3

- **症状**: ワークフロー実行が赤（Failure）。
- **原因候補**: FTP接続失敗、ネットワーク到達性、Secrets未設定等（DB Auditの検出結果に起因する失敗は「6. DB Audit Error」を参照、本項目は実行基盤側の失敗を対象とする）。
- **確認手順**: 実行ログを確認する。FTP関連の失敗は[`release.md`「障害時の確認項目」](release.md#障害時の確認項目)のチェックリストに従う。
- **復旧手順**: Secrets登録状況・ネットワーク到達性・認証情報を確認し是正後、「Run workflow」（`workflow_dispatch`）で再実行する。
- **エスカレーション**: `scheduler.yml`の失敗（本番Pipelineが定期実行されない状態）が解消しない場合は速やかに管理者へ報告する。

---

## 関連ドキュメント

- [`daily_operation.md`](daily_operation.md) — 日常運用
- [`db_repair_procedures.md`](db_repair_procedures.md) — DB内容レベルの修復手順
- [`db_audit.md`](db_audit.md) — DB監査項目・整合性チェックSQLの設計根拠
- [`release.md`](release.md) — FTP障害時の確認項目・Recovery・Rollback
- [`backup_restore.md`](backup_restore.md) — バックアップ・リストア
- [ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md) — Resume・TOCTOU対応の設計根拠
