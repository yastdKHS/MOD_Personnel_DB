# Ground Truth Human Approval Process(Gate 1-C)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Gate 1-C(人間承認プロセス)の検証
- Completed: Gate 1-A(内容スコープ、結論候補)、Gate 1-B(格納方式、結論候補)
- In Progress: Gate 1-C(人間承認プロセス)
- Blocked: Ground Truth実データ作成、以降のすべての後続作業
- This Task's Exit Condition: ラベリング主体・承認プロセスの候補A〜Dを、承認単位・
  disagreement処理・reviewer identity・timestamp・version・change history・再レビュー条件
  の観点で比較し、結論候補(未確定)を提示すること

> 本文書は[`ground-truth-options-comparison.md`](ground-truth-options-comparison.md) §5・
> [`ground-truth-decision-readiness.md`](ground-truth-decision-readiness.md) §4.2で既に
> 提示した「案P」「案Q」の議論を土台に、より具体的な4候補(A/B/C/D)として深掘りする。
> **本文書内でもラベル・承認プロセスの実運用は一切開始しない。**

---

## 1. Constitution §4の原則の確認(既存整理の再掲、変更なし)

`docs/constitution.md` §4原文:
> 「AIはGold Databaseを書き換えない」「AIはKnowledge Baseを直接変更しない」
> 「人間は承認者である」「承認という行為を省略・形骸化させる変更は...採用しない」

Ground Truthは、Constitution §4が明示的に定義する「Gold Database」「Knowledge Base」の
いずれにも字義どおりには該当しない(`ground-truth-decision-readiness.md` §4.2で既指摘、
変更なし)。しかし、「人間は承認者」「承認という行為を省略・形骸化させない」という**上位の
原則**は、データの種別を問わず適用されると解釈するのが安全側であり、本文書もこの解釈を
前提に候補を比較する(ただし、この解釈自体の確定はユーザー判断による、`ground-truth-decision-
readiness.md` §4.2の未解決事項のまま)。

---

## 2. 候補A〜Dの比較

### 候補A: AIが候補ラベルを生成 → 人間が全件レビュー → 人間がGold化を承認

| 観点 | 内容 |
|---|---|
| AIがGold labelを書き換えてよいか | AIは「候補」段階までしか関与せず、最終確定(Gold化)は
  常に人間が行う。AIがGoldを直接書き換えることはない |
| AIが候補ラベルを生成することは許容されるか | 許容される(Constitution §4は「AIは提案者」を
  明示的に認めている) |
| 承認の単位 | 全件(PDF・Section・Block・Labelいずれの粒度でも、人間が個別に目を通す) |
| disagreementの扱い | 人間がAI提案に同意しない場合、人間の判断がそのまま採用される
  (人間が最終権限を持つため、disagreement自体は発生しない設計) |
| reviewer identity | 記録する場合、レビューした人間の識別情報(承認者名等)を各ラベルに
  紐付ける設計が可能 |
| approval timestamp | 各ラベルの承認日時を記録可能 |
| version | AI提案版・人間承認版を区別して記録可能(2版構成) |
| change history | 全件レビューのため、AI提案からの変更点(修正の有無・内容)を
  逐一記録できる |
| 再レビュー条件 | ラベリングスキーマ変更時・Resolver設計変更時等に、全件または
  影響範囲を再レビューする運用が考えられる |
| 長所 | Constitution §4への適合が最も明確・厳格 |
| 短所 | 人間の作業負荷が高い(サンプルサイズによっては現実的な完了が困難、
  `ground-truth-options-comparison.md` §5で既指摘) |

### 候補B: AIが候補ラベルを生成 → 人間が不確実ケースのみレビュー → 残りはルールベースで確定

| 観点 | 内容 |
|---|---|
| AIがGold labelを書き換えてよいか | **重要な論点**: 「ルールベースで確定」する残りの
  ケースについて、最終的にGold化する主体が実質的にAI(またはルール)になり、人間の
  個別レビューを経ないままGold相当のステータスに達する。これはConstitution §4の
  「承認という行為を省略・形骸化させる変更は...採用しない」という原則に**抵触する
  可能性が高い** |
