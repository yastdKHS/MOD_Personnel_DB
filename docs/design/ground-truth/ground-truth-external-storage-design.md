# Ground Truth External Storage Design(Gate 1-B 副次設計)

## 1. Status

Status: DRAFT

## 2. Approval

Approval: PENDING

## 3. DESIGN POSITION

- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Gate 1-B副次設計
- Completed: E14 corpus identity / E17 design recovery / ADR-0048 formalization /
  E14/E17 roadmap / Gate 1-A部分承認 / Gate 1-B「方式2」方向性承認 / Gate 1-C候補B除外 /
  Gate 1-B/1-C並行検討可能という依存構造 / Gate 1関連設計checkpoint(`a69f62f`・`8fb5265`)
- In Progress: Git外Ground Truth管理の副次設計(本文書)
- Blocked: Ground Truth実データ作成 / Block classificationの実データ検証 /
  CategoryD 1:N,N:1の最終判断 / Hybrid Section定義確定 / Resolver threshold
  validation / Resolver implementation
- This Task's Exit Condition: Git外Ground Truth管理について、永続性・バックアップ・
  復旧・integrity・アクセス管理・manifest・versioning等の要件が再現可能な設計文書として
  整理され、未確定事項とユーザー承認事項が明確になること

## 4. Already Approved(本Taskで再審議しない事項)

[`ground-truth-gate-1-b-final.md`](ground-truth-gate-1-b-final.md)(`Status: APPROVED`
（方向性のみ。副次的設計は別Task）、`Approved-in-task: E30`)で既に承認された事項:

> Ground Truthの保存方式として、「実データはGit外で管理し、Gitにはmanifestおよび
> 構造的判定情報を管理する」方式2の方向性を承認する。

本Taskはこの方向性そのものを再審議しない(Task-E36最重要制約24)。本文書が扱うのは
「方式2を成立させるために何が必要か」という副次設計のみである。

## 5. Scope

本文書の対象は、Git外に保存される可能性のあるGround Truth関連データ(将来構築される
場合)の管理要件であり、以下を含む。

- 永続性・バックアップ・復旧
- Integrity verification(改ざん・破損検知)
- アクセス管理
- Gitに保存するmanifest/metadataとの対応関係
- Versioning
- 人間承認プロセス(Gate 1-C)との境界

**対象外**(本文書のスコープに含まない):
- Ground Truth実データそのものの作成・構築
- 外部ストレージの具体的な製品・サービスの選定
- Gate 1-C(候補A/Cの最終選択)そのもの
- CategoryD 1:N/N:1のD区分の解消
- Resolver実装

## 6. Confirmed repository constraints(既存repoの確定事実)

詳細は本Task(Task-E36)のスクラッチ成果物`repository_constraint_reconciliation.md`
(`/tmp/taskE36/`、リポジトリ外)を参照。要旨:

- 実PDF本体は本リポジトリで管理しない。既存の**PDF Registry**(ADR-0018)は、
  内容アドレス方式(`<hash[:2]>/<hash[2:4]>/<hash>.pdf`)のシャーディング構造で
  リポジトリ外部の専用ストレージに保管し、技術選定は「実装時に選定」として
  ADRでは契約(方式)のみを固定している。
- `pdfs`テーブルは`content_hash`(UNIQUE)・`source_url`・`file_path`(外部参照)・
  `status`(lifecycle)という、Git外データをDB側で参照するための既存パターンを持つ。
- SHA-256が既存repoの標準ハッシュアルゴリズム(`docs/security.md` Checksum/Hash節)。
- 既存の`docs/operations/backup_restore.md`・`release.md`は、DB・PDF Registry・
  コード資産(Git自体を分散バックアップとみなす)・Export成果物それぞれに異なる
  バックアップ方針を定めており、「要件」と「実装時に確定する未定パラメータ」を
  明確に分離する文書スタイルを一貫して採る。
- Constitution §4は「Gold Database」「Knowledge Base」を明示的に定義するが、
  Ground Truthはいずれにも字義どおり該当しない(未解決の解釈論点、13章で継続)。
