# 0047. Pipeline実行再開性とデータ来歴管理モデル

## ステータス
Accepted

## コンテキスト

`JobRunner.run_for_pdf()`は、PDF処理の途中（Section単位・Record単位）で失敗した場合、それまでにコミット済みの`personnel_sections`/`candidate_records`をそのまま残して`Job.status='failed'`・`Pdf.status='failed'`として終了する（Task27）。Task29により、Stage固有例外・`RepositoryError`（`sqlite3.IntegrityError`のラップ含む）は`JobRunner`の呼び出し境界で吸収されるようになり、再実行時に既存行との`UNIQUE`制約衝突が起きてもクラッシュはしなくなった。しかしTask31の調査（Step1〜Step5、非公式の設計整理として実施、ADR化はされていなかった）で、「クラッシュしない」ことと「安全に再実行できる（同じ失敗を繰り返さず、既に成功した部分を再利用できる）」ことは別問題であると判明した。

Task31の調査では、以下3つの再実行シナリオを区別する必要があることを確認した。

- **Case A（Section単位の途中失敗からの再開）**: 同一`parser_version_id`内で、あるSectionの処理中にJobが失敗し、再実行する場合。
- **Case B（Record単位の途中失敗からの再開）**: 同一Section内で、一部のRecordが検証未完了（`validation_status='pending'`）のまま残っている場合。
- **Case C（parser_version更新後の再解析）**: `parser_versions`に新しいリリース（[ADR-0023](0023-parser-versioning-policy.md)のSemVerタグ）が追加され、同一PDFを新versionで再処理する場合。

Case A・Case Bは、Task31 Step6（`SqliteCandidateRepository`への`find_section`/`find_candidate`/`find_active_section`/`supersede_section`追加）およびStep7（`JobRunner`のSection/Record単位Resume実装）で、ADR起票を経ずに実装済みである（明示的な指示によりコード実装を優先し、ADR整理は後追いとした）。本ADRは、この既存実装（Case A/B）を正式な設計決定として追認しつつ、Case C（Supersedeによる新旧version管理）の設計を確定する。Case Cは本ADR確定後、Task32 Step2で`JobRunner`へ実装され、Step3で境界条件・実SQLiteによる整合性検証を経ている（詳細は「Case Cの実装状況」節を参照）。

### 前提となる既存決定との関係

- [ADR-0006](0006-pipeline-provenance.md)（来歴管理）: 物理削除しない設計思想。本ADRのSupersede機構はこれに従う。
- [ADR-0019](0019-workflow-orchestration.md)（ワークフローオーケストレーション）: 「失敗したジョブの再実行はGitHub Actions自体のリトライ機構に委ねる」と決定している。しかし同ADR策定当時、「PDF単位の再実行が安全である（既存データと衝突しない）」ことは検証されておらず、Task31の調査で実際には安全でなかったことが判明した。**本ADRは、ADR-0019が前提とする「再実行の安全性」を実効化する決定と位置づける**（ADR-0019自体の決定を変更・上書きするものではない）。
- [ADR-0023](0023-parser-versioning-policy.md)（Parserバージョニング方針）: `parser_versions.code_version`はGitリリースタグ（SemVer）であり、CIがリリースタグ付与をトリガーに自動作成する。「同一version内での部分再開」（Case A/B）は、この採番方針自体を変更しない。「新versionでの再処理」（Case C）も同様に、versionの採番タイミング・粒度には触れない。
- [ADR-0044](0044-pipelinerunner-jobrunner-boundary.md)・[ADR-0045](0045-job-runner-aggregate-artifact-coordinator.md): `PipelineRunner`はRepository・集約Artifactの展開いずれも知らない。本ADRのResume判定はすべて`JobRunner`側の責務とし、`PipelineRunner`（`pipeline/runner.py`）は無変更のままとする。

## 決定

### 1. Resume機構の全体像（Case A/B/C）

`JobRunner`は、Section単位・Record単位のいずれについても「既存の永続化済み成果物があれば再利用し、なければ新規処理する」という判定を、`CandidateRepository`の検索系API（副作用なし）を介して行う。判定結果に応じて、以下の3種類の応答のいずれかを取る。

| 状態 | 応答 |
|---|---|
| 既存成果物なし | 通常どおり新規処理（Stage実行→Repository永続化） |
| 既存成果物あり・未完了（`pending`） | 既存の永続化データを使って処理を再開する（既に完了した部分のStageは再実行しない） |
| 既存成果物あり・完了済み（`passed`/`failed`） | 完全にskipする（Stage実行・Repository書込みいずれも行わない） |

