# Gate 1-B副次設計の具体化: 5項目の選択肢整理

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Ground Truth
- Current Phase: Ground Truth
- Current Subtask: Gate 1-B副次設計
- Completed: E14 corpus recovery / E17 design recovery / ADR-0048 formalization /
  Gate 1-A partial approval / Gate 1-B方式2方向性 approval / Gate 1-C候補B除外
  approval / E36 external storage design checkpoint(commit `4059145`、push済み)
- In Progress: Gate 1-B副次設計
- Blocked: Gate 1-B最終確定 / Gate 1-C候補A/C選択 / CategoryD D区分解消 /
  Ground Truth構築 / Resolver実装
- This Task's Exit Condition: Gate 1-B副次設計について、外部保存先・Backup/
  Recovery/Integrity・manifest schema・Versioning・runbookの各設計判断を整理し、
  承認可能な形で提示すること

> 本文書は[`ground-truth-external-storage-design.md`](ground-truth-external-storage-design.md)
> (Task-E36、承認済みcheckpoint`4059145`)§18「Unresolved decisions」・§19
> 「Approval gates」で識別した5項目(Gate 1-B-i〜v)を深掘りする。**いずれの項目も
> 本文書内で決定しない。** 設計選択肢・根拠・影響範囲を整理し、ユーザー承認待ちで
> 停止する。既存文書は上書きしない。

---

## Gate 1-B-i: 外部保存先選定方針

### Confirmed facts

- PDF Registry(ADR-0018)は「実装時に選定」という方針で技術選定を先送りしつつ、
  契約(内容アドレス方式・シャーディング・年次再ハッシュ検証)のみを先にADRで
  固定している。
- Ground Truthが参照する元PDFは、既にPDF Registry管理下にある(1643-PDF corpus)。
- `ground-truth-content-scope-analysis.md`(Gate 1-A承認内容)により、Ground Truth
  自体は実値を含まない(位置参照+構造ラベルが基本)。

### 選択肢

| 選択肢 | 内容 |
|---|---|
| 案I-1: PDF Registryインフラを再利用・拡張 | Ground Truthのラベルデータも、
  PDF Registryと同じストレージ・同じ内容アドレス方式の別namespace(例:
  `ground-truth/`配下)に格納する。 |
| 案I-2: 独立した新規ストレージ | PDF Registryとは物理的に分離した、Ground Truth
  専用の外部ストレージを別途用意する。 |
| 案I-3: 技術選定を実装時まで完全に先送り(契約のみ固定) | ADR-0018と同様、
  「内容アドレス方式・SHA-256・整合性検証の頻度」等の契約のみを本Taskで整理し
  (既にTask-E36で実施済み)、具体的な製品・サービスの選定自体は行わない。 |

### 根拠・トレードオフ

- **案I-1の利点**: 運用インフラを1つに集約でき、既存のPDF Registry運用手順
  (バックアップ・integrity検証等)を転用しやすい。**欠点**: PDF Registry
  (本番運用・公表情報の長期保管が目的、ADR-0018)とGround Truth(Resolver検証用の
  評価データ、非公開・意図的に難しいケースを含む)という**目的の異なるデータを
  同一インフラに混在させる**ことになり、Task-E29 `ground-truth-storage-decision.md`
  §3.6で既に指摘した「Gold DBの意味論が曖昧になるリスク」と同種の懸念が
  Registryレベルでも生じうる。
- **案I-2の利点**: 目的の異なるデータを明確に分離できる。**欠点**: 運用インフラが
  二重化し、バックアップ・アクセス管理等を別々に設計・運用するコストが増える。
- **案I-3の利点**: Task-E36が既に整理した「要件」と「未定パラメータ」の分離
  スタイルをそのまま継続でき、拙速な選定によるやり直しリスクを避けられる。
  PDF Registry自体もこの方針(実装時選定)を採用しており、既存repoの一貫した
  設計哲学と整合する。**欠点**: 「方針」を求められている本項目の趣旨に対し、
  「まだ決めない」という回答にとどまる可能性がある。

### 影響範囲

- 案I-1を採る場合、PDF Registry(ADR-0018)自体への影響評価(namespace分離が
  ADR-0018の設計を変更するか)が別途必要になる可能性がある。
- 案I-2を採る場合、運用要件(Backup/Recovery/Access control、Gate 1-B-ii)が
  Ground Truth専用に一から設計されることになり、PDF Registryの既存運用との
  重複コストが発生する。
- 案I-3を採る場合、後続のGate 1-B-ii(Backup/Recovery/Integrity)・Gate 1-B-iii
  (manifest schema)の一部が「ストレージ非依存で設計可能な部分」と「ストレージ
  選定後でなければ確定できない部分」に分かれる。

---