- `tests/golden`は実在PDFではなく合成データを用いる。

**これらは本Taskで新たに確定した事実ではなく、既存repoの調査によって確認した事実で
ある。**

## 7. Persistence requirements(永続性要件)

| 項目 | 要件 | 未確定パラメータ |
|---|---|---|
| 保存期間 | Ground Truthは今後複数のTask(Block classification検証・CategoryD再評価・
  Resolver threshold決定・regression verification)にわたって参照される前提であり、
  少なくともResolver実装・regression verification完了までは保持する。 | 恒久保存とするか、
  一定期間後に見直すかは未確定。 |
| lifecycle | PDF Registryの`pdfs.status`(fetched→analyzed→parsed→validated→
  failed)と同様の状態遷移モデルが、Ground Truthのラベリング進捗管理にも適用できる
  可能性がある(例: candidate→reviewed→approved)。 | 具体的な状態名・遷移条件は
  Gate 1-C(候補A/C選択)の結論に依存するため、本文書では確定しない。 |
| 単一障害点(SPOF) | Ground Truthの実データが単一のストレージ・単一の担当者環境
  にのみ存在する状態を避ける必要がある(本セッションが過去に経験した`/tmp`データ
  消失[Task-E15]と同種のリスク)。 | 具体的な冗長化方式(複製先の数・場所)は未確定。 |
| ストレージ障害への耐性 | PDF Registryが要求する「10年規模の可用性」に準じる水準を
  参考値として検討する余地がある。 | Ground Truth自体に同水準の可用性が必要かは
  未確定(Ground Truthは検証用データであり、PDF Registryのような永久保存が
  必須の性質を持つとは限らない)。 |
| 担当者変更への耐性 | 保存場所・アクセス方法がリポジトリ内のドキュメント
  (本文書・manifest)から再現可能であることを要件とする(特定個人の環境に
  依存しない)。 | 具体的な引継ぎ手順は未確定。 |

## 8. Backup requirements(バックアップ要件)

`docs/operations/release.md`の既存Backupテーブル(6章参照)に倣い、要件と未確定
パラメータを分離する。

| 項目 | 要件 | 未確定パラメータ |
|---|---|---|
| backup frequency | ラベリング作業のまとまった単位(例: 1バッチ分のラベル付け完了時)
  ごとに取得することが望ましい。 | 具体的な頻度(日次/週次/バッチ単位)は未確定。 |
| backup location | 主保存先とは独立した場所に保管する(単一障害点を避ける、
  7章と同じ原則)。 | 具体的な場所は未確定(外部ストレージ選定と連動)。 |
| backup independence | 主保存先と同一の認証情報・同一の物理障害ドメインに
  依存しないことが望ましい。 | 具体的な独立性の担保方法は未確定。 |
| backup integrity | バックアップ自体も、主データと同じ内容ハッシュ(SHA-256、
  6章)で検証可能であることを要件とする。 | 検証の自動化・頻度は未確定。 |
| backup retention | ADR-0018のPDF再ハッシュ検証(年1回以上)に類する定期検証の
  対象とすることが望ましい。 | 保持世代数(release.mdの「保持世代: 実装時に確定」
  という既存の未定パターンと同様)は未確定。 |
| restore test | バックアップは取得するだけでなく、定期的な復元テストで有効性を
  確認する(`release.md`「検証」節と同じ考え方)。 | 復元テストの頻度・手順の
  詳細は未確定。 |

## 9. Recovery requirements(復旧要件)

| 項目 | 要件 |
|---|---|
| manifestから対象を特定できるか | 復旧時は、Gitに保存されたmanifest(12章)を正として、
  どのGround Truthエントリ(PDF識別子+Section+Block範囲等)が失われたかを特定できる
  ことを要件とする。 |
| hashから同一データを検証できるか | 復旧したデータのcontent hashが、manifestに
  記録されたhashと一致することを検証できることを要件とする(6章のSHA-256標準を適用)。 |