「skip」は`processed_count`/`failed_count`のいずれにも計上しない（Task31 Step3〜Step5で確定した方針、`_Outcome((), 0, 0, None)`）。これらのカウンタは「今回のJob実行で新規に処理した件数」を表すという既存の意味を変更しない。

### 2. Case A: Section単位Resume（実装済み、Task31 Step6/Step7）

`_process_section()`は以下の判定を行う（実装は`src/mod_personnel_db/pipeline/job_runner.py`の`_process_section`/`_extract_and_process_records`/`_resume_pending_candidates`）。

1. `find_section(pdf_id, section_index)`で、現在の`JobRunner`が束縛する`parser_version_id`と一致する既存Sectionの有無を確認する。
2. 存在しなければ、`add_section()`から通常どおり処理する。
3. 存在し、`list_by_section()`が0件を返せば（Section Parserは成功したがField Extractor以降が1件も完了していない状態）、既存Section行を再利用し、`add_section()`をスキップしてField Extractor以降を通常どおり実行する。
4. 存在し、全Candidateの`validation_status`が`passed`または`failed`であれば、Section全体を完全skipする（Field Extractor・Normalizer・Validatorのいずれも実行しない）。
5. 存在し、一部のCandidateが`pending`のままであれば、Field Extractorを再実行せず、既存Candidate一覧（`list_by_section()`の結果）から`pending`のものだけをRecord単位で再開する（Case Bへ委譲）。

### 3. Case B: Record単位Resume（実装済み、Task31 Step6/Step7）

`_process_record()`は以下の判定を行う。

1. `find_candidate(section_id, record_index)`で既存Candidateの有無を確認する。
2. 存在しなければ、`add_raw()`から通常どおり処理する（Normalizer→Validatorへ進む）。
3. 存在し`validation_status='pending'`であれば、`add_raw()`は呼ばず、Repositoryから取得した`CandidateRecord.raw`（既存の永続化データ）を使ってNormalizerから再開する。
4. 存在し`validation_status`が`passed`/`failed`であれば、完全skipする。

この設計により、`add_raw()`によるFieldExtractor出力の再永続化（＝`UNIQUE`制約衝突の発生源）を避けつつ、Normalizer/Validatorの再実行によって`pending`のまま放置されていたCandidateを完了させられる。

### 4. Case C: parser_version更新後の再解析（本ADRで新規に確定、実装済み：Task32 Step2/Step3）

新しい`parser_version_id`で同一PDFを再処理する際、`personnel_sections`は`UNIQUE(pdf_id, section_index, parser_version_id)`により新versionでは自動的に新規行として追加される（既存versionとの`UNIQUE`衝突は起きない）。問題は、旧versionの行が`status='parsed'`のまま残り続け、新旧どちらのSectionも「有効」に見えてしまう点である。これを解消するため、以下の手順を確定する。

1. `JobRunner`は、新Sectionを`add_section()`する**前**に、`find_active_section(pdf_id, section_index)`を呼び、現在アクティブな（`status='parsed'`の）Sectionが存在するかを確認する。
2. `add_section()`で新versionのSectionを追加する。
3. 手順1で取得したSection IDが存在すれば、`supersede_section(old_section_id)`を呼び、旧Sectionを`status='superseded'`に更新する。

`candidate_records`には対応する`status`/`superseded_by`列を追加しない。新旧の判別は、親`personnel_sections.status`から導出する（`candidate_records`は`personnel_section_id`経由で親を辿れば、どちらのversionに属するかが一意に定まるため、子テーブル側で状態を二重管理しない）。

### 5. 設計前提（Resume系APIの不変条件）

本設計では、`(pdf_id, section_index)` ごとに `status='parsed'` の `personnel_sections` は高々1件であることを前提とする。

この不変条件は、Sectionのライフサイクルを `parsed` → `superseded` に遷移させる運用（Case Cの手順3、`supersede_section()`の呼び出し）により維持される。したがって `find_active_section()` は

- `pdf_id`
- `section_index`
- `status='parsed'`

のみを条件として検索し、一意に現在アクティブなSectionを取得できる。