## Gate 1-B-ii: Backup/Recovery/Integrityパラメータ

### Confirmed facts

- `docs/operations/release.md`のBackupテーブルは、対象ごとに異なる頻度・保持期間を
  定めており、「保持世代: 実装時に確定」という未定パラメータを許容する既存
  スタイルを持つ。
- FTPサーバ側`.bak`は1世代のみ(`release.md`「保持世代」節)。
- ADR-0018は「年1回以上」の再ハッシュ検証を要件とする。
- `docs/security.md`はSHA-256を標準ハッシュアルゴリズムとする。

### 選択肢(頻度・世代数・検証周期をそれぞれ独立した軸として整理)

| 軸 | 選択肢candidate | 根拠となる既存precedent |
|---|---|---|
| Backup頻度 | (a)ラベリングバッチ完了ごと(event-driven) / (b)定期(週次等、
  release.mdの「少なくとも週次」に類する) / (c)両方の併用 | release.mdのDB
  バックアップ方針(マイグレーション適用前+定期週次) |
| 保持世代数 | (a)1世代のみ(FTP `.bak`と同様の最小構成) / (b)直近N世代
  (release.mdのDBスナップショット方針と同様) / (c)Git的な無制限保持
  (manifestがGit管理下にある部分は自然にこれに該当) | release.md「保持世代:
  実装時に確定」という既存の未定パターン |
| Integrity検証周期 | (a)年1回以上(ADR-0018のPDF Registryと同一周期) /
  (b)ラベリングバッチごと(より高頻度) / (c)Backup取得時に毎回 | ADR-0018
  「保管中のファイルは...少なくとも年1回...再ハッシュ検証」 |

### 根拠・トレードオフ

- Backup頻度を「バッチ完了ごと」にする場合、ラベリング作業の粒度(Gate 1-C
  確定後に判明)に依存するため、Gate 1-Cより先にこの軸だけを確定させると
  手戻りリスクがある。
- 保持世代数を「1世代のみ」にする場合、実装コストは最小だが、誤ったラベル付けで
  上書きされた場合の復旧可能性が失われる(既存FTP `.bak`が抱えるのと同じ制限、
  `backup_restore.md`「既知の制限」節が正直に明記するスタイルを踏襲するなら、
  この制限も明示すべき)。
- Integrity検証周期を「年1回」にする場合、ADR-0018と一貫した運用になるが、
  Ground Truthはより頻繁に更新される可能性がある(PDF Registryは追記型、
  Ground Truthはラベル修正を伴う)ため、同一周期が適切かは要検討。

### 影響範囲

- 保持世代数の選択は、Gate 1-B-iv(Versioning方針、immutable snapshotを
  採用するか)と密接に関連する。immutable snapshotを採用する場合、「世代を
  削除する」という概念自体がバックアップ設計から後退し、保持世代数の議論の
  性質が変わる。

---

## Gate 1-B-iii: manifest schema

### Confirmed facts

- `pdfs`テーブル(`docs/database/schema.md`)は、`id`(PK)/`content_hash`(UNIQUE)/
  `source_url`/`published_date`/`fetched_at`/`file_path`/`file_size_bytes`/
  `status`(lifecycle)/`created_at`/`updated_at`という構造を持つ。
- Task-E36 `ground-truth-external-storage-design.md` §12は、フィールド候補
  (Ground Truth ID/dataset-version ID/source reference/structural label/
  annotation version/approval status/reviewer/approval timestamp/content
  hash/schema version)を列挙済みだが、具体的なスキーマ構造(フラット/階層型、
  ファイル形式)までは決定していない。

### 選択肢

| 選択肢 | 内容 |
|---|---|
| 案III-1: `pdfs`テーブル類似のフラット構造(1エントリ=1行) | 各Ground Truth
  エントリを、`pdfs`テーブルと同じ思想でフラットな行として表現する
  (例: CSV/TSVまたは単純なテーブル形式)。既存パターンとの一貫性が高い。 |
  ただし、1つのPDF・1つのSectionに対して複数のBlock/行レベルのラベルが
  付くため、正規化(PDF単位/Section単位/Block単位の階層)が必要になり、
  単純なフラット構造では表現しづらい可能性がある。 |
| 案III-2: 階層型構造(YAML/JSON、PDF→Section→Block→Labelのネスト) | `layouts/`
  配下のmanifest(YAML形式)や、`sample_outputs/`のJSON形式(Task-E28で確認した
  golden fileのJSON構造)に類似した、階層的なドキュメント形式。1つのPDFに
  対する全ラベルを1ファイルにまとめられる。 |
| 案III-3: DB類似の正規化テーブル群(複数ファイル、PDF/Section/Block/Labelを
  分離) | `docs/database/schema.md`の設計思想(正規化・外部キー参照)を
  Git管理下のファイル群として模倣する(例: `pdfs.csv`/`sections.csv`/
  `blocks.csv`/`labels.csv`)。 |