| AIが候補ラベルを生成することは許容されるか | 生成自体は許容されるが、確定プロセスに
  問題がある |
| 承認の単位 | 「不確実ケース」のみ人間が個別レビューし、それ以外は自動確定という
  非対称な単位 |
| disagreementの扱い | ルールベース確定分については、人間が同意・不同意を判断する
  機会自体がない |
| reviewer identity / approval timestamp | 不確実ケースのみ記録可能。自動確定分には
  「承認者」が実質的に存在しない |
| version / change history | 自動確定分は「AI提案=最終版」となり、人間による変更履歴が
  生じない |
| 再レビュー条件 | 「不確実」の閾値をどう設定するかという、新たな設計判断(閾値決定)を
  要する。この閾値自体がまだ存在しないResolver thresholdの議論と類似した循環に陥る可能性 |
| 長所 | 人間の作業負荷を大幅に削減できる |
| 短所 | Constitution §4との整合性に明確な懸念がある。**この候補は、他の候補と対等な
  選択肢としてではなく、Constitution上のリスクが高い候補として扱うべきである** |

### 候補C: AIは分類候補を提示するだけ → 人間がGround Truthラベルを直接作成 → AIはGoldを書き換えない

| 観点 | 内容 |
|---|---|
| AIがGold labelを書き換えてよいか | 一切書き換えない。AIの関与は「参考情報の提示」
  (該当PDF箇所の抽出・整形、過去の類似ケースの提示等)にとどまる |
| AIが候補ラベルを生成することは許容されるか | 「候補ラベル」という形でのAI生成は行わず、
  「分類の選択肢」や「判断材料」の提示にとどめる、候補Aよりもさらに保守的な設計 |
| 承認の単位 | 人間がゼロから作成するため、全件が必然的に人間作成(候補Aの「全件レビュー」
  よりもさらに人間の関与度が高い) |
| disagreementの扱い | 該当しない(AIがラベルを提案しないため、disagreementという概念が
  発生しない) |
| reviewer identity / approval timestamp / version / change history | 候補Aと同様に
  記録可能(むしろ「レビュー」ではなく「作成」なので、記録の単純さでは候補Aよりやや有利) |
| 再レビュー条件 | 候補Aと同様 |
| 長所 | `ground-truth-options-comparison.md` §5の「案P」に相当し、Constitution §4への
  適合が候補Aよりもさらに厳格 |
| 短所 | 人間の作業負荷が候補Aよりもさらに高く、AIの速度を活かせない。サンプルサイズに
  よっては現実的に完了しない可能性が候補Aより高い |

### 候補D: その他、既存repositoryの原則と整合する方式(検討用の例示)

本Task内では特定の代替案を確定しないが、候補A/Cの中間的な設計として、以下のような
バリエーションが理論上考えられる(**あくまで検討材料の例示であり、推奨ではない**)。

- 候補D-1: 候補Aと同じ(AI提案+全件人間レビュー)だが、レビュー時に「独立判断」フラグを
  設け、AI提案を見る前に人間が一度自分の判断を記録してからAI提案と突き合わせる、
  という順序を追加する(`ground-truth-decision-readiness.md`・`ground-truth-options-
  comparison.md`で既に指摘した「anchoring対策」)。
- 候補D-2: 候補Aをベースに、複数人のレビュアーによるダブルチェック(2名以上が独立に
  レビューし、不一致があれば議論して確定する)を導入する。ただし、これは前提として
  複数のレビュアーが確保できることを要し、実行可能性はユーザーの体制次第。

**候補Dはいずれも未確定の検討材料であり、候補A/B/Cのような正式な比較対象ではない。**

---

## 3. 承認単位(PDF/Section/Block/Label)についての追加整理

