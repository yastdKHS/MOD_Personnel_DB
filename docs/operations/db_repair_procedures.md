# DB Repair Procedures（Task34 Step4）

> **これは自動修復ツールではない。** `tools/db_audit.py`（[`db_audit.md`](db_audit.md)）が検出した異常について、**人手による判断・確認を前提とした手動修復手順**をまとめたものである。いかなる修復SQLも、監査ツールや他の自動化スクリプトから無条件に実行してはならない。
>
> **共通方針（[ADR-0006](../adr/0006-pipeline-provenance.md)）**: 本プロジェクトは業務データを物理削除しない設計思想を採る。したがって以下の修復手順は原則として`UPDATE`のみを用い、`DELETE`は使用しない。`DELETE`でしか対応できないと思われるケース（テスト用ダミーデータの混入等）に遭遇した場合は、本手順の対象外として個別にユーザーへ確認する。
>
> **共通の注意事項**:
> - 修復SQLを実行する前に、必ず対象行のバックアップ（DBファイル全体のスナップショット、または対象行のSELECT結果の保存）を取得する。
> - 修復SQLの`WHERE`句は、監査SQLで特定した**個別の`id`**に絞り込んで実行する。グループ全体に対する一括`UPDATE`は、意図しない行まで書き換えるリスクがあるため行わない。
> - 修復後は、対応する監査SQL（[`db_audit.md`](db_audit.md)のQ1〜Q15）を再実行し、0行になることを確認する。
> - 判断に迷う場合（どちらの行が正しいか機械的に決められない場合等）は、修復を実行せずユーザーに確認する。

## 目次

