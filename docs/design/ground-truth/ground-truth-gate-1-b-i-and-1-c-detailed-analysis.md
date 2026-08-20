# Gate 1-B-i(外部保存先)・Gate 1-C(人間承認プロセス) 詳細分析(承認済み作業順序 Step 1)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Ground Truth
- Current Phase: Ground Truth
- Current Subtask: 承認済み作業順序 Step 1(Gate 1-B-i / Gate 1-C 並行検討)
- Completed: E14 corpus recovery / E17 design recovery / ADR-0048 formalization /
  Gate 1-A partial approval / Gate 1-B方式2方向性 approval / Gate 1-C候補B除外 /
  E36 external storage design checkpoint/push(`4059145`) / Gate 1-B-i〜v options
  comparison / Gate 1-B承認順序分析(承認済み、Step1〜4の作業順序を採用)
- In Progress: Step 1(Gate 1-B-iとGate 1-Cの並行詳細分析、本文書)
- Blocked: Gate 1-B-ii/iii/iv/vの最終決定 / Gate 1-C候補A/C最終選択 /
  CategoryD D区分解消 / Ground Truth構築 / Resolver実装
- This Task's Exit Condition: Gate 1-B-iおよびGate 1-Cについて、具体的な選択肢・
  根拠・利点/欠点・依存関係・lock-in risk・可逆性を整理し、ユーザー承認待ちで
  提示すること(最終決定は行わない)

> 本文書は[`ground-truth-gate-1-b-approval-sequence-analysis.md`](ground-truth-gate-1-b-approval-sequence-analysis.md)
> (承認済み)が推奨したStep 1に対応する。同文書・
> [`ground-truth-gate-1-b-secondary-design-options.md`](ground-truth-gate-1-b-secondary-design-options.md)・
> [`ground-truth-human-approval-process.md`](ground-truth-human-approval-process.md)を
> 上書きしない。**本文書内でも、Gate 1-B-iの具体案(I-1/I-2/I-3)、Gate 1-Cの
> 具体案(候補A/C)のいずれも採用・確定しない。** 承認されたのは「この2項目を
> このタイミングで並行検討する」という作業順序のみである。

---

## 1. Gate 1-B-i(外部保存先選定方針)の詳細分析

### 1.1 選択肢の再掲

`ground-truth-gate-1-b-secondary-design-options.md` §Gate 1-B-iで整理済みの
3案(I-1: PDF Registry再利用/I-2: 独立ストレージ/I-3: 技術選定の先送り)を
前提に、以下の観点を追加する。

### 1.2 各案の詳細評価

| 評価観点 | 案I-1(PDF Registry再利用) | 案I-2(独立ストレージ) | 案I-3(先送り・契約のみ固定) |
|---|---|---|---|
| **根拠** | 既に運用実績のあるインフラを転用でき、Backup/Integrity
  (Gate 1-B-ii)の仕組みを新規設計せずに済む可能性がある | PDF Registry
  (本番・公表情報の永久保管、ADR-0018)とGround Truth(評価用・非公開・
  意図的に難しいケースを含む)という目的の異なるデータを、意図的に
  分離する | ADR-0018自身が「技術選定は実装時」という方針を採用しており、
  既存repoの一貫した設計哲学(契約を先に固定し、製品選定を遅らせる)と
  整合する |
| **利点** | 運用インフラの一本化。既存のバックアップ・integrity検証
  (年1回以上の再ハッシュ検証等)をそのまま転用できる可能性 | 目的の異なる
  データの混在によるガバナンス上の曖昧さを避けられる。PDF Registry
  (ADR-0018)自体への影響がない | 拙速な選定によるやり直しリスクを避け
  られる。Gate 1-Aの承認内容(Ground Truthは実値を含まない位置参照+
  構造ラベルが基本)により、Ground Truth自体のデータ量はPDF実体より
  大幅に小さく、フル規模の独立インフラを今すぐ用意する必要性は薄い |
  **欠点** | PDF Registryの意味論(「公表情報の長期保管」)とGround
  Truth(「Resolver検証用の評価データ」)を混在させることになり、
  将来PDF Registry側の設計変更(ADR-0018改訂)がGround Truthに意図せず
  波及するリスクがある | 運用インフラの二重化コスト。ただし、
  Ground Truthが(i)+(ii)スコープ(実値を含まない)にとどまる場合、
  実PDFそのもののコピーは発生しないため、想定されるほど大きな
  重複コストにはならない可能性がある(この点は本文書の新たな観察、
  1.4節参照) | 「選定方針」を問われている本項目に対し、「まだ決めない」
  という回答にとどまる。Gate 1-B-ii(Backup等)・Gate 1-B-iii(schema)の
  一部(source referenceの具体的な参照形式)が、この案のままでは
  「方針レベル」までしか詰められない |