いずれの候補(A/C)を採用する場合でも、「人間が何の単位でレビュー・承認するか」は
別途の設計判断を要する。

| 単位 | 特徴 |
|---|---|
| PDF単位 | 1つのPDF全体を一括で確認・承認。粒度が粗く、レビュー漏れのリスクがあるが、
  文脈(PDF全体の構成)を把握しやすい |
| Section単位 | Hybrid判定(Gate 1-A §2.2)の検証に直接対応する自然な単位 |
| Block単位 | Block classification(Gate 1-A §2.1)の検証に直接対応する自然な単位。
  粒度が細かく、レビュー件数が多くなる |
| Label単位 | 個々のラベル値そのものを承認単位とする、最も細かい粒度。厳密だが
  作業量が最大になる |

**Gate 1-Aの結論候補(4つのApproval Gateがそれぞれ異なる粒度の情報を必要とする)を踏まえると、
承認単位を単一の粒度に固定する必要はなく、Gate種別ごとに異なる単位(Block classificationは
Block単位、Hybrid判定はSection単位等)を採用する余地がある。** ただし、これも本文書内では
確定しない。

---

## 4. Gate 1-C 結論候補(未確定、承認前)

**結論候補**:

1. 候補B(ルールベース自動確定を含む方式)は、Constitution §4「承認という行為を省略・
   形骸化させる変更は...採用しない」という原則との整合性に明確な懸念があるため、
   **候補A・Cと対等な選択肢としては推奨しない**。
2. 候補A(AI提案+人間全件レビュー)と候補C(人間が直接作成、AIは参考情報提示のみ)は
   いずれもConstitution §4に整合するが、作業負荷とConstitution適合の厳格さの
   トレードオフが異なる。候補Aは効率と適合のバランスが取れた案として検討に値する
   (`ground-truth-decision-readiness.md` §4.2の「案Q」と同じ位置づけ)が、
   候補Cの方がより保守的で誤解の余地が少ない。
3. 承認単位は、Approval Gate種別(Block/Hybrid/CategoryD/Threshold)ごとに異なる粒度を
   使い分けることが、Gate 1-Aの結論候補と整合的である可能性がある。

**いずれも結論候補であり、`Status: APPROVED`ではない。**

## 5. 未解決事項

1. 候補A・C・(D系列)のいずれを採用するか。
2. Constitution §4の「人間は承認者」原則が、Ground Truthという(字義上は明示されていない)
   データ種別にどこまで厳格に適用されるべきかの解釈そのもの(`ground-truth-decision-
   readiness.md` §4.2から継続する未解決事項)。
3. 承認単位をGate種別ごとに使い分けるか、単一の単位に統一するか。
4. disagreement処理・reviewer identity・version管理の具体的な技術的実装方法
   (Gate 1-Bの格納方式が決まらないと、これらの技術的実装は具体化できない —
   7章で依存関係として整理)。

## POSITION AFTER TASK(本文書時点)

- Current Phase: Ground Truth(Gate 1-C完了、結論候補提示。Approval未実施)
- Completed: 候補A/B/C/Dの比較(AIのGold書き換え可否・候補生成の許容性・承認単位・
  disagreement処理・reviewer identity・timestamp・version・change history・再レビュー条件)、
  承認単位(PDF/Section/Block/Label)の追加整理
- Newly discovered: 候補B(ルールベース自動確定)がConstitution §4「承認の省略・形骸化
  防止」原則との整合性に明確な懸念を持つことが、比較を通じて具体的に明確になった。
  また、承認単位をApproval Gate種別ごとに使い分ける余地があるという整理が得られた
- Still blocked: Ground Truth実データ作成、disagreement処理等の技術的実装(Gate 1-Bの
  格納方式確定が前提)、以降のすべての後続作業
- Next approved decision: Gate 1-Cの結論候補(候補B除外、候補A/Cいずれかへの絞り込み)、
  および承認単位の方針
