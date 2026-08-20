# Ground Truth格納方式の比較(Approval Gate 1 / 4.1)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Ground Truth格納方針の決定
- Completed: Ground Truth 6項目比較([`ground-truth-options-comparison.md`](ground-truth-options-comparison.md))、既存ルール調査・decision-readiness整理([`ground-truth-decision-readiness.md`](ground-truth-decision-readiness.md))
- In Progress: Ground Truth格納方針(本文書)
- Blocked: Ground Truth構築、Resolver実装
- This Task's Exit Condition: Ground Truthの保存・参照方式について、既存ルールと矛盾しない方針を
  ユーザー承認可能な形で提示すること

> 本文書は[`ground-truth-options-comparison.md`](ground-truth-options-comparison.md)・
> [`ground-truth-decision-readiness.md`](ground-truth-decision-readiness.md)を基礎資料として使用し、
> 上書きしない。`ground-truth-decision-readiness.md` §4.1で提示した4方向性を、具体的な4つの格納方式
> として深掘りする。**本文書内でも、Ground Truthの実データは一切作成・生成・コピー・commitしない。**

---

## 0. 前提の明確化: Ground Truthは「実データそのもの」か「実データを参照するラベル」か

比較に先立ち、この区別を明示する。**これ自体は本文書内で確定させる事項ではなく、以降の比較を
正しく読むための概念整理である。**

Ground Truthが実際に保持しうる内容は、性質の異なる3種類に分解できる。

| 内容の種類 | 具体例 | 個人データ該当性 |
|---|---|---|
| (i) 位置参照(reference) | PDFファイル名/ハッシュ + Section番号 + 行範囲 | 該当しない(座標情報のみ、氏名等の値を含まない) |
| (ii) 構造的判定ラベル(structural label) | `BlockKind=self_contained`、`Hybrid=true`、
  「Section 20の行5〜8とdata行9はaction↔dataペア」等 | 該当しない(判定結果のみ、氏名等の値そのものは
  含まない) |
| (iii) 抽出値そのもの(literal field values) | 「氏名: 髙橋一郎」「階級: 三等陸佐」等、実際に
  PDFから読み取れる値を正解値として記載したもの | **該当する**(発令PDF記載の職務遂行情報、
  ADR-0008が定義する収集対象属性そのもの) |

`ground-truth-options-comparison.md` §1で整理した対象分類軸(Block classification / Hybrid判定 /
Resolver出力)は、いずれも**構造的な判定**であり、(i)+(ii)のみで検証可能である。すなわち、
「このPDFのこのSectionのこの行は`self_contained`である」というラベルは、氏名・階級の実際の
文字列(iii)を含めなくても成立する。

一方、(iii)が必要になるのは、**抽出精度そのもの**(「パイプラインが氏名を正しく読み取れたか」)を
検証する場合であり、これはADR-0007が既に扱う`tests/golden`の役割(ただし合成データで)と重なる。
Approval Gate 1が対象とする6項目(`ground-truth-options-comparison.md`参照)は、いずれも
Block/Hybrid/Resolverの**構造判定**を検証するためのものであり、抽出精度検証(iii)を明示的に
目的として含んでいない。

**したがって、Approval Gate 1の目的に限定する場合、Ground Truthは(i)+(ii)で成立しうる可能性が
高く、(iii)(個人データの実値)を必ずしも必要としない。** ただし、これは「(iii)を含めるべきでない」
という決定ではなく、**スコープの選択肢として明示する**にとどめる。以下の4方式の比較は、
(i)(ii)のみを想定した場合と、(iii)を含む場合の両方について言及する。

---

## 1. Confirmed facts(追加調査で得た関連事実)

| # | 事実 | 出典 |
|---|---|---|
| 1 | `.gitignore`は`/data/`を明示的に除外している。コメント: 「大容量の実データPDF
  （sample_pdfs/README.mdの基準を満たさないもの）意図的にコミットする場合のみgit add -fを使う
  運用とする」 | `.gitignore` L58-61(本Task確認) |