| **依存関係(下流への影響)** | Gate 1-B-ii: PDF Registryの既存Backup
  レジーム(release.mdの表)を転用しやすくなる。Gate 1-B-iii:
  source referenceフィールドがPDF Registryのcontent_hashパス構造
  (`<hash[:2]>/<hash[2:4]>/<hash>`)と自然に整合する | Gate 1-B-ii:
  独自のBackup設計が必要。Gate 1-B-iii: source referenceの参照形式を
  ゼロから設計する自由度がある一方、PDF Registryとの対応関係を
  別途明示する必要がある | Gate 1-B-ii/iiiとも、「方針」レベル
  (頻度・世代数の考え方、schemaのフィールド構成候補)までは検討可能
  だが、「実装」レベル(具体的なAPIエンドポイント・ディレクトリ構造等)は
  確定できない |
| **Lock-in risk** | 中〜高(PDF RegistryとGround Truthのnamespaceが
  混在した状態から、後で分離しようとすると、PDF Registry自体の
  既存エントリに影響しないよう慎重な移行が必要になる) | 低〜中
  (独立して始めているため、後から統合する場合のコストはあるが、
  「分離されたものを統合する」方が「混在したものを分離する」より
  一般に安全) | 最低(何も選択していないため) |
| **可逆性(現時点)** | 高(実データが存在しないため) | 高 | 該当なし
  (選択自体がない) |
| **可逆性(Ground Truth実データ構築後)** | 低(PDF Registryとの
  混在を解消するには物理的なデータ移行が必要) | 中(独立ストレージ内での
  技術変更は、混在解消よりコストが低い) | 実データ構築開始までに
  結局i-1/i-2いずれかを選ぶ必要があるため、「先送り」自体の可逆性は
  議論の対象にならない(先送りが終わった時点でI-1/I-2いずれかの
  可逆性プロファイルに帰着する) |

### 1.3 Gate 1-B-iが他ノードに与える影響(Dependency Matrixの再確認、深掘り)

`ground-truth-gate-1-b-approval-sequence-analysis.md` §2の`i → ii`(○弱)・
`i → iii`(○弱)・`i → v`(●強)という評価は、本節の詳細評価によっても
裏付けられる。特に、**「i → ii」「i → iii」が「弱い」依存にとどまる理由**は、
Gate 1-A承認内容(実値を含まない)によりGround Truthのデータ規模自体が
小さく、どの案を選んでも「方針レベル」の検討はi確定前から進められるためで
あることが、本節の分析でより具体的に裏付けられた。

### 1.4 新たな観察(1.2節「利点」欄からの帰結)

Gate 1-Aの承認内容(Ground Truthは実値を含まない、(i)+(ii)基本)により、
**Ground Truthの外部保存データは、PDF実体そのもの(すでにPDF Registry管理下)を
複製するものではなく、位置参照・構造ラベル・approval metadataという軽量な
データにとどまる。** これは、案I-2(独立ストレージ)の「インフラ二重化コスト」を
一般的な想定より小さくする可能性がある一方、案I-1(PDF Registry再利用)の
「同居によるメリット」(容量の大きいデータを共通インフラで扱う効率)も同程度に
小さくなる。**したがって、i-1とi-2の優劣は、データ規模の観点からは
決定的な差にならない可能性が高く、むしろガバナンス上の分離(1.2節の
「欠点」欄)が相対的に重要な判断材料になりうる**、という観察が得られた。
**これは分析上の観察であり、いずれかの案への誘導ではない。**

---

## 2. Gate 1-C(人間承認プロセス)の詳細分析

### 2.1 前提(既承認事項、再審議しない)