この前提が崩れた場合（同一 `(pdf_id, section_index)` に対して複数の `parsed` 行が存在する場合）の動作は、本ADRでは保証対象外とする。Task32 Step3では、実SQLiteを用いた統合テスト（`tests/unit/pipeline/test_job_runner_resume_sqlite.py`）により、正常系（本ADR確定後にCase Cの手順どおり処理された場合）でこの前提が維持されることを確認済みである。ただし、本ADR確定・Case C実装より前に処理されたデータ（Case Cの手順を経ていないデータ）がこの不変条件を満たすかどうかは別問題であり、「結果（トレードオフ）」節に記載のとおり、依然として本ADRの対象外のまま残っている。

### Case Cの実装状況

Case C（parser_version変更時のResume／Supersede）は、本ADRにおいて設計を確定した。

Task31ではResumeに必要なRepository API（`find_active_section()`・`supersede_section()`等）の追加までを実施し、その後Task32 Step2で、`JobRunner`（`_add_section_and_process()`、`src/mod_personnel_db/pipeline/job_runner.py`）へ

1. `find_active_section()`
2. `add_section()`
3. `supersede_section()`（該当する旧Sectionが存在する場合のみ）

の呼び出し順序を実装した。Task32 Step3では、境界条件（`add_section()`失敗時にsupersedeしないこと、旧IDと新IDが一致するケースの防御、複数Section時の独立性）および実SQLiteによる統合テストを追加し、本ADRの設計との整合性を確認済みである（`tests/unit/pipeline/test_job_runner.py`のCase Cテスト群、`tests/unit/pipeline/test_job_runner_resume_sqlite.py`）。

## find_active_sectionを新設した理由

Case A用の`find_section(pdf_id, section_index)`は、内部で`self._parser_version_id`（＝`JobRunner`インスタンスが束縛する現行バージョン）に一致する行のみを検索する。これは「このversionで既にこのSectionを処理したか」という問い（Case A/Bの前提）に対しては正しい設計だが、Case Cが必要とする「**他のversionで現在アクティブな**Sectionがあるか」という問いには答えられない——`find_section()`は定義上、現行version以外の行を見つけられないためである。

この2つの問いは意味的に異なるクエリであり、1つのメソッドでは両立しない。そのため`find_active_section(pdf_id, section_index)`を独立したAPIとして新設した。`parser_version_id`を検索条件に含めず、`WHERE pdf_id=? AND section_index=? AND status='parsed'`のみで検索する（`Supersede`運用が正しく維持されている限り、ある`(pdf_id, section_index)`について`status='parsed'`の行は高々1件であるため、これで一意に「現在アクティブな旧Section」を取得できる）。

`find_active_section`はCase C専用のAPIであり、Case A/Bのskip判定には使わない（`find_section`と役割を混同しない）。

## add_section前にfind_active_sectionを呼ぶ理由

手順を「1. `find_active_section` → 2. `add_section` → 3. `supersede_section`」の順に固定する（逆順にしない）理由は、`add_section()`を先に実行してしまうと、新旧2行が両方`status='parsed'`の状態が一時的に生じ、`find_active_section()`が新旧どちらの行を返すか区別できなくなるためである。`find_active_section()`を`add_section()`より前に呼ぶことで、この時点で存在する`status='parsed'`の行は必ず「旧version（または初回処理時は0件）」であることが保証され、新Section自身を誤って「supersede対象」として検出することを構造的に防げる。

## Supersede設計・冪等性・TOCTOU

### 冪等性

`supersede_section()`は`UPDATE personnel_sections SET status='superseded' WHERE id=? AND status='parsed'`を実行する（Task31 Step6実装済み）。2回目以降の呼び出しは`rowcount=0`になるが、これを異常とはみなさず例外を送出しない。最終状態（`status='superseded'`）は初回・再呼び出しいずれでも同一であり、呼び出し側（`JobRunner`）は戻り値を見て分岐する必要がない。

### TOCTOU（Time-of-Check to Time-of-Use）競合について

`find_active_section()`による確認と、その後の`add_section()`/`supersede_section()`実行の間には、SQLite接続レベルでの原子性保証がない（`docs/database/schema.md`が定めるとおり、本プロジェクトは明示的なトランザクション管理（`BEGIN`/`ROLLBACK`）を持たず、各Repository書込みメソッドは単独の文をオートコミットする設計である）。したがって、同一PDFに対する2つの`run_for_pdf()`呼び出しが並行実行された場合、以下のような競合が理論上あり得る。