| metadataだけから復旧不能になった場合の扱い | Gitのmanifest(構造的判定ラベル、
  Gate 1-A承認内容により実値を含まない)が生き残っている限り、位置参照・構造ラベル
  自体は失われない。ただし、その位置参照が指す元PDF(既存のPDF Registry管理下)が
  同時に失われた場合、ラベル付け作業そのものの再実施が必要になる。この場合の扱いは
  「データ消失」ではなく「再ラベリングが必要な状態」として区別する。 |
| backupからのrestore | 8章のバックアップから復元する場合、復元後にmanifestとの
  整合性(hash一致・件数一致)を検証してから運用再開とする(`backup_restore.md`の
  「Restore→DB Audit→正常確認」という既存フローと同じ考え方)。 |
| approval stateの復旧 | Gate 1-C(人間承認プロセス)で確定するreviewer identity・
  approval timestamp等のapproval状態も、backup対象に含める必要がある(approval
  stateのみ消失し、データ本体のみ残る、という非対称な状態を避ける)。 |

## 10. Integrity requirements(integrity verification要件)

既存標準(6章、SHA-256)・ADR-0018の年次再ハッシュ検証パターンを踏襲する。

| 項目 | 要件 |
|---|---|
| cryptographic hash | Ground Truthの各エントリ(またはデータセット全体)に対して
  SHA-256ハッシュを計算し、manifestに記録する。 |
| manifest | manifest自体もGit管理下に置くことで、Git自体が持つ内容検証・
  変更履歴追跡機能(commit hash・diff)を、manifestの改ざん検知に利用できる
  (追加の仕組みを要しない)。 |
| version | 各エントリのラベルバージョンを識別できることを要件とする(13章)。 |
| provenance | ADR-0006の「入力元への参照を保持する」原則に倣い、各Ground Truth
  エントリは、どのPDF(`content_hash`)・どのSection・どの行範囲に由来するかを
  追跡可能な形で記録する。 |
| modification detection | 主データの内容ハッシュが、manifestに記録された
  ハッシュと一致するかを定期的に検証する(頻度はADR-0018に倣い年1回以上を
  参考値とするが、確定しない)。 |

## 11. Access-control requirements(アクセス管理要件)

Constitution §4「AIはGold Databaseを書き換えない」原則との境界を明確にする。

| 操作 | 要件 |
|---|---|
| 読み取り | Ground Truthの参照(Resolver検証・閾値決定時の読み取り)は、AI・人間
  いずれも実施可能とする(読み取り自体は「書き換え」ではない)。 |
| 書き込み(ラベル生成) | AIによる初期ラベル案の生成は許容される(Gate 1-C原文書、
  候補A/Cいずれも前提とする)。ただし、これは「候補」であり、確定ラベルではない。 |
| Approval(確定) | Gate 1-Cで未確定(候補A/C選択待ち)。**いずれの候補でも、
  AIが単独でラベルを最終確定(Gold相当のステータスへ昇格)する経路は設けない**
  (`ground-truth-gate-1-c-final.md`の既承認内容と整合)。 |
| Backup / Restore操作 | 本来的にはデータの書き換えを伴わない操作だが、誤操作時の
  影響が大きいため、実行前の確認手順(`backup_restore.md`の「正常終了条件」
  「異常時対応」のような明示的なチェックリスト)を要件とする。 |
| Audit | 誰が・いつ・どのラベルを承認したかを追跡可能にする(Gate 1-Cの
  Audit trailステップと接続、14章)。 |

**AIがGoldを直接書き換えない、という既存原則との境界**: Ground Truthは字義上
「Gold Database」ではないが、将来Resolver threshold決定の根拠として使われる以上、
実質的にGold相当の重みを持つ。したがって、本文書は「読み取り・候補生成はAI可、
最終確定は人間のみ」という境界を、Constitution §4の精神を踏襲する形で採用する
(これは新しい設計判断というより、Gate 1-Cで既に整理された「候補B除外」の帰結を
アクセス制御の観点から言い換えたものである)。

## 12. Manifest requirements(manifest要件)

Gitに保存するmanifestに含める**候補**フィールド(確定仕様ではない)。`pdfs`テーブルの
既存パターン(6章)を参考にする。