| 2 | `sample_pdfs/README.md`自身が「大量の実データは本リポジトリではなく、別途データストア
  （`data/`等、`.gitignore`対象）で扱う想定」と明記している | `sample_pdfs/README.md` |
| 3 | `docs/database/schema.md`の`pdfs`テーブル定義: 「実PDFファイル自体は本リポジトリでは
  管理しない（sample_pdfs/README.md）ため、`file_path`は本番運用時の外部ストレージ参照とする」 |
  `docs/database/schema.md` L174 |
| 4 | 本セッションの実行環境には現在`/data/`ディレクトリが存在しない(1643 PDF corpus自体は、
  過去Task実行時の環境にのみ存在し、本セッションの複数Task間で一貫して「リポジトリ外の
  何らかの場所」として扱われてきた) | 本Task確認(`ls /data`結果) |
| 5 | `DB/personnel.db`(Gold Database)は既にリポジトリにcommitされ、複数回のhash確認を通じて
  変更されていないことが継続的に検証されている(既存の正規経路の実例) | 本セッション全体を通じた
  継続的な確認 |
| 6 | `docs/review/domain.md`は`candidate_records`→`gold_records`という既存のレビューフロー
  (Candidate → Assigned → In Review → Modified → Approved → Gold Database)を定義している。
  このフローは「公開されるべき人事データ」を対象としており、Resolverアルゴリズムの正しさを
  検証するための評価データ(Ground Truth)を明示的な対象としていない | `docs/review/domain.md` |
| 7 | `tests/golden`は合成データのみを使用(`ground-truth-decision-readiness.md` §1-3で確認済み) | 同上 |

---

## 2. Design constraints(既存ルールからの制約)

- CLAUDE.md/AGENTS.mdの禁止事項は「実PDF・そこから抽出した個人データのコミット」を対象とする。
  0章の区分(iii)がこれに該当し、(i)(ii)は文言上直接には該当しない可能性が高い(ただし、
  (i)(ii)であっても「実在の人事発令PDFの具体的な内容を指し示す情報」である以上、間接的な
  懸念がまったくないとは言い切れない — この判断自体は本文書で確定しない)。
- ADR-0008は収集対象を「発令PDFに記載された、職務遂行に関する情報（氏名・階級・官職・所属・
  発令日等）」に限定しており、これは0章の(iii)そのものを指す。(i)(ii)はADR-0008が直接
  想定する「収集対象属性」には該当しない(位置情報・分類ラベルは氏名等の属性そのものではない)。
- Constitution §4は「人間は承認者」「AIはGold Databaseを書き換えない」「AIはKnowledge Baseを
  直接変更しない」を定める。Ground Truthはこのいずれの語にも字義どおり該当しないため
  (`ground-truth-decision-readiness.md` §4.2で既指摘)、どの程度の厳格さで人間承認を要するかは
  解釈次第。

---

## 3. 4方式の比較

### 方式1: 実データをGit管理する方式

| 評価軸 | 評価 |
|---|---|
| CLAUDE.md整合性 | (iii)を含む場合、禁止事項に直接抵触する可能性が高い。(i)(ii)のみの場合、
  文言上は該当しない可能性があるが、実PDFの内容を特定できる情報である点で、禁止事項の趣旨
  (実データの無秩序な拡散防止)にどこまで抵触するかは解釈が必要 |
| AGENTS.md整合性 | 同上 |
| ADR-0008整合性 | (iii)の場合、収集対象属性そのものであり、ADR-0008が想定する「正規経路
  (Gold DB)」を経ない収集・格納となる可能性がある。(i)(ii)は収集対象属性に該当しないため、
  この観点では問題になりにくい |
| Constitution §4整合性 | Gold Database/Knowledge Baseいずれにも該当しないため直接の禁止規定はないが、
  「人間は承認者」原則の適用として、AIが独断でcommit・pushすることは避けるべき(本セッション
  全体で一貫して採用してきた運用と同じ) |