- 2つの実行が同時に`find_active_section()`を呼び、両方が同じ旧Section IDを「supersede対象」として検出する。
- 両方が`add_section()`に成功する可能性がある——ただし新version側の`add_section()`自体は`UNIQUE(pdf_id, section_index, parser_version_id)`により、同一`parser_version_id`での重複は防がれる（同一`JobRunner`インスタンス・同一versionでの並行実行であれば、片方は`RepositoryError`で失敗し、既存の吸収ロジック（Task29）で安全に処理される）。
- `supersede_section()`自体は`WHERE status='parsed'`の条件付き更新であるため、2つの実行が同じ旧Section IDに対して呼んでも、2回目は`rowcount=0`の無害な no-op になる（冪等性により実害はない）。

以上より、TOCTOU競合は**完全には解消されない**が、（1）`supersede_section()`の条件付きUPDATEにより「誤って二重にsupersedeする」实害は防がれ、（2）`add_section()`のUNIQUE制約により「同一version内での二重書込み」も既存の例外吸収機構でカバーされるため、**データ破損には至らない**。この既知の制限は「結果（トレードオフ）」節に明記する。運用上、[ADR-0019](0019-workflow-orchestration.md)が前提とするGitHub Actionsベースの実行環境では、同一PDFに対する並行実行は起こりにくいと見込まれる。

## 検討した代替案

### 案1: `parser_version_id`をRepository公開APIの引数として渡す

`find_section(pdf_id, section_index, parser_version_id)`のように、`parser_version_id`を呼び出し側（`JobRunner`）が明示的に渡す設計を検討した。却下した。理由は以下の通り。

- 既存の`CandidateRepository`メソッド（`add_section`, `add_raw`, `attach_normalized`, `update_validation`）はいずれも`parser_version_id`を引数に取らず、コンストラクタで束縛した`self._parser_version_id`を内部で使う一貫した設計になっている（`repositories/sqlite/candidate.py`）。`find_section`/`find_candidate`だけが例外的に明示引数を取ると、この既存の一貫性を破る。
- `JobRunner`が`parser_version_id`を保持・受け渡しする必要が生じ、`JobRunner`側のコードが煩雑になる。
- Repositoryインスタンスは1つの`parser_version_id`に束縛されたスコープで生成される設計（Composition Root、[ADR-0046](0046-composition-root-dependency-injection-contract.md)）であるため、呼び出しのたびに同じ値を渡すことは冗長である。

ただし、外部シグネチャを最小限に保ちつつ、内部の`WHERE`句では`self._parser_version_id`を含む3列すべて（`UNIQUE`制約と1:1）で照合する実装とした（`find_section`/`find_candidate`とも）。これにより、シグネチャの一貫性（外部引数を増やさない）と、クエリの安全性（`UNIQUE`制約の全列に一致させる）を両立させている。

### 案2: `candidate_records`にも`status`/`superseded_by`列を追加する

`personnel_sections`と対称に、`candidate_records`にも独自のSupersede状態を持たせる案を検討した。却下した。`candidate_records`は`personnel_section_id`経由で親Sectionに従属するため、親がsupersedeされれば子も間接的に「旧version」と判別できる。子テーブル自体に重複した状態を持たせると、親と子の状態が矛盾しうる状態（親は`superseded`、子は取り残されたまま等）を新たに作り込むリスクがあり、「削除せず追記する」設計思想（[ADR-0006](0006-pipeline-provenance.md)）に対しても、親テーブル1箇所で判定できる方がシンプルである。

### 案3: `add_or_get_section()`のような単一Upsertメソッドに統合する

`find_section()`+`add_section()`を1つの`add_or_get_section()`メソッドに統合する案を検討した。却下した。「新規追加か再利用か」を`JobRunner`側で明示的に分岐できなくなり、ログ・Learning記録上の追跡性が低下する。また、Case Cの`find_active_section()`はCase A用の`find_section()`とは意味的に異なるクエリであり、単一のUpsertメソッドに統合するとこの区別自体が失われる。

### 案4: `supersede_section()`に状態条件を付けない（無条件UPDATE）

`WHERE id=?`のみで無条件にUPDATEする案を検討した。却下した。条件を付けないと、既に`superseded`の行に対しても無条件で同じUPDATEを発行できてしまい、「本来この呼び出しで初めてsupersedeされるべき行」と「既にsupersedeされていた行」の区別がSQLレベルで失われる。`WHERE status='parsed'`を付けることで、SQLiteが単一SQL文として原子的に実行する比較・更新（compare-and-swap相当）になり、TOCTOU競合を完全にではないが部分的に軽減できる（上記「TOCTOU競合について」参照）。

### 案5: Job再開フラグ（`run_for_pdf(pdf, is_resume=True)`等）を新設する

