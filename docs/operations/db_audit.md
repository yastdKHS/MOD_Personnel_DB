# DB監査（Task34）

> **位置づけ**: 本ドキュメントは、運用・保守フェーズ（Task33完了後）における DB整合性監査の設計文書である。[`docs/database/schema.md`](../database/schema.md) の物理スキーマ、[ADR-0006](../adr/0006-pipeline-provenance.md)（来歴管理）、[ADR-0047](../adr/0047-pipeline-resume-and-lineage-management-model.md)（Resume/Lineage管理）を根拠とする。監査対象はSQLite DBファイルであり、監査そのものはRead Only（SELECT/PRAGMAのみ）で行う。異常検知時の修復手順は別文書 [`db_repair_procedures.md`](db_repair_procedures.md) を参照（自動修復は行わない）。

## 目次

1. [監査項目一覧（Step1）](#監査項目一覧step1)
2. [整合性チェックSQL（Step2）](#整合性チェックsqlstep2)
3. [DB監査ツール](#db監査ツール)
4. [GitHub Actionsによる自動実行（Task35）](#github-actionsによる自動実行task35)
5. [Migration不要確認（Step5）](#migration不要確認step5)
6. [関連文書](#関連文書)

---

## 監査項目一覧（Step1）

### 用語の対応について

依頼文中の「personnel_records」は、実スキーマ上のテーブル名 `candidate_records` を指すものとして扱う（`docs/database/schema.md` の12業務テーブルに `personnel_records` という名前のテーブルは存在しない）。以降、実テーブル名 `candidate_records` で統一する。

### personnel_sections

| # | 項目 | 保証すべき内容 | 根拠 |
|---|---|---|---|
| PS-1 | parsedが複数存在しない | 同一 `(pdf_id, section_index)` について `status='parsed'` の行は高々1件 | ADR-0047「5. 設計前提（Resume系APIの不変条件）」 |
| PS-2 | lineageが循環していない（※注記あり） | `personnel_sections` は `superseded_by` のような自己参照ポインタ列を持たない（`status` フラグのみ、schema.md #3）ため、構造上の循環は発生し得ない。代わりに「新旧の逆転」（新しい`parser_version`の行が`superseded`のまま、古い`parser_version`の行が`parsed`のまま）という論理的な矛盾がないかを監査する | ADR-0047「add_section前にfind_active_sectionを呼ぶ理由」が前提とする時系列順序 |
| PS-3 | superseded先が存在する | `status='superseded'` の行が存在するなら、同一 `(pdf_id, section_index)` に現在アクティブな `status='parsed'` の行が存在すること（後継のいない孤立supersede行の検出） | ADR-0047 Case C手順（`find_active_section`→`add_section`→`supersede_section`の一連の流れが正しく完了していれば必ず後継が存在する） |
| PS-4 | parser_version整合 | `parser_version_id` が `parser_versions.id` に存在すること | schema.md #3 外部キー定義 |
| PS-5 | pdf_id整合 | `pdf_id` が `pdfs.id` に存在すること | schema.md #3 外部キー定義 |
| PS-6 | layout_id整合（追加項目） | `layout_id` が `layouts.id` に存在すること | schema.md #3 外部キー定義 |

**PS-2について**: 依頼文の「lineageが循環していない」を文字通り検証できるのは、後述の `gold_records`（明示的な自己参照FK `superseded_by` を持つ）である。`personnel_sections` には同等の列がないため、本ADRで保証すべき実質的な内容として「新旧の時系列逆転がないか」に読み替えている。この読み替えの妥当性に疑義がある場合は実装前にユーザーへ確認する。

### candidate_records

| # | 項目 | 保証すべき内容 | 根拠 |
|---|---|---|---|
| CR-1 | section_id存在確認 | `personnel_section_id` が `personnel_sections.id` に存在すること | schema.md #4 外部キー定義 |
| CR-2 | pending/parsed整合 | 親 `personnel_sections.status='superseded'` であるにもかかわらず、配下の `candidate_records.validation_status='pending'` のまま取り残されている行がないこと（Case Bのresumeは同一`parser_version_id`内でのみ`find_candidate`を検索するため、supersedeされた旧versionのpending行は二度と拾われない） | ADR-0047「3. Case B: Record単位Resume」の検索範囲、`_process_record()`実装（`pipeline/job_runner.py`） |
| CR-3 | lineage整合 | `candidate_records.parser_version_id` が、親 `personnel_sections.parser_version_id` と一致すること（Repository実装上一致するはずだが、構造的な制約列を持たないため監査で保険的に確認する） | `SqliteCandidateRepository.add_raw()`（`self._parser_version_id`を内部で使う設計） |
| CR-4 | UNIQUE整合（参考） | `(personnel_section_id, record_index, parser_version_id)` の重複がないこと | schema.md #4 一意制約（DB自体が`UNIQUE`制約で保証するため、監査SQLでの再確認は必須ではないが`PRAGMA integrity_check`相当の網羅性のため含める） |

### jobs

| # | 項目 | 保証すべき内容 | 根拠 |
|---|---|---|---|
| J-1 | dangling job確認 | `status='running'` のまま異常に長時間（既定閾値24時間）経過している行がないこと（プロセスクラッシュ等による取り残しの検知） | ADR-0019（再実行はGitHub Actionsのリトライに委ねる設計のため、クラッシュ後に取り残された`running`行はアプリケーション側では誰も遷移させない） |
| J-2 | status整合 | `status='running'` なのに `finished_at` が設定済み、または `status IN ('succeeded','failed')` なのに `finished_at` が未設定、という矛盾がないこと | `SqliteJobRepository.update_status()`（`job.py`）の実装が正常系で保証する対応関係 |
| J-3 | pdf_id / parser_version_id整合 | 非NULLの場合、それぞれ `pdfs.id` / `parser_versions.id` に存在すること | schema.md #12 外部キー定義（いずれもnullable） |

### その他（Repository契約・Schema制約から保証される整合性）

| # | 項目 | 保証すべき内容 | 根拠 |
|---|---|---|---|
| O-1 | 全テーブル横断FK整合性 | 全テーブルの外部キー参照に破損がないこと | SQLite組み込み `PRAGMA foreign_key_check`。PS-4/PS-5/PS-6/CR-1/J-3の個別チェックを横断的に補完する網羅チェック |
| O-2 | gold_records: is_current高々1件 | 同一 `(person_key, effective_date)` について `is_current=1` の行は高々1件 | schema.md #5「訂正時は…旧バージョンの`is_current`を0に」 |
| O-3 | gold_records: superseded_by循環していない | `superseded_by` の自己参照チェーンに循環がないこと（`gold_records`は`personnel_sections`と異なり実際に自己参照FK`superseded_by`を持つため、「循環」を文字通り検証できる） | schema.md #5 外部キー定義（自己参照）、`SqliteGoldRepository.supersede()` |
| O-4 | gold_records: superseded_by先が存在する | `superseded_by` が非NULLの場合、参照先の `gold_records.id` が実在すること | schema.md #5 外部キー定義 |
| O-5 | review_changes: 多態的target_idの整合性 | `target_table`（`candidate_records`または`gold_records`）に応じて、`target_id` が該当テーブルに実在すること。schema.mdが明記するとおりSQLiteのFK機能では検証できず「アプリケーション層の責務」とされている箇所であり、DB層のFK制約だけでは検出できない | schema.md #7「設計メモ（多態的参照について）」 |
| O-6 | knowledge_items UNIQUE整合 | `(category, item_key, effective_from)` の重複がないこと | schema.md #8 一意制約（DB制約で保証済み、監査SQL不要。参考記載のみ） |
| O-7 | JSON列の構文妥当性 | `raw_fields` / `normalized_fields` / `normalization_applied` / `fields` / `target_scope` が妥当なJSONであること | schema.md 全体の設計方針「JSON列」（`CHECK (json_valid(...))` によりDB制約で保証済み、監査SQL不要。参考記載のみ） |

O-6・O-7は `CHECK` 制約によりDB層で常に保証されるため、Step2の監査SQL一覧には含めない（`PRAGMA integrity_check` 相当の一般的なDBファイル破損確認で代替できる）。

---

## 整合性チェックSQL（Step2）

要求どおり、以下は全て **SQLiteのみ・SELECT/PRAGMAのみ・UPDATE禁止・DELETE禁止** である。`tools/db_audit.py`（後述）はこれらのSQLをそのまま実行する。

### Q1（PS-1）: personnel_sectionsの複数parsed検出

```sql
SELECT pdf_id, section_index, COUNT(*) AS parsed_count
FROM personnel_sections
WHERE status = 'parsed'
GROUP BY pdf_id, section_index
HAVING COUNT(*) > 1;
```

- **目的**: ADR-0047の不変条件（`(pdf_id, section_index)`ごとに`parsed`は高々1件）が破られていないかを確認する。
- **正常時**: 0行。
- **異常時**: 該当する `pdf_id` / `section_index` と重複件数が返る。Task33以前（`transaction()`導入前）の並行Case C実行によるTOCTOU競合、または手動でのstatus書き換えが疑われる。**Severity: Error**。

### Q2（PS-2）: personnel_sectionsの新旧逆転検出

```sql
SELECT s_old.id AS parsed_id, s_old.pdf_id, s_old.section_index,
       pv_old.released_at AS parsed_released_at,
       s_new.id AS superseded_id, pv_new.released_at AS superseded_released_at
FROM personnel_sections s_old
JOIN parser_versions pv_old ON pv_old.id = s_old.parser_version_id
JOIN personnel_sections s_new
    ON s_new.pdf_id = s_old.pdf_id
   AND s_new.section_index = s_old.section_index
   AND s_new.status = 'superseded'
JOIN parser_versions pv_new ON pv_new.id = s_new.parser_version_id
WHERE s_old.status = 'parsed'
  AND pv_new.released_at > pv_old.released_at;
```

- **目的**: 現在`parsed`な行より新しい`parser_version`の行が`superseded`のまま残っている（時系列の逆転）がないかを確認する。
- **正常時**: 0行。
- **異常時**: 逆転しているペアが返る。正常なCase Cフローでは発生しないため、手動操作や過去データ移行時の混入が疑われる。**Severity: Warning**（データ破損とは断定できないため）。

### Q3（PS-3）: personnel_sectionsの孤立superseded検出

```sql
SELECT s.id, s.pdf_id, s.section_index, s.parser_version_id
FROM personnel_sections s
WHERE s.status = 'superseded'
  AND NOT EXISTS (
      SELECT 1 FROM personnel_sections p
      WHERE p.pdf_id = s.pdf_id
        AND p.section_index = s.section_index
        AND p.status = 'parsed'
  );
```

- **目的**: `superseded`にもかかわらず、後継となる`parsed`行が同一グループに存在しない「後継なきsupersede」を検出する。
- **正常時**: 0行。
- **異常時**: 孤立した行のIDが返る。ADR-0047のCase C手順（`find_active_section`→`add_section`→`supersede_section`）が完了する前に中断した、あるいはTask33以前のTOCTOUによりデータが失われた可能性がある。**Severity: Error**。

### Q4（PS-4/PS-5/PS-6）: personnel_sectionsのFK整合性

```sql
SELECT ps.id, ps.pdf_id, ps.parser_version_id, ps.layout_id
FROM personnel_sections ps
LEFT JOIN pdfs p ON p.id = ps.pdf_id
LEFT JOIN parser_versions pv ON pv.id = ps.parser_version_id
LEFT JOIN layouts l ON l.id = ps.layout_id
WHERE p.id IS NULL OR pv.id IS NULL OR l.id IS NULL;
```

- **目的**: `pdf_id` / `parser_version_id` / `layout_id` の参照先が実在するかを確認する。
- **正常時**: 0行。
- **異常時**: 参照切れの行が返る。`PRAGMA foreign_keys=ON`が有効化される前に投入されたデータ等が疑われる。**Severity: Error**。

### Q5（CR-1）: candidate_recordsのsection_id存在確認

```sql
SELECT cr.id, cr.personnel_section_id
FROM candidate_records cr
LEFT JOIN personnel_sections ps ON ps.id = cr.personnel_section_id
WHERE ps.id IS NULL;
```

- **目的**: `candidate_records.personnel_section_id` の参照先が実在するかを確認する。
- **正常時**: 0行。
- **異常時**: 参照切れの行が返る。**Severity: Error**。

### Q6（CR-2）: candidate_recordsのpending取り残され検出

```sql
SELECT cr.id, cr.personnel_section_id, cr.validation_status, ps.status AS section_status
FROM candidate_records cr
JOIN personnel_sections ps ON ps.id = cr.personnel_section_id
WHERE cr.validation_status = 'pending'
  AND ps.status = 'superseded';
```

- **目的**: supersedeされた旧Section配下に、検証未完了（`pending`）のまま取り残されたレコードがないかを確認する。
- **正常時**: 0行。
- **異常時**: 取り残されたレコードのIDが返る。Case Bのresumeロジックは新versionの`find_candidate`しか検索しないため、これらは今後も自動的には拾われない「幽霊pending」である。**Severity: Warning**（データ破損ではなく、単に処理が確定しないまま来歴として残っているだけであるため）。

### Q7（CR-3）: candidate_recordsのlineage不整合検出

```sql
SELECT cr.id, cr.parser_version_id AS record_version, ps.parser_version_id AS section_version
FROM candidate_records cr
JOIN personnel_sections ps ON ps.id = cr.personnel_section_id
WHERE cr.parser_version_id != ps.parser_version_id;
```

- **目的**: 子レコードの`parser_version_id`が親Sectionのものと一致しているかを確認する。
- **正常時**: 0行。
- **異常時**: 不一致の行が返る。現行Repository実装では構造的に発生しないはずだが、保険的に監査する。**Severity: Error**。

### Q8（J-1）: jobsのdangling running job検出

```sql
SELECT id, job_type, pdf_id, started_at
FROM jobs
WHERE status = 'running'
  AND started_at < STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now', '-24 hours');
```

- **目的**: 異常に長時間`running`のまま放置されているjobを検出する（閾値は`tools/db_audit.py`の`--stale-running-hours`で変更可能、既定24時間）。
- **正常時**: 0行。
- **異常時**: 該当jobの行が返る。プロセスクラッシュ等によりステータス遷移しなかった疑いがある。**Severity: Warning**。

### Q9（J-2）: jobsのstatus/finished_at矛盾検出

```sql
SELECT id, status, finished_at
FROM jobs
WHERE (status = 'running' AND finished_at IS NOT NULL)
   OR (status IN ('succeeded', 'failed') AND finished_at IS NULL);
```

- **目的**: `status`と`finished_at`の対応関係の矛盾を検出する。
- **正常時**: 0行。
- **異常時**: 矛盾する行が返る。**Severity: Error**。

### Q10（J-3）: jobsのFK整合性

```sql
SELECT j.id, j.pdf_id, j.parser_version_id
FROM jobs j
LEFT JOIN pdfs p ON p.id = j.pdf_id
LEFT JOIN parser_versions pv ON pv.id = j.parser_version_id
WHERE (j.pdf_id IS NOT NULL AND p.id IS NULL)
   OR (j.parser_version_id IS NOT NULL AND pv.id IS NULL);
```

- **目的**: nullable な `pdf_id` / `parser_version_id` について、非NULLの場合の参照整合性を確認する。
- **正常時**: 0行。
- **異常時**: 参照切れの行が返る。**Severity: Error**。

### Q11（O-2）: gold_recordsのis_current重複検出

```sql
SELECT person_key, effective_date, COUNT(*) AS current_count
FROM gold_records
WHERE is_current = 1
GROUP BY person_key, effective_date
HAVING COUNT(*) > 1;
```

- **目的**: 同一`(person_key, effective_date)`について`is_current=1`が高々1件であることを確認する。
- **正常時**: 0行。
- **異常時**: 重複しているグループが返る。**Severity: Error**。

### Q12（O-3）: gold_recordsのsuperseded_by循環検出

```sql
WITH RECURSIVE chain(start_id, current_id, depth) AS (
    SELECT id, superseded_by, 1
    FROM gold_records
    WHERE superseded_by IS NOT NULL
    UNION ALL
    SELECT chain.start_id, gr.superseded_by, chain.depth + 1
    FROM chain
    JOIN gold_records gr ON gr.id = chain.current_id
    WHERE chain.current_id IS NOT NULL AND chain.depth < 1000
)
SELECT DISTINCT start_id
FROM chain
WHERE current_id = start_id;
```

- **目的**: `superseded_by`の自己参照チェーンをたどり、始点に戻ってくる（循環している）行がないかを確認する。`personnel_sections`にはない、`gold_records`固有の明示的な自己参照FKに対する検証。
- **正常時**: 0行。
- **異常時**: 循環の起点となる`id`が返る。`SqliteGoldRepository.supersede()`の通常の実行では発生しないはずであり、手動UPDATE等が疑われる。**Severity: Error**（最も深刻）。

### Q13（O-4）: gold_recordsのsuperseded_by先が存在しない検出

```sql
SELECT gr.id, gr.superseded_by
FROM gold_records gr
LEFT JOIN gold_records target ON target.id = gr.superseded_by
WHERE gr.superseded_by IS NOT NULL
  AND target.id IS NULL;
```

- **目的**: `superseded_by`の参照先が実在するかを確認する。
- **正常時**: 0行。
- **異常時**: 参照切れの行が返る。**Severity: Error**。

### Q14（O-5）: review_changesの多態的target_id整合性検出

```sql
SELECT rc.id, rc.target_table, rc.target_id
FROM review_changes rc
WHERE (rc.target_table = 'candidate_records'
       AND NOT EXISTS (SELECT 1 FROM candidate_records cr WHERE cr.id = rc.target_id))
   OR (rc.target_table = 'gold_records'
       AND NOT EXISTS (SELECT 1 FROM gold_records gr WHERE gr.id = rc.target_id));
```

- **目的**: SQLiteのFK機構では検証できない多態的参照（`target_table`+`target_id`）の整合性を確認する。
- **正常時**: 0行。
- **異常時**: 参照切れの行が返る。**Severity: Error**。

### Q15（O-1）: 全テーブル横断FK整合性

```sql
PRAGMA foreign_key_check;
```

- **目的**: 全12業務テーブルの外部キー参照を一括で検証する、SQLite組み込みの網羅チェック。Q4/Q5/Q10/Q13で個別に確認済みの内容を含むが、見落としに対する保険として実行する。
- **正常時**: 0行。
- **異常時**: `(table, rowid, parent, fkid)`の組が返る。**Severity: Error**。

---

## DB監査ツール

`tools/db_audit.py`（Step3実装）は上記Q1〜Q15を実行するRead OnlyのCLIツールである。使用方法・終了コード・JSON出力の詳細は `tools/db_audit.py` 冒頭のdocstring、および以下を参照。

```
python tools/db_audit.py [--db-path DB/personnel.db] [--json] [--stale-running-hours 24]
```

- **Read Only**: DB接続を `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` で開き、SQLite自体にWrite操作を拒否させる（アプリケーションコードの規約違反だけでなく、接続レベルで保証する）。
- **Repository経由不要**: 監査は業務ロジック（`JobRunner`・各Repository実装）を一切呼び出さず、`sqlite3`標準ライブラリでQ1〜Q15を直接実行する。
- **終了コード**: `0`=問題なし、`1`=Warningのみ、`2`=Errorを含む（Errorが1件でもあれば`2`を優先する）。
- **CandidateRepository.transaction()との関係**: 監査ツールは読み取り専用であり、`transaction()`（Case Cの書き込み専用境界）を一切使用しない。Repository契約・JobRunner・Case A/B/Cの実装には変更を加えていない。

---

## GitHub Actionsによる自動実行（Task35）

`tools/db_audit.py`は、[`.github/workflows/db_audit.yml`](../../.github/workflows/db_audit.yml)により`schedule`（毎日09:15 UTC）・`workflow_dispatch`で定期・手動実行される。既存の`scheduler.yml`と同じFTP Secretsで本番DBを読み取り専用でダウンロードし（書き戻しは行わない）、監査結果をJSON Artifact（`db-audit-result`、`retention-days: 30`）として保存する。

ExitCode（本ドキュメントが定める0/1/2の意味自体は変更しない）の扱いはWorkflow側で判定する。ExitCode 2（Error検出）の場合のみジョブをFailさせ、ExitCode 0・1（問題なし・Warningのみ）はいずれもSuccessとし、Warningの内容はGitHub Actions Job Summaryで可視化する。詳細は`db_audit.yml`内のコメントを参照。

**GitHub Actionsの仕様上の制約**: `workflow_dispatch`はデフォルトブランチ（`main`）上に存在するワークフローに対してのみ実行できる。`db_audit.yml`導入時（Task35 Step4）は`main`反映前だったため実環境での`workflow_dispatch`実行確認ができず、`main`反映後に確認した（詳細は`.github/workflows/README.md`を参照）。

---

## Migration不要確認（Step5）

Task33（`feat(repository): eliminate TOCTOU race in Case C transaction`）で追加した内容について、Migrationが不要である理由を以下のとおり確認した。

| 確認項目 | 結果 | 根拠 |
|---|---|---|
| schema変更なし | 確認済み | `src/mod_personnel_db/repositories/sqlite/_schema.py`はTask33のいずれのコミット（`e46ce60`等）でも変更されていない（`git diff 325b8af..HEAD -- .../_schema.py`が空）。最終更新は`6cfa0d8`（Phase3 Task11-3）まで遡り、Task33とは無関係 |
| table変更なし | 確認済み | `DB/personnel.db`の`sqlite_master`を実クエリで確認した結果、12業務テーブル（`pdfs, layouts, parser_versions, personnel_sections, candidate_records, gold_records, review_sessions, review_changes, knowledge_items, learning_dataset, exports, jobs`）のみが存在し、`_schema.py`のDDLと完全に一致する。新規テーブル・削除テーブルなし |
| index変更なし | 確認済み | 同`sqlite_master`確認により、全インデックス（`idx_*`および`sqlite_autoindex_*`）が`_schema.py`の`CREATE INDEX`/`UNIQUE`制約定義と一致する。追加・削除なし |
| trigger変更なし | 確認済み | 同`sqlite_master`確認により`type='trigger'`の行は0件（`_schema.py`はもとよりトリガーを定義していない） |
| constraint変更なし | 確認済み | `_schema.py`の`CHECK`/`UNIQUE`/`REFERENCES`制約定義に変更なし（上記schema変更なしと同一の根拠） |

**Task33が実際に追加したのは以下2点のみであり、いずれもDBファイルのスキーマ（DDL）を変更するものではない**。

1. `PRAGMA busy_timeout = 5000`（`repositories/sqlite/_base.py::connect()`）: 接続確立時に発行するSQLite接続パラメータであり、DBファイルには永続化されない（接続ごとに毎回設定し直す値）。`docs/database/schema.md`の「運用上の注意事項」が定める`journal_mode`/`busy_timeout`に関する既存の記載範囲内の変更である。
2. `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`（`repositories/sqlite/candidate.py::transaction()`）: アプリケーションコードが実行時に発行するトランザクション制御文であり、DDL（`CREATE TABLE`等）ではない。SQLiteの標準的なトランザクション機構をアプリケーション層から利用しているだけであり、`schema_migrations`テーブルや`PRAGMA user_version`によるスキーマバージョン管理（`docs/database/schema.md`「バージョン管理」節、未実装）とは無関係である。

以上より、`docs/database/schema.md`の[Migration方針](../database/schema.md#migration方針)が定める「業務テーブルの新設・削除、PK/FKの変更」「非破壊的な変更（カラム追加等）」のいずれにも該当せず、Migrationは不要と判断する。

`PRAGMA user_version`は監査時点（`DB/personnel.db`実クエリ確認）でも`0`のままであり、Task33前後で変化していない。

---

## 関連文書

- [`docs/database/schema.md`](../database/schema.md) — 物理スキーマ定義（本監査の対象そのもの）
- [`docs/adr/0006-pipeline-provenance.md`](../adr/0006-pipeline-provenance.md) — 来歴管理方針（物理削除しない設計思想。修復手順が`DELETE`を使わない根拠）
- [`docs/adr/0047-pipeline-resume-and-lineage-management-model.md`](../adr/0047-pipeline-resume-and-lineage-management-model.md) — Case A/B/C・Supersede設計・TOCTOU対応（PS-1〜PS-3・CR-2の根拠）
- [`db_repair_procedures.md`](db_repair_procedures.md) — Step4: 異常検知時の手動修復手順（Repair Procedure、自動修復ツールではない）