`ground-truth-gate-1-c-final.md`(承認済み)より、候補B(ルールベース自動確定)は
不採用。以下は候補A・候補Cのみを対象とする。

### 2.2 各案の詳細評価

| 評価観点 | 候補A(AI提案+人間全件レビュー) | 候補C(人間が直接作成、AIは参考情報提示のみ) |
|---|---|---|
| **根拠** | Constitution §4「AIは提案者、人間は承認者」の原則に文字どおり
  対応する構造(AI提案→人間承認という2段階) | Constitution §4の原則を
  より厳格に解釈し、AIによる「提案」自体をラベルの形にしない
  (参考情報の提示にとどめる)ことで、人間の判断への影響を最小化する |
| **利点** | 人間の作業負荷を大幅に削減できる(ゼロから作成ではなく
  レビュー・修正)。AIの速度を活かし、サンプルサイズを拡大しやすい | Constitution
  §4への適合が最も厳格。AI提案への無自覚な追従(anchoring)リスクが
  構造的に発生しない |
  **欠点** | レビュー担当者がAI提案に無自覚に追従する(anchoring)リスクが
  ある。対策として、低確信度ケースの独立判断要求等の安全弁が別途必要
  (`ground-truth-human-approval-process.md`で既指摘) | 人間の作業負荷が
  候補Aより高く、AIの速度を活かせない。サンプルサイズによっては
  現実的に完了しない可能性が候補Aより高い |
| **依存関係(下流への影響)** | Gate 1-B-iv: 「候補(candidate)」と
  「承認済み(approved)」という2段階の状態が明確に存在するため、
  ハイブリッドVersioning案(IV-3、承認時にimmutable化)の「承認」
  イベントが「AI提案からの人間レビュー完了」として明確に定義できる。
  Gate 1-B-iii: schemaに「AI提案版」「人間承認版」を区別するフィールドが
  必要になる可能性がある | Gate 1-B-iv: 「人間が最初から作成する」ため、
  候補Aほど明確な「候補→承認」の2段階が存在しない(作成された時点で
  既に人間の判断を経ている)。IV-3の「承認」イベントの定義が、
  候補Aとは異なる粒度になる可能性がある。Gate 1-B-iii: AI提案版という
  概念が存在しないため、schemaがよりシンプルになりうる |
| **Lock-in risk** | 中〜高(後述2.3節、非対称性の観察) | 低〜中 |
| **可逆性(候補Aから候補Cへの変更)** | **低**。候補Aの下で生成された
  ラベルは、AI提案の影響を受けている可能性があるため、候補Cの厳格な
  基準に合わせるには、既存ラベルを人間が独立に(AI提案を見ずに)
  再作成する必要が生じうる。事実上、既存作業のやり直しに近いコストが
  発生する。 | — |
| **可逆性(候補Cから候補Aへの変更)** | — | **高**。候補Cの下で人間が
  直接作成したラベルは、その後AI支援を導入しても、既存ラベルの
  正当性(人間が独立に作成したという性質)は損なわれない。**将来の
  バッチにAI提案を導入するだけで済み、過去分の再作業は不要。** |

### 2.3 新たな観察: 候補A・候補C間の可逆性の非対称性

2.2節の可逆性評価から、**候補Aと候補Cの間には非対称な可逆性がある**ことが
明確になった。

- 候補C → 候補A への移行: 低コスト(過去のラベルはそのまま有効、
  将来分にAI支援を追加するだけ)。
- 候補A → 候補C への移行: 高コスト(過去のラベルがAI提案の影響を
  受けている可能性を排除できず、独立性を担保し直すには実質的な
  再作業が必要)。

**この非対称性は、Gate 1-Aの内容スコープ分析(Task-E29)やGate 1-Bの
Dependency Matrix分析(前Task)と同種の「仮説」であり、実際に候補Aで
ラベリングを試行した上での検証を経たものではない。** ただし、
Constitution §4の「承認という行為を省略・形骸化させる変更は...採用しない」
という原則に照らすと、**「まず厳格な候補Cで始め、必要に応じて候補Aへ
緩和する」方向の方が、「まず候補Aで始め、後から候補Cの厳格さを
求められた場合」より、後戻りのコストが小さい**という含意を持つ。
**これは観察であり、候補Cを推奨するものではない(2.4節で明示するとおり
最終判断はユーザーに委ねる)。**