呼び出し側が「これは再実行です」と明示的に伝えるフラグを追加する案を検討した。却下した。`find_section()`/`find_candidate()`/`find_active_section()`の結果だけで、初回実行と再実行を同一のコードパスで統一的に扱えるため、フラグによる分岐を追加すると制御フローが二重化し、[ADR-0014](0014-development-discipline.md)の関数複雑度制限に抵触しやすくなる。実際、Task31 Step7の実装でもフラグは導入していない。

## 結果（トレードオフ）

- **得られるもの**: Section/Record単位での安全な再開（Case A/B）、およびparser_versionをまたいだ再解析でも新旧データが物理削除されず`status`列で来歴を追跡できる仕組み（Case C）。いずれもTask32 Step2/Step3時点で実装・テストとも完了している。
- **失うもの・残る制限**:
  - TOCTOU競合は完全には解消されない（上記参照）。将来的にトランザクション境界（`BEGIN`/`COMMIT`）を導入する場合は、別途ADRでの再検討が必要になる。
  - Case Cの「新旧versionの`candidate_records`比較」（差分表示等）は本ADRのスコープ外のまま据え置く。必要になった時点で別ADRとする。
  - `find_active_section()`は`.fetchone()`により1件のみを返す実装（Task31 Step6時点、Task32 Step2/Step3でも変更していない）であり、複数の`status='parsed'`行が万一存在した場合の挙動は、どの行が返るか未定義のままである。Task32 Step2/Step3では、本ADR確定後にCase Cの手順で処理された正常系の整合性（実SQLite統合テスト）は確認したが、**本ADR確定・Case C実装より前に処理された既存データ（supersede未実施のまま複数versionで処理されたレコードが既にDBに存在する場合等）との整合性確認は行っていない**。実データでの確認は別途運用タスクとして必要である。
- **既存ADRとの整合性**: [ADR-0006](0006-pipeline-provenance.md)（物理削除しない）、[ADR-0019](0019-workflow-orchestration.md)（再実行はGitHub Actionsのリトライに委ねる、本ADRはその前提を実効化する）、[ADR-0023](0023-parser-versioning-policy.md)（parser_versionはリリース単位、本ADRは採番方針を変更しない）のいずれとも矛盾しない。

## Case C実装の記録（Task32 Step2/Step3）

- 実装箇所: `JobRunner._process_section()`の「既存Section未検出（新規PDF or 新version初回処理）」分岐から`_add_section_and_process()`を呼び出し、`find_active_section()`→`add_section()`→（該当あれば）`supersede_section()`の手順を実装した（Task32 Step2）。
- 上記「結果（トレードオフ）」で述べた`find_active_section()`の複数行存在時の未定義動作については、実データでの事前確認は行われないまま実装が完了している。既知の制限として残る。
- Case Cのテストは、`tests/unit/pipeline/test_job_runner.py`（Stubによる呼び出し順序・境界条件: `add_section()`失敗時の非supersede、旧新ID一致時の防御、複数Section時の独立性）と`tests/unit/pipeline/test_job_runner_resume_sqlite.py`（実SQLiteによる`status='parsed'`高々1件の維持確認）の2層で実施した（Task32 Step3）。
- 本ADRはCase A/Bの実装（Task31 Step6/Step7）を追認する内容を含むが、Case A/Bのコード自体に変更は生じていない。

## 関連ADR

- [ADR-0006](0006-pipeline-provenance.md) — 来歴管理方針（物理削除しない設計思想、Supersedeの根拠）
- [ADR-0019](0019-workflow-orchestration.md) — ワークフローオーケストレーション（再実行のGitHub Actionsへの委譲、本ADRが前提を実効化する対象）
- [ADR-0023](0023-parser-versioning-policy.md) — Parserバージョニング方針（`parser_version_id`の採番はリリース単位のまま変更しない）
- [ADR-0044](0044-pipelinerunner-jobrunner-boundary.md) — `PipelineRunner`/`JobRunner`責務境界（本ADRのResume判定はすべて`JobRunner`側の責務）
- [ADR-0045](0045-job-runner-aggregate-artifact-coordinator.md) — `JobRunner`によるCoordinatorモデル（Section/Record単位の反復呼び出し構造、本ADRのResume判定はこの構造内で行う）
- [ADR-0046](0046-composition-root-dependency-injection-contract.md) — Composition Root依存注入契約（`CandidateRepository`が1つの`parser_version_id`に束縛されて生成される前提）