### 根拠・トレードオフ

- 案III-1は既存`pdfs`テーブルとの一貫性が高いが、Ground Truthの階層性
  (PDF>Section>Block>Label)を1行で表現しづらく、非正規化による冗長性が
  生じる。
- 案III-2は`layouts/`のYAML manifest・golden fileのJSON構造という、
  **リポジトリに既に2つの前例がある形式**であり、人間が読みやすく、
  レビューにも適している。
- 案III-3はDB設計との対応が最も明確だが、Git管理下での複数ファイル間の
  参照整合性(外部キー相当)をどう保証するかという、DBにはない追加の課題が
  生じる。

### 影響範囲

- 案III-2(YAML/JSON)を採る場合、`docs/design/ground-truth/`配下ではなく、
  別のディレクトリ構成(例: `layouts/`や`sample_outputs/`に類する専用
  ディレクトリ)が必要になる可能性があり、Task-E36 §15(Git/non-Git boundary)の
  「Gitに保存する候補」の物理配置に影響する。
- いずれの案も、Gate 1-A承認内容(実値を含まない)を満たす限り、CLAUDE.md/
  AGENTS.mdとの整合性には影響しない。

---

## Gate 1-B-iv: Versioning方針

### Confirmed facts

- Constitution §4「Gold Database is Truth」節: 「過去の記録は基本的に不変であり、
  修正は新しい版を積み重ねる形で行う」。
- Ground TruthはConstitution §4が定義する「Gold Database」に字義上該当しない
  (未解決の解釈論点、Task-E29 decision-readiness §4.2から継続)。

### 選択肢

| 選択肢 | 内容 |
|---|---|
| 案IV-1: Immutable snapshot(Gold DBと同じ不変性原則を踏襲) | 一度承認された
  ラベルは変更せず、修正は新版の追加として扱う。 |
| 案IV-2: Mutable + audit trail(変更は許すが、変更履歴を必ず記録) | ラベルの
  上書きを許容するが、Gate 1-C(Audit trail)で記録される変更履歴により、
  誰が・いつ・何を変更したかを追跡可能にする。 |
| 案IV-3: ハイブリッド(承認済みはimmutable、candidateはmutable) | `approval
  status`(manifest候補フィールド、Gate 1-B-iii)が`approved`になった時点で
  immutableへ移行し、それ以前(candidate/in-review)は自由に修正可能とする。 |

### 根拠・トレードオフ

- 案IV-1はConstitution §4の精神に最も忠実だが、Ground Truthが字義上Gold
  Databaseでない以上、同じ厳格さを要求する必然性があるかは論点として残る
  (過剰な厳格さが、Ground Truth整備自体のスピードを不必要に落とす可能性)。
- 案IV-2は柔軟性が高いが、「人間は承認者」原則(Constitution §4)の下で、
  承認済みラベルが後から無断で変わりうる状態は、Resolver threshold決定の
  根拠としての信頼性を損なうリスクがある。
- 案IV-3は、Gate 1-C(候補A/C選択)の8ステップ(Candidate generation→...→Gold
  promotion)と自然に対応し、「承認前は柔軟、承認後は不変」という直感的な
  区切りを提供する。

### 影響範囲

- 本項目の選択は、Gate 1-B-ii(保持世代数)の設計と直結する(immutable
  採用時は「世代削除」という概念自体が発生しない)。
- Gate 1-C(候補A/C最終選択)が確定しないと、「承認」の定義自体が確定しない
  ため、案IV-3の「承認済み」がいつ発生するかは未確定のまま。

---

## Gate 1-B-v: runbook要否

### Confirmed facts

- `docs/operations/backup_restore.md`は、DBのBackup→Restore→DB Audit→Pipeline
  Resume確認→正常確認という運用フローをRunbook形式で文書化した既存の前例。
- Task-E36 §17(Operational requirements)は、将来同種のrunbookをGround Truth
  向けに作成することが望ましいと記載したが、本Task-E36内では作成しなかった。

### 選択肢

| 選択肢 | 内容 |
|---|---|
| 案V-1: 今すぐ作成する | Gate 1-B-i〜ivが未確定のまま、汎用的なrunbookの
  骨子だけを先に用意する。 |
| 案V-2: Gate 1-B-i〜iv確定後に作成する | 外部保存先・パラメータ・schema・
  versioning方針が決まってから、それらに整合した具体的な手順を書く。 |
| 案V-3: Ground Truth構築開始時に作成する | 実際の構築(Roadmap Task Sequence
  第1段階の実施)に着手するタイミングで、実運用に即したrunbookを書く。 |