1. [personnel_sections: 複数parsed存在（Q1 / PS-1）](#1-personnel_sections-複数parsed存在q1--ps-1)
2. [personnel_sections: 孤立superseded（Q3 / PS-3）](#2-personnel_sections-孤立supersededq3--ps-3)
3. [candidate_records: pending取り残され（Q6 / CR-2）](#3-candidate_records-pending取り残されq6--cr-2)
4. [jobs: dangling running job（Q8 / J-1）](#4-jobs-dangling-running-jobq8--j-1)
5. [jobs: status/finished_at矛盾（Q9 / J-2）](#5-jobs-statusfinished_at矛盾q9--j-2)
6. [gold_records: is_current重複（Q11 / O-2）](#6-gold_records-is_current重複q11--o-2)
7. [gold_records: superseded_by循環（Q12 / O-3）](#7-gold_records-superseded_by循環q12--o-3)
8. [gold_records: superseded_by先が存在しない（Q13 / O-4）](#8-gold_records-superseded_by先が存在しないq13--o-4)
9. [review_changes: target_id整合しない（Q14 / O-5）](#9-review_changes-target_id整合しないq14--o-5)
10. [FK違反全般（Q4/Q5/Q10/Q15）](#10-fk違反全般q4q5q10q15)

---

## 1. personnel_sections: 複数parsed存在（Q1 / PS-1）

**監査項目**: 同一`(pdf_id, section_index)`に`status='parsed'`の行が2件以上存在する。

**原因**: Task33（`transaction()`導入）以前に、異なる`parser_version`による並行Case C実行がTOCTOU競合を起こし、両方の実行が`add_section()`に成功したケース（[ADR-0047「TOCTOU競合について（Task33で解消）」](../adr/0047-pipeline-resume-and-lineage-management-model.md)参照）。または、手動での`status`直接書き換えミス。

**修復前確認**:
1. 対象`(pdf_id, section_index)`グループの全行を`SELECT`し、各行の`parser_version_id`・`parser_versions.released_at`・`created_at`・`section_text`を比較する。
2. どの行を「現在有効なparsed行」として残すべきかを、実際に最新のコード・知識ベースで生成されたものかどうかまで含めて人手で判断する（`released_at`が新しい方が常に正しいとは限らない）。
3. 残さない行に紐づく`candidate_records`の状態（`validation_status`）も確認し、修復後に矛盾（項目3「pending取り残され」等）を新たに作らないか確認する。

**修復SQL**（残す1件以外の各行に対して個別に実行）:

```sql
UPDATE personnel_sections
SET status = 'superseded'
WHERE id = <残す行以外の該当id>
  AND status = 'parsed';
```

`WHERE status = 'parsed'`を必ず付ける（`SqliteCandidateRepository.supersede_section()`と同じ条件付きUPDATEパターンを踏襲し、多重実行時も安全にする）。

**修復後確認**:
- [`db_audit.md`](db_audit.md) Q1を再実行し0行になることを確認する。
- Q3（孤立superseded）も併せて再実行し、新たな孤立行を作っていないか確認する。

**注意事項**: どちらの行が正しいparsed行かは機械的に自動判定しない。誤った方をsupersededにすると、正しいデータが（物理削除はされないが）実運用上見えなくなる。判断に迷う場合はユーザーに確認する。

---

## 2. personnel_sections: 孤立superseded（Q3 / PS-3）

**監査項目**: `status='superseded'`だが、同一`(pdf_id, section_index)`に後継の`status='parsed'`行が存在しない。

**原因**: ADR-0047のCase C手順（`find_active_section`→`add_section`→`supersede_section`）が`add_section()`失敗後に中断した、あるいはTask33以前のTOCTOUによりデータが失われた可能性がある。

**修復方針**: 本来存在すべき「後継のparsed行」が失われている可能性が高い。**まず該当PDFをJobRunnerで再実行し、Case Cの正しい手順で新しいparsed行を追加することを優先する**（直接のUPDATEより安全）。既存のsuperseded行を単純にparsedへ戻す方法は、何が最新の正しい内容かを再構築できないため原則行わない。

**修復SQL**（section内容自体は変わっておらず、単なる取り消し操作のミスであると明確に判明した場合のみ、最終手段として使用）:

```sql
UPDATE personnel_sections
SET status = 'parsed'
WHERE id = <孤立していたsuperseded行のid>
  AND status = 'superseded';
```

**修復前確認**:
- 当該`pdf_id`/`section_index`に対応する`jobs`の実行履歴を確認し、なぜ後継が存在しないかを特定する。
- 実行SQL前に、[`db_audit.md`](db_audit.md) Q1（複数parsed検出）を実行し、対象グループに既に別のparsed行が存在しないことを確認する（存在する場合、statusを戻すと項目1の状態を新たに作ってしまう）。

**修復後確認**:
- Q3を再実行し0件になることを確認する。
- 可能であれば当該PDFをJobRunnerで再実行し、Case Cにより正しいlineageが再構築されることを確認する。

**注意事項**: `UNIQUE(pdf_id, section_index, parser_version_id)`制約により、他のparsed行と共存すると項目1の複数parsed状態を作り込む可能性がある。

---

## 3. candidate_records: pending取り残され（Q6 / CR-2）

**監査項目**: 親`personnel_sections.status='superseded'`なのに、配下の`candidate_records.validation_status='pending'`のまま残っている。

**原因**: Case Bのresumeロジック（`_process_record()`、`pipeline/job_runner.py`）は同一`parser_version_id`内でのみ`find_candidate()`を検索するため、supersedeされた旧versionのpending行は今後も自動的には拾われない。

**修復方針**: **原則としてSQLによる修復は行わない。** これらの行は「もう使われない」だけであり、Validatorを実際に通していない以上、`validation_status`を`passed`/`failed`へ機械的に更新することは検証を経ていない値を確定させることになり不適切である。ADR-0006の来歴保持方針に従い、そのまま保持する。

**修復前確認 / 修復後確認**: 該当なし（「修復しない」という判断自体を記録する）。

**注意事項**: 件数が多くなる場合は運用上のアーカイブ方針検討対象となる（[`docs/database/schema.md`「今後の検討事項」](../database/schema.md#今後の検討事項スコープ外)）。監査レポート上での注意喚起に留める。

---

## 4. jobs: dangling running job（Q8 / J-1）

**監査項目**: `status='running'`のまま既定閾値（既定24時間）を超えて経過している。

**原因**: プロセスクラッシュ・強制終了等により、`status`が`succeeded`/`failed`へ正常に遷移しなかった。

**修復前確認**: **必ず実行基盤（GitHub Actions等）側の実行履歴を確認し、当該jobに対応するプロセスが実際に終了していること**（まだ実行中でないこと）を確認する。実行中のjobを誤ってfailedにすると、二重実行やデータ不整合を招く可能性がある。

**修復SQL**:

```sql
UPDATE jobs
SET status = 'failed',
    finished_at = STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now'),
    error_summary = COALESCE(error_summary || ' / ', '')
                    || '[Repair] dangling running job manually closed'
WHERE id = <該当job id>
  AND status = 'running';
```

**修復後確認**: Q8・Q9を再実行し、対象行が消えていることを確認する。

**注意事項**: `error_summary`は追記する形にし、既存の値を上書きしない。

---

## 5. jobs: status/finished_at矛盾（Q9 / J-2）

**監査項目**: `status`と`finished_at`の対応関係が矛盾している（`running`なのに`finished_at`あり、または`succeeded`/`failed`なのに`finished_at`なし）。

**原因**: アプリケーションコードのバグ、または手動UPDATE。`SqliteJobRepository.update_status()`（`job.py`）の正常系実装では矛盾は発生しないため、通常は運用上の直接操作が疑われる。

**修復SQL**:

```sql
-- running なのに finished_at が設定されている場合
UPDATE jobs SET finished_at = NULL
WHERE id = <該当id> AND status = 'running';

-- succeeded/failed なのに finished_at が未設定の場合（現在時刻での補完は最終手段）
UPDATE jobs SET finished_at = STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')
WHERE id = <該当id> AND status IN ('succeeded', 'failed') AND finished_at IS NULL;
```

**修復前確認**: 可能な限り`logs/`配下の詳細ログから実際の完了時刻を復元できないか確認する。現在時刻での機械的な補完はログが失われている場合の最終手段とする。

**修復後確認**: Q9を再実行し0件になることを確認する。

**注意事項**: なし（軽微な監査項目）。

---

## 6. gold_records: is_current重複（Q11 / O-2）

**監査項目**: 同一`(person_key, effective_date)`について`is_current=1`の行が2件以上存在する。

**原因**: `SqliteGoldRepository.supersede()`の呼び出し漏れ、または並行実行競合（`GoldRepository`にはTask33の`transaction()`は導入されておらず、Task34のスコープ外として理論上のTOCTOUリスクが残っている点に注意）。

**修復方針**: 対象グループ内で、内容（`fields`）まで確認したうえで「実際に正しい最新の確定値」である1行のみを`is_current=1`として残し、他を`is_current=0`・`superseded_by`に残す行の`id`を設定する。

**修復SQL**（残す1件以外の各行に対して個別に実行）:

```sql
UPDATE gold_records
SET is_current = 0,
    superseded_by = <残す行のid>,
    valid_to = STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now')
WHERE id = <残す行以外の該当id>
  AND is_current = 1;
```

**修復前確認**: 対象グループの全バージョンを`SELECT`し、`version`番号だけでなく`fields`の内容・`valid_from`を比較して、どのバージョンが本当に正しい確定値かを判断する（`version`が大きい方が常に正しいとは限らない。誤った重複INSERTの可能性もある）。

**修復後確認**: Q11を再実行し0件になることを確認する。Q12（循環）・Q13（dangling）も併せて確認する。

**注意事項**: 対象が既に`exports`（公開データ）に含まれている場合、訂正の公開告知が別途必要になる可能性がある（運用判断、本手順のスコープ外）。

---

## 7. gold_records: superseded_by循環（Q12 / O-3）

**監査項目**: `superseded_by`の自己参照チェーンが循環している。

**原因**: `SqliteGoldRepository.supersede()`の通常実装は単方向のUPDATEのみであり、正常運用では発生しない。手動でのUPDATEミスや、複数ツールの混在使用が疑われる。

**修復方針**: **汎用的な修復SQLは提示しない。** 循環に含まれる全行の`fields`・`valid_from`・`valid_to`を比較し、実際の訂正履歴の意図（どれが最初でどれが最後か）を人手で復元したうえで、個別にUPDATEを設計する。

**修復前確認**: 循環を構成する全行を洗い出し、内容を精査する。

**修復後確認**: Q12を再実行し0件になることを確認する。

**注意事項**: 監査項目の中で最も深刻な破損パターンである。検出した場合は修復SQLを即座に実行せず、作業を停止してユーザーに報告する。

---

## 8. gold_records: superseded_by先が存在しない（Q13 / O-4）

**監査項目**: `superseded_by`が非NULLだが、参照先の`gold_records.id`が実在しない。

**原因**: 本来DELETEしない設計のため通常は起きないはずだが、`PRAGMA foreign_keys=ON`が有効化される前に投入されたデータ等で発生し得る。

**修復SQL**:

```sql
UPDATE gold_records
SET superseded_by = NULL
WHERE id = <該当id>
  AND superseded_by = <存在しない参照先id>;
```

`is_current`は変更しない（既に`0`のままにしておき、「supersedeされたが後継不明」という状態を明示する。何が最新かを再構築できないため、無理に`is_current=1`へ戻さない）。

**修復前確認**: `PRAGMA foreign_key_check`等で、本当に参照先が存在しないことを再確認する。

**修復後確認**: Q13を再実行し0件になることを確認する。

**注意事項**: `superseded_by`をNULLに戻しても「後継不明」を意味するだけで「現在有効」を意味しない。`is_current`の判定は別途Q11で確認する。

---

## 9. review_changes: target_id整合しない（Q14 / O-5）

**監査項目**: `target_table`+`target_id`の多態的参照が、実際のテーブルに存在しない。

**原因**: 対象レコード自体は物理削除されない設計のため通常は起きないはずだが、`target_table`の入力ミス等が疑われる。

**修復方針**: `target_table`の値そのものの入力ミスであれば、正しいテーブル名にUPDATEする。真に対象レコードが特定できない場合、`review_changes`は追記専用の監査証跡（[`docs/database/schema.md`](../database/schema.md) #7「`INSERT`のみ（追記専用。変更履歴自体を後から書き換えない）」）であるため、内容（`old_value`/`new_value`等）は書き換えず、原因調査の結果を別途記録するに留める。

**修復SQL**（`target_table`の入力ミスと判明した場合のみ）:

```sql
UPDATE review_changes
SET target_table = '<正しいtable名（candidate_records または gold_records）>'
WHERE id = <該当id>;
```

**修復前確認**: `review_sessions.reviewer`・実施時期（`created_at`）から、当時対象としていたレコードを人手で特定できるか調査する。

**修復後確認**: Q14を再実行し0件になることを確認する。

**注意事項**: `target_table`以外の列は原則書き換えない（追記専用ログの性質を壊さないため）。

---

## 10. FK違反全般（Q4/Q5/Q10/Q15）

**監査項目**: `personnel_sections`/`candidate_records`/`jobs`の個別FK、または`PRAGMA foreign_key_check`が検出する全テーブル横断のFK違反。

**原因**: `PRAGMA foreign_keys=ON`が有効化される前に投入されたデータ、または個別テーブルへの直接操作。

**修復方針**: 違反の内容（`table`・`parent`・`fkid`）に応じて、上記1〜9のうち該当する手順を適用する。上記のいずれにも該当しない未知のFK違反を検出した場合は、内容を精査したうえで個別にUPDATE方針をユーザーと相談する。汎用的な修復SQLはここでは提示しない（対象テーブルにより方針が異なるため）。

**修復前確認**: `PRAGMA foreign_key_check;`の出力（`table`, `rowid`, `parent`, `fkid`）を全て記録し、どのテーブル間の参照が壊れているかを特定する。

**修復後確認**: `PRAGMA foreign_key_check;`を再実行し、出力が空になることを確認する。

**注意事項**: なし（他項目の注意事項を参照）。