| tests/golden既存運用との整合性 | (iii)を含む場合、明確に矛盾(既存は合成データのみ)。
  (i)(ii)のみの場合、tests/goldenが扱う対象(PDF→期待出力の一致検証)とは性質が異なるため、
  直接の比較対象にならない |
| 再現性 | 高い(Git履歴で完全に再現可能) |
| 監査可能性 | 高い(PR diff・commit履歴で追跡可能) |
| 個人データ管理上のリスク | (iii)を含む場合、非常に高い(Git履歴に永続化し、単純な削除では
  消えない。force pushや履歴書き換えは別途禁止されている操作)。(i)(ii)のみの場合、リスクは
  大幅に低いが、ゼロではない(実PDFの具体的な所在・構造を特定できる情報が公開される) |
| 次Taskへの引継ぎ容易性 | 非常に高い(clone直後から即座に参照可能) |
| Resolver validationへの利用可能性 | 高い(直接参照でき、実装・自動テストが書きやすい) |

### 方式2: 実データをGit外に保存し、Gitにはschema/manifest/ID/検証仕様のみ保存する方式

| 評価軸 | 評価 |
|---|---|
| CLAUDE.md整合性 | 高い。実データ(特に(iii))をコミットしないため禁止事項に抵触しない。
  `.gitignore`の`/data/`パターン、`pdfs.file_path`の外部参照設計という、**既存の2つの独立した
  先例と直接一致する** |
| AGENTS.md整合性 | 同上、高い |
| ADR-0008整合性 | 収集・格納自体はGit外で行われるため、リポジトリの制約と衝突しない。
  収集範囲の限定(氏名・階級等のみ)はGit外ストレージ側の運用として別途遵守が必要 |
| Constitution §4整合性 | schema/manifestはPRレビューを経てGitで承認プロセスを踏める。
  実データ自体(Git外)の承認プロセスは、Gitの仕組みでは保証されないため別途設計が必要
  (未解決事項として残る) |
| tests/golden既存運用との整合性 | 矛盾なし。tests/goldenは別の問題(回帰テスト)への別解
  (合成データ)であり、Ground Truthの実データ検証という異なる目的に対して、`pdfs.file_path`の
  外部参照パターンという**既存の先例に沿う** |
| 再現性 | 中程度。schema/manifestはGit管理下で完全に再現可能だが、実データ自体(Git外)の
  保全は別途のバックアップ・アクセス管理に依存する。本セッションが過去に経験した`/tmp`データ
  消失(Task-E15の復旧調査を要した事例)と同種のリスクが、Git外ストレージの選定・運用次第で
  再発しうる |
| 監査可能性 | 中程度。ラベル自体の変更履歴はGit(manifest)で追跡できるが、実データ自体の
  変更履歴はGit外のため別途の監査ログ機構が必要 |
| 個人データ管理上のリスク | 低い。Gitリポジトリ自体(フォーク・クローンで拡散する対象)には
  実データが含まれない |
| 次Taskへの引継ぎ容易性 | 中程度。manifestはリポジトリから即座に参照できるが、実データへの
  実際のアクセス手段(どこにあるか、どう取得するか)を別途明記する必要がある。ストレージの
  永続性(セッション・コンテナをまたいで消失しないか)の確認も必要 |
| Resolver validationへの利用可能性 | 高い。manifestが正しく実データを指し示せば、Resolver実装・
  テスト時にプログラム的に参照可能 |

### 方式3: Gold Database等の既存正規経路で管理し、設計文書から参照する方式

| 評価軸 | 評価 |
|---|---|
| CLAUDE.md整合性 | Gold DB自体は既存のcommit済み前例があるが、これは「サンプル目的以外の
  実データコミット禁止」の対象外として扱われてきた正規経路。GTをGold DBの一部として追加することが
  この例外の範囲に含まれるかは、Gold DBの目的(公開・配布データ)とGTの目的(内部評価データ)の
  違いから、単純に「含まれる」とは言えない |