| フィールド(候補) | 内容 | 実値を含むか |
|---|---|---|
| Ground Truth ID | エントリの一意識別子 | 含まない |
| dataset/version ID | どのラベリングバッチ・スキーマバージョンに属するか | 含まない |
| source reference | 由来PDFの`content_hash`(既存`pdfs.content_hash`と同一の
  ハッシュ値を参照する形が既存設計と整合的) | 含まない(ハッシュ値のみ) |
| file/document identifier | PDF識別子(ファイル名またはハッシュ) | 含まない |
| structural label | Gate 1-A承認内容(`ground-truth-gate-1-a-final.md`)に基づく
  (i)位置参照+(ii)構造的判定ラベル | 含まない(BlockKind等の分類ラベルのみ) |
| annotation version | ラベル自体の版番号 | 含まない |
| approval status | candidate/approved等(Gate 1-C結論待ち) | 含まない |
| reviewer | 承認者識別子(Gate 1-C結論待ち) | 含まない |
| approval timestamp | 承認日時 | 含まない |
| content hash | Ground Truthエントリ自体の内容ハッシュ(SHA-256) | 含まない
  (ハッシュ値のみ、ハッシュ元の実値は含まない) |
| schema version | manifestスキーマ自体のバージョン | 含まない |

**実値や個人情報をmanifestへ保存する必要がないことの検討**: Gate 1-Aで承認された
とおり、Block classification・Hybrid判定・Resolver threshold validationの検証は
(i)+(ii)のみで成立し、氏名・階級等の実値(iii)を必要としない。したがって、上記
manifest候補フィールドはいずれも実値を含まない設計が可能である。ただし、CategoryD
1:N/N:1の一部エッジケース(Gate 1-A原文書§2.3で留保)については、将来的に構造
パターン表現で対応できるかの検証が必要であり、その場合でもmanifestに実際の氏名・
階級の文字列を直接埋め込む必要はなく、「氏名らしき文字列の位置」等の構造情報で
表現できる可能性が高い(Gate 1-Aの整理と整合)。

**上記はいずれも候補であり、本Task内で確定仕様としない。**

## 13. Versioning requirements(versioning要件)

| 項目 | 要件 | 未確定パラメータ |
|---|---|---|
| dataset version | Ground Truth全体のバージョン(サンプル拡張・スキーマ変更等の
  節目ごとに更新)を識別できることを要件とする。 | 具体的なバージョニング方式
  (semver等)は未確定。 |
| annotation version | 個々のラベルが、いつ・どのスキーマ版で付与されたかを
  識別できることを要件とする。 | 詳細は未確定。 |
| schema version | manifestのフィールド構成自体が変わった場合、スキーマの
  バージョンを識別できることを要件とする。 | 詳細は未確定。 |
| immutable snapshot | 一度承認されたラベルは、Gold Database(Constitution §4
  「過去の記録は基本的に不変であり、修正は新しい版を積み重ねる形で行う」)と
  同じ思想を踏襲し、上書きではなく新版の積み重ねで修正することが望ましい。 |
  適用するかどうか自体は未確定(Ground TruthがGold Databaseと同じ不変性原則に
  従うべきかは、Constitution §4の適用範囲解釈[前出の未解決事項]に依存する)。 |
| revision history | 版の変更履歴を追跡可能にすることを要件とする。 |
  Git管理下のmanifestであれば、commit履歴が自然に版履歴を提供する。実データ
  (Git外)側の版履歴管理方法は未確定。 |
| rollback | 誤ったラベル付けを以前の版に戻せることが望ましい。 |
  「過去版を削除するか保持し続けるか」は、本文書では決定しない(指示どおり)。 |

## 14. Approval-workflow boundary(Gate 1-Cとの境界)

**本節はGate 1-Cの候補A/C最終選択そのものを行わない。** 既承認事項
(候補B除外、`ground-truth-gate-1-c-final.md`)を前提に、保存管理がapproval
workflowとどう接続しうるかの設計候補のみを整理する。