### 2.4 Gate 1-Cの選択自体は依然として未確定

上記の分析は、候補A・候補Cの性質を明確化するものであり、**いずれかへの
決定ではない。** 承認単位(PDF/Section/Block/Label)・Constitution §4の
「Gold Database」「Knowledge Base」がGround Truthにどこまで適用されるかの
解釈という、既存の未解決事項(`ground-truth-decision-readiness.md` §4.2)も
引き続き未確定のまま残る。

---

## 3. Gate 1-BiとGate 1-Cの独立性(クロスチェック)

`ground-truth-gate-1-b-approval-sequence-analysis.md` §2 Dependency Matrixは
「iとCは互いに依存しない」と評価していた。本節では、**選択肢レベル**での
クロスチェックを行う。

- 案I-1/I-2/I-3(外部保存先)のいずれを選んでも、候補A/Cの評価(2.2節)は
  変化しない(外部保存先が物理的にどこであれ、「誰が承認するか」という
  プロセスの設計とは独立している)。
- 候補A/Cのいずれを選んでも、案I-1/I-2/I-3の評価(1.2節)は変化しない。

**したがって、選択肢レベルでも、iとCの独立性(並行検討可能)という
既承認の前提は再確認された。** これは新しい承認事項ではなく、
既存の承認(`ground-truth-gate-dependency-final.md`)の追加的な裏付けである。

---

## 4. Approval Matrix(Step 1範囲)

| 項目 | 選択肢 | 主要な新規知見 | User Approval |
|---|---|---|---|
| Gate 1-B-i | I-1/I-2/I-3 | Ground Truthのデータ規模が小さいため、
  I-1/I-2の「規模による優劣」は決定的でなく、ガバナンス上の分離が
  相対的に重要な判断材料になりうる(1.4節) | **PENDING** |
| Gate 1-C | 候補A/候補C | 候補A→候補Cの移行コストは高く、候補C→候補Aの
  移行コストは低いという**非対称性**(2.3節) | **PENDING** |

**いずれも確定していない。**

---

## 5. 未解決事項

1. Gate 1-B-iの最終選択(I-1/I-2/I-3)。
2. Gate 1-Cの最終選択(候補A/候補C)。特に、2.3節の非対称性の観察
   (「まずCから始めてAへ緩和する方が安全」という含意)をどう判断材料として
   使うか。
3. 1.4節・2.3節の「観察」自体が、実データでの検証を経ていない論理的推論に
   とどまることの取り扱い(参考情報として扱うか、追加の検証を要求するか)。

## 6. User Approval Required

1. Gate 1-B-i(I-1/I-2/I-3)の選択、またはさらなる検討の継続。
2. Gate 1-C(候補A/候補C)の選択、またはさらなる検討の継続
   (特に2.3節の非対称性の観察をどう扱うか)。
3. 上記が決まった場合、承認済み作業順序のStep 2(Gate 1-B-ii/iv セット検討)に
   進んでよいか。

## POSITION AFTER TASK

- Current Phase: Ground Truth(承認済み作業順序Step 1完了。Gate 1-B-i・
  Gate 1-Cいずれも最終選択は未実施)
- Completed: Gate 1-B-i(I-1/I-2/I-3)・Gate 1-C(候補A/候補C)それぞれについて、
  根拠・利点欠点・依存関係・lock-in risk・可逆性を整理。両者の独立性を
  選択肢レベルで再確認。
- Newly discovered: (1) Ground Truthのデータ規模の小ささ(Gate 1-A承認内容の
  帰結)により、Gate 1-B-iのI-1/I-2の優劣が規模の観点では決定的でないこと。
  (2) Gate 1-Cの候補A/候補C間に**非対称な可逆性**があり、候補C→候補Aの
  移行は低コストだが候補A→候補Cの移行は高コストであること。
- Still blocked: Gate 1-B-i最終選択、Gate 1-C最終選択、Gate 1-B-ii/iii/iv/v
  最終決定、CategoryD D区分解消、Ground Truth構築、Resolver implementation
- Next approved decision: 6章「User Approval Required」の3件