| AGENTS.md整合性 | 同上 |
| ADR-0008整合性 | もっとも直接的に整合する。ADR-0008が想定する「防衛省公表情報の構造化格納」の
  正規経路そのもの |
| Constitution §4整合性 | 重要な緊張点。「AIはGold Databaseを書き換えない」「Gold Databaseへの
  反映は必ず人間のレビューを経る」という厳格な原則があり、GTをGold DBの一部として管理する場合、
  この厳格なレビュープロセス(review_sessions/review_changes等の既存機構)にそのまま従う必要がある。
  また、Gold DBは「公開・配布されるデータの正」という意味論を持つため、Resolver検証用の
  内部評価データ(誤りパターンや意図的に難しいケースを含む)を混在させると、Gold DBの意味論が
  曖昧になるリスクがある |
| tests/golden既存運用との整合性 | 目的が異なる(GT: Resolver検証、Gold DB: 本番公開データ)ため、
  直接の整合・矛盾なし |
| 再現性 | 高い(DBスキーマ・migrationで管理) |
| 監査可能性 | 非常に高い。既存の`review_sessions`/`review_changes`という専用の監査trail機構が
  そのまま使える |
| 個人データ管理上のリスク | 中程度。Gold DB自体は既に個人データを含む前提で設計されている
  (ADR-0008に基づく正規経路)ため新種のリスクは増えないが、「本来公開すべきでない中間評価データ」
  までGold DBに混入するリスクがある |
| 次Taskへの引継ぎ容易性 | 中程度。既存のRepository層経由でアクセス可能だが、新規テーブル追加
  等のスキーマ変更が必要な場合、ADR起票プロセスを要する可能性がある |
| Resolver validationへの利用可能性 | 高い(構造化DBのため、プログラム的な参照・照合が容易) |

### 方式4: 合成データをGit管理し、実データGround Truthは別管理する方式

**この方式は方式1〜3のいずれかと排他的な選択肢ではなく、「合成データ部分」と「実データ部分」を
組み合わせる複合的な方針である点に注意。** 実データ部分の具体的な格納先は、方式2または方式3
いずれかとの組み合わせが前提になる。

| 評価軸 | 評価 |
|---|---|
| CLAUDE.md整合性 | 合成データ部分は高い(既存tests/golden先例と完全に一致)。実データ部分は
  組み合わせる方式(2または3)の評価に従う |
| AGENTS.md整合性 | 同上 |
| ADR-0008整合性 | 合成データ部分は対象外(実在の公表情報ではない)。実データ部分は組み合わせる
  方式に依存 |
| Constitution §4整合性 | 合成データはGold Database/Knowledge Baseいずれにも該当しないため、
  人間承認は必要としつつも厳格な意味でのGold DB原則の対象外になる |
| tests/golden既存運用との整合性 | 合成データ部分は最も整合性が高い(既存パターンの直接拡張) |
| 再現性 | 合成データ部分は非常に高い。実データ部分は組み合わせる方式に依存 |
| 監査可能性 | 合成データ部分は高い(Git diff)。実データ部分は組み合わせる方式に依存 |
| 個人データ管理上のリスク | 合成データ部分はゼロ(架空データのため個人データが存在しない)。
  実データ部分は組み合わせる方式のリスクをそのまま引き継ぐ |
| 次Taskへの引継ぎ容易性 | 合成データ部分は非常に高い |
| Resolver validationへの利用可能性 | **重要な限界**: 合成データのみでは、Approval Gate 1が
  目指す「実データ上の未知パターンの発見・検証」(例: CategoryDResolverの1:N/N:1パターンは
  実データ検証で初めて発見された)という目的を達成できない。合成データGTは、Resolver実装後の
  「既知パターンの回帰確認」には有効だが、それだけでは実データGT(方式2または3)の代替にはならない |