`docs/review/domain.md`の既存ライフサイクル(Candidate → Assigned → In Review →
Modified → Approved → Gold Database)と類比した場合の対応候補:

| 既存Review概念 | Ground Truthでの対応候補(未確定) |
|---|---|
| Candidate | AIが生成した初期ラベル案、またはラベリング未着手のエントリ |
| Assigned / In Review | 人間レビュアーが確認中のエントリ(Gate 1-C候補A採用時)、
  または人間が直接作成中のエントリ(候補C採用時) |
| Modified | レビュー中に修正されたラベル |
| Approved | 人間が最終確認・承認したラベル(この時点でmanifestの`approval status`
  [12章]が更新される想定) |
| Gold Database相当 | Ground Truthには「公開」という概念がないため、既存の
  Gold Database(本番公開データ)とは異なる終端状態(例: 「Resolver検証に
  使用可能な確定ラベル」)を指す候補概念 |

**この対応表は設計候補であり、Gate 1-C(候補A/C最終選択)が確定して初めて、
どのステップが実際に必要かが定まる。本文書では確定しない。**

## 15. Git / non-Git boundary(Gitに保存するもの／保存しないもの)

### Gitに保存する候補

- manifest schema定義(12章のフィールド構成そのもの、確定後)
- manifest本体(実値を含まない位置参照+構造ラベルのみである限り)
- dataset identifier・version metadata
- content hash(ハッシュ値そのもの、ハッシュ元の実値は含まない)
- provenance metadata(由来PDFのcontent_hash参照等)
- approval state(candidate/approved等のステータス値、reviewer識別子)
- 本設計文書を含む設計ドキュメント一式
- restore procedure(手順書としてのMarkdown)
- validation procedure(検証手順書としてのMarkdown)

### Gitに保存しない候補

- 実PDF(既存のPDF Registry管理、CLAUDE.md禁止事項と一貫)
- 実PDFのコピー
- Ground Truth実データそのもの(氏名・階級等の実値を含む可能性がある形式のデータ)
- 個人情報
- 大量のGround Truth raw data(構造ラベルであっても、大量データはリポジトリ肥大化を
  避けるため、`sample_pdfs/README.md`の「大量の実データは...別途データストア」
  という既存原則に倣いGit外とする候補)
- 外部ストレージの認証情報
- secret/token/password(`docs/configuration.md`の既存Secret管理方針に従う)

### 既存repoルールとの照合・差異報告

上記の区分は、CLAUDE.mdの実PDF・個人データコミット禁止、`.gitignore`の`/data/`
パターン、`docs/configuration.md`のSecret管理方針と整合しており、**矛盾・差異は
検出されなかった。**

## 16. Failure scenarios(失敗シナリオ)

`docs/operations/incident_response.md`の既存スタイル(失敗ケースごとの確認・対応
手順)に倣い、Ground Truthに固有のシナリオを列挙する(**対応手順の詳細は未確定、
シナリオの識別のみ本文書で行う**)。

| シナリオ | 想定される影響 | 対応の方向性(未確定) |
|---|---|---|
| 外部ストレージの一時的な障害 | Ground Truthへの読み取り不可(Resolver検証作業の
  一時停止) | バックアップ先からの一時利用、または障害復旧待ち(9章のrecovery
  requirements) |
| 外部ストレージの永続的な喪失 | manifestに記録されたラベルの根拠(元データ)が
  失われる | manifestの位置参照から、元PDF(既存のPDF Registry)を再確認し、
  再ラベリングが必要になる可能性(9章) |
| manifestとGround Truth実データの不整合(hash不一致) | ラベルの信頼性が疑わしい
  状態 | integrity requirements(10章)による検知、原因調査後の再同期または
  再ラベリング |
| 未承認のまま外部ストレージに書き込まれたデータ | Constitution §4の「人間は
  承認者」原則との整合性リスク | approval status(12章)が`candidate`のままの
  データは、Resolver検証等の確定的な用途に使用しないという運用上の区別
  (11章のAccess-control requirements) |