### 根拠・トレードオフ

- 案V-1は`backup_restore.md`のような具体的な手順書にはなりえず、実質的には
  「要件の再掲」にとどまる可能性が高い(既にTask-E36 §17が要件を記載済み)。
- 案V-2は、既存の`backup_restore.md`が実際のCLIコマンド(`download-db`/
  `upload-db`等)を含む実践的な文書であることを踏まえると、パラメータ確定前に
  作成することの実益が薄い。
- 案V-3は、既存repoの一般的な傾向(運用文書は実装が固まってから書く)と
  整合するが、runbook不在のままGround Truth構築が始まった場合の運用リスクが
  残る。

### 影響範囲

- 本項目は他の4項目(i〜iv)すべてに依存するため、単独で先に決定しても
  実効性が低い。**5項目の中で最も後回しにしやすい項目**と位置づけられる
  (ただし、これは順序の示唆であり、決定ではない)。

---

## Approval Matrix(統合)

| 項目 | 選択肢 | 推奨(非拘束的、参考) | User Approval |
|---|---|---|---|
| Gate 1-B-i(外部保存先選定方針) | 案I-1/I-2/I-3 | 案I-3(技術選定は先送り、
  契約のみ固定)がADR-0018の既存パターンと最も整合するが、PDF Registryとの
  関係(統合か分離か)自体は決定が必要 | **PENDING** |
| Gate 1-B-ii(Backup/Recovery/Integrityパラメータ) | 頻度・世代数・検証周期の
  組み合わせ | 明確な単一推奨なし(Gate 1-B-iv・Gate 1-Cとの依存関係が強いため) | **PENDING** |
| Gate 1-B-iii(manifest schema) | 案III-1/III-2/III-3 | 案III-2(YAML/JSON階層型)が
  既存の`layouts/`・golden file前例と一貫するが、確定は保留 | **PENDING** |
| Gate 1-B-iv(Versioning方針) | 案IV-1/IV-2/IV-3 | 案IV-3(ハイブリッド)がGate 1-Cの
  8ステップと自然に対応するが、Gate 1-C確定前には実質的に決定不能 | **PENDING** |
| Gate 1-B-v(runbook要否) | 案V-1/V-2/V-3 | 案V-2またはV-3が既存の運用文書
  作成パターンと整合するが、確定は保留 | **PENDING** |

**いずれも確定していない。** 上記「推奨」欄は検討の参考情報であり、
`Status: APPROVED`を意味しない。

---

## 依存関係の観察(新しい決定ではなく、事実の整理)

5項目を検討した結果、以下の依存関係が観察された(Task-E30・E33で「Gate間の
依存関係を明示して停止する」とした運用に倣い、事実として記録する)。

- Gate 1-B-ii(Backup/Recovery/Integrity)とGate 1-B-iv(Versioning)は相互に
  強く依存する(保持世代数とimmutable snapshotの採否が直結)。
- Gate 1-B-iv(Versioning)は、Gate 1-C(候補A/C選択、承認の定義)が確定しないと
  実質的に決定できない。
- Gate 1-B-v(runbook)は、他の4項目すべてに依存するため、最後に決定するのが
  自然と考えられる。
- Gate 1-B-i(外部保存先)は、他の4項目と比較して相対的に独立して検討可能
  (ただし案I-1採用時はADR-0018への影響評価が必要になる)。

**この依存関係の観察自体も、順序を確定させるものではない。**

## POSITION AFTER TASK

- Current Phase: Ground Truth(Gate 1-B副次設計の5項目について選択肢・根拠・
  影響範囲を整理完了。決定はいずれも未実施)
- Completed: Gate 1-B-i〜vそれぞれについて、既存repoパターン(PDF Registry/
  ADR-0018、`pdfs`テーブル、`layouts/`manifest、golden file JSON、
  `backup_restore.md`/`release.md`)を根拠とした選択肢比較を整理
- Newly discovered: 5項目間に相互依存関係があることが具体的に明確になった
  (特にGate 1-B-ii/ivの強い相互依存、Gate 1-B-ivのGate 1-C依存、Gate 1-B-vの
  他4項目への依存)。これにより、5項目を独立に決定するのではなく、依存順序を
  考慮した検討が必要になる可能性が示唆された(ただし順序自体は未決定)。
- Still blocked: Gate 1-B-i〜vの決定、Gate 1-C候補A/C選択、CategoryD D区分解消、
  Ground Truth構築、Resolver implementation
- Next approved decision: Gate 1-B-i〜vそれぞれについてのご判断
  (Approval Matrix参照)。特にGate 1-B-i(外部保存先選定方針)が他の項目より
  相対的に独立して検討可能であるため、着手する場合の候補となりうる
  (ただし優先順位の決定自体もユーザー判断による)。