---

## 4. Recommendation(推奨、確定ではない)

以下は検討の参考として示す推奨であり、**確定した設計判断ではない**。

- **0章の内容区分**: Approval Gate 1のスコープ(Block/Hybrid/Resolver出力という構造判定)に
  限定する場合、Ground Truthの内容は(i)位置参照+(ii)構造的判定ラベルで成立しうる可能性が高い。
  (iii)抽出値そのものを含めるかどうかは、抽出精度検証という別目的を今回のGate 1に含めるかどうかの
  判断次第であり、含めない方がリスク・複雑さを抑えられる。
- **格納方式**: 方式2(実データをGit外・schema/manifestのみGit管理)が、既存の2つの独立した先例
  (`.gitignore`の`/data/`パターン、`pdfs.file_path`の外部参照設計)と直接一致し、CLAUDE.md/
  AGENTS.mdの禁止事項との抵触リスクが最も低い。ただし、Git外ストレージの消失リスク対策
  (本セッションが過去に経験した`/tmp`データ消失と同種のリスク)を別途具体化する必要がある。
- 方式4(合成データ)は、方式2または3による実データGTの**補完**として、Resolver実装後の
  regression test(Roadmap Task Sequence第9段階)に活用する価値があるが、単独ではApproval Gate 1の
  目的を達成できない。

---

## 5. Unresolved decisions(未解決、ユーザー承認が必要)

1. **Ground Truthの内容スコープ**: (i)+(ii)(位置参照+構造判定ラベル)のみとするか、
   (iii)(抽出値そのもの)も含めるか。含める場合、CLAUDE.md/AGENTS.mdとの関係を個別に
   再整理する必要がある。
2. **格納方式**: 方式1〜4のいずれを採用するか(または複数の組み合わせ)。
3. 方式2を選ぶ場合、**Git外ストレージの具体的な場所・永続性の担保方法**(`/data/`は現環境に
   存在しないため、新規に用意する必要がある。過去の`/tmp`データ消失と同種のリスクへの対策)。
4. 方式3を選ぶ場合、**Gold DBへの新規テーブル追加等のスキーマ変更が必要かどうか**、および
   それに伴うADR起票の要否。
5. 方式2または3いずれの場合も、**実データ自体(Git外またはDB内)に対する人間承認プロセスの
   具体的な設計**(Constitution §4の「人間は承認者」原則をどう技術的に担保するか)。

---

## POSITION AFTER TASK

- Current Phase: Ground Truth(格納方式の比較完了、最終判断はユーザー承認待ち)
- Completed: 4方式(Git管理/Git外+manifest/Gold DB経由/合成データ+別管理)を10の評価軸
  (CLAUDE.md・AGENTS.md・ADR-0008・Constitution §4・tests/golden整合性・再現性・監査可能性・
  個人データリスク・引継ぎ容易性・Resolver validation利用可能性)で比較する本文書の作成。
  「Ground Truthは実データそのものか、実データを参照する構造的ラベルか」という区分を明示し、
  この区分が格納方式の評価そのものに影響することを整理した
- Newly discovered: `.gitignore`の`/data/`除外パターンと`docs/database/schema.md`の
  `pdfs.file_path`外部参照設計という、**既存repoに独立して2箇所存在する「実データをGit外で
  管理する」明確な先例**を確認した。これは方式2の実行可能性を強く裏付ける事実である。また、
  Ground Truthの内容を「位置参照+構造判定ラベル」に限定すれば、氏名・階級等の実値(個人データ)を
  一切含めずに済む可能性があるという、格納方式の議論全体の前提を変えうる整理が得られた
- Still blocked: Ground Truthの実際の構築、格納方式の最終決定、内容スコープの最終決定、
  Block classification定義検証以降のすべての後続作業
- Next approved decision: 上記「Unresolved decisions」5件、特に(1)内容スコープと(2)格納方式の
  組み合わせについてのご判断