| Gate 1-C(承認プロセス)確定前にラベリングが進んでしまう | 手戻りリスク
  (承認プロセスに合わないラベルの再整理が必要になる) | Gate 1-Cの確定を
  Ground Truth実データ構築の前提条件とする(Task-E36の制約と整合、20章) |

## 17. Operational requirements(運用要件)

- `docs/operations/backup_restore.md`の既存運用フロー(Backup→Restore→
  Audit→Resume確認→正常確認)に類する、Ground Truth向けの運用フローを将来
  文書化することが望ましい(**本Task内では作成しない**、19章のApproval Gate参照)。
- 運用担当者が変更されても、本文書・manifest・(将来作成される)runbookから
  作業を再現できることを要件とする(7章の「担当者変更への耐性」と対応)。
- 外部ストレージへのアクセス権限は、`docs/security.md`の「最小権限」原則
  (既存)に従う候補とする(具体的な権限設計は未確定)。

## 18. Unresolved decisions(未解決事項、一覧)

1. 外部保存先の具体的な製品・サービス選定(ADR-0018のPDF Registryと同様、
   実装時に選定する候補)。
2. Backup frequency・retention世代数等の具体的パラメータ。
3. lifecycle状態名・遷移条件(Gate 1-C候補A/C選択に依存)。
4. Ground TruthがGold Databaseと同じ不変性原則(immutable snapshot)に従うべきか
   (Constitution §4適用範囲の解釈に依存、`ground-truth-decision-readiness.md`
   §4.2からの継続課題)。
5. manifest schemaの確定フィールド構成(12章は候補のみ)。
6. Approval workflow(14章)の対応表を実際に採用するか、Gate 1-C確定後に別途設計するか。
7. CategoryD 1:N/N:1エッジケースにおける構造パターン表現の実現可能性
   (Gate 1-A原文書§2.3、D未確認のまま)。
8. 運用runbook(17章)を別途作成するタイミング。

## 19. Approval gates(本文書が新たに要求する承認ゲート)

| ゲート | 内容 |
|---|---|
| Gate 1-B-i | 外部保存先の選定方針(ADR-0018のPDF Registry再利用か、独立した
  新規ストレージか)の決定。 |
| Gate 1-B-ii | Backup/Recovery/Integrityの具体的パラメータ(頻度・世代数・
  検証周期)の決定。 |
| Gate 1-B-iii | manifest schema(12章候補)の確定。 |
| Gate 1-B-iv | Versioning方針(immutable snapshotを採用するか)の決定
  (Constitution §4適用範囲の解釈と連動)。 |
| Gate 1-B-v | 運用runbook作成の要否・タイミング。 |

**これらはいずれも本文書内で確定しない。ユーザー承認を経て初めて次段階の設計・
実装に進む。**

## 20. POSITION AFTER TASK

- Current Phase: Ground Truth(Gate 1-B副次設計の要件整理完了、確定はいずれも未実施)
- Completed: 永続性・バックアップ・復旧・integrity・アクセス管理・manifest・
  versioning・approval workflow境界・Git/non-Git境界・失敗シナリオ・運用要件の
  整理(本文書)。既存repoパターン(PDF Registry/ADR-0018、`pdfs`テーブル、
  SHA-256標準、既存バックアップ運用文書)との整合性確認。
- Newly discovered: 既存のPDF Registry設計(ADR-0018)が、Ground Truthの
  Git外保存設計と構造的に極めて近い先例であること(内容アドレス方式・
  技術選定の先送り・年次再ハッシュ検証という契約の固定パターン)を確認した。
  これにより、Ground Truthの副次設計を「ゼロから設計する」のではなく
  「既存PDF Registryパターンを踏襲する」という選択肢が具体的に裏付けられた
  (ただし採用するかどうかは19章 Gate 1-B-iとして未確定のまま残す)。
- Still blocked: Ground Truth実データ作成、Block classificationの実データ検証、
  CategoryD 1:N,N:1の最終判断、Hybrid Section定義確定、Resolver threshold
  validation、Resolver implementation。
- Next approved decision: 19章「Approval gates」の5項目(Gate 1-B-i〜v)。
