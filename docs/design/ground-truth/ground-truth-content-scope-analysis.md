# Ground Truth Content Scope Analysis(Gate 1-A)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Gate 1-A(内容スコープ)の検証
- Completed: E14 corpus identity / ADR-0048 formalization・main merge / E14-E17 roadmap /
  CLAUDE.md DESIGN POSITION運用規則 / Ground Truth 6項目比較 / decision-readiness /
  storage-method comparison
- In Progress: Gate 1-A(内容スコープ)
- Blocked: Ground Truth実データ作成、Gate 1-B(格納方式)の確定、Gate 1-C(人間承認プロセス)の確定、
  Block classification確定、CategoryDResolver再設計、Hybrid rate discrepancy解消、
  Resolver threshold、Resolver実装
- This Task's Exit Condition: (i)位置参照・(ii)構造的判定ラベル・(iii)抽出値そのものの
  区分について、各Approval Gate(Block classification/Hybrid判定/CategoryD 1:N,N:1/
  Resolver threshold)ごとに必要な情報を整理し、結論候補(未確定)を提示すること

> 本文書は[`ground-truth-storage-method-comparison.md`](ground-truth-storage-method-comparison.md)
> §0で導入した(i)/(ii)/(iii)の区分を、Resolver前設計の各Approval Gateごとに個別検証したものである。
> 既存文書は上書きしない。**本文書内でも実データは一切作成しない。「(i)+(ii)のみ」は暫定設計候補
> であり、本文書内で自動的に確定させない。**

---

## 1. 検証対象の3区分(既存整理の再掲)

| 区分 | 内容 | 具体例 |
|---|---|---|
| (i) 位置参照 | PDF識別子(ファイル名またはハッシュ)・Section識別子・行/ブロック範囲等の
  位置情報 | `pdf=2022/0801a.pdf, section=20, lines=5-8` |
| (ii) 構造的判定ラベル | BlockKind分類、action/data関係、Hybrid判定、1:1/1:N/N:1構造分類等 | `BlockKind=post_only_fragment`、`Hybrid=true`、`adjacency=1action:2data` |
| (iii) 抽出値そのもの | 氏名・階級等、PDFから実際に読み取れる値 | `氏名: 髙橋一郎`(架空例) |

---

## 2. Approval Gateごとの必要情報の整理

### 2.1 Block classification(BlockKind判定)

**目的**(ADR-0048 §6): 各行が`self_contained`/`post_only_fragment`/`name_only_fragment`/`other`の
いずれに属するかを判定する基盤の妥当性を検証する。

**必要な情報**:
- (i) どのPDF・どのSection・どの行を指すか(必須)。
- (ii) その行に付与すべき正解BlockKindラベル(必須)。
- (iii) 氏名・階級等の実値は、BlockKind判定自体(「部署+階級+氏名が1行に揃っているか」という
  **構造的な問い**)には不要。判定に必要なのは「氏名らしき文字列があるか」「階級らしき文字列が
  あるか」という**構造的特徴の有無**であり、実際に何という氏名かは判定結果に影響しない。

**(iii)を除外した場合に失われる検証能力**: 「実際に付与されたラベルが、目視で見たときに
妥当か」という人間レビュー時の**文脈確認のしやすさ**が下がる可能性がある(レビュアーが
「なぜこの行がself_containedなのか」を確認する際、実際の行内容を見れば直感的に分かるが、
ラベルのみでは分かりにくい)。ただし、これは検証**能力**の喪失ではなく、レビュー**作業効率**の
低下であり、区別して扱う必要がある。

**結論候補(未確定)**: Block classificationの検証自体は(i)+(ii)で技術的に成立する。
(iii)はレビュー時の利便性向上に資するが、必須ではない。

### 2.2 Hybrid判定(Section-level)

**目的**(ADR-0048 §9): 同一Section内に`self_contained`とfragment blockが混在する
「Hybrid Section」かどうかを判定する。Hybrid Section比率78.0%(Task-E17 heuristic)vs
17.6%(Task-E4既存値)の乖離解消がRoadmap上の焦点。

**必要な情報**:
- (i) どのPDF・どのSectionを指すか(必須)。
- (ii) そのSectionが「Hybrid/Non-Hybrid」のいずれか、および内部のBlock構成(必須。
  2.1のBlock classificationラベルの集計として導出可能な場合もある)。
- (iii) 不要。Hybrid判定はSection内のBlock構成比率という**集計的な構造情報**であり、
  実際の氏名・階級の値には依存しない。

**(iii)を除外した場合に失われる検証能力**: なし(Hybrid判定はSection-level集計であり、
個々の行の実値とは無関係)。

**結論候補(未確定)**: Hybrid判定の検証は(i)+(ii)のみで完全に成立する。(iii)は不要と
考えられる。

### 2.3 CategoryD 1:N/N:1パターン(CategoryDResolverの隣接関係)

**目的**(ADR-0048 §8、Task-E17実データ検証): CategoryDResolverの「隣接する1:1
action↔data行ペア」という前提が、実データ上1action:2data・2action:1dataパターンで
崩れることが判明している。この再評価には、action行とdata行の対応関係(どの行とどの行が
どういう比率で対応するか)のラベルが必要。

**必要な情報**:
- (i) どのPDF・どのSection・どの行(action行・data行それぞれ)を指すか(必須)。
- (ii) action行とdata行の対応関係(1:1、1:N、N:1等の構造分類)ラベル(必須)。
- (iii) **ここが最も微妙な点**。「(旧職)＋新rank＋新name」パターン
  (`representative_case_verification.md`で確認済み)のような、**action行とdata行の対応が
  正しいかどうかを判定するために、部分的に実値の並び・構造(氏名が同一人物を指しているか等)を
  参照する必要が生じる可能性がある**。ただし、これも「氏名の実際の文字列が何か」ではなく、
  「同一行内・隣接行間で、氏名らしき文字列と階級らしき文字列がどう並んでいるか」という
  **構造的パターン**として表現できる可能性が高い(例: 「氏名(旧)+階級(新)+氏名(新)」という
  構造ラベルであり、実際の氏名の文字列そのものではない)。

**(iii)を除外した場合に失われる検証能力**: 「対応関係の判定が、たまたま構造が似ているが
実際には無関係な行同士を誤って対応付けていないか」という、**意味内容に基づく最終確認**が
やや弱くなる可能性がある。ただし、これはGate 1-Aの範囲で確定的に判断できることではなく、
実際にラベリングを試行してみないと分からない部分がある(未確定事項として残す)。

**結論候補(未確定)**: 大部分は(i)+(ii)で成立する可能性が高いが、一部のエッジケース検証で
(iii)相当の情報(ただし実際の氏名文字列である必要はなく、構造パターンとして表現できる可能性がある)
が必要になるかもしれない、という留保付きの結論。**この点は実データ検証(ラベリング試行)を
経てはじめて確定できる可能性があり、本文書内では確定しない。**

### 2.4 Resolver threshold validation

**目的**(Task-E17 `resolver_threshold_analysis.md`): block-level confidence・structural
evidence・adjacency・column consistency等の閾値候補について、実データでの分布・
false positive/negative率を測定する。

**必要な情報**:
- (i) どのPDF・どのSection・どのBlock/行を指すか(必須)。
- (ii) 正解ラベル(2.1〜2.3の集計)に対する、各閾値候補の予測結果との一致/不一致(必須)。
- (iii) 不要。閾値のprecision/recall評価は、正解ラベル(ii)と予測ラベルの比較のみで
  成立し、実際の氏名・階級の値には依存しない。

**結論候補(未確定)**: Resolver threshold validationの検証は(i)+(ii)のみで成立する。

---

## 3. (iii)を含めない場合の制約の明示

- **人間レビュー時の文脈確認しやすさが下がる**(2.1で指摘)。ラベルのみでは「なぜこの
  ラベルが正しいか」をレビュアーが直感的に把握しづらくなり、レビュー時に元のPDFを
  都度参照する必要が生じる(ただし、これは(i)の位置参照があれば、元のPDF(Git外・
  `data/`等)を別途参照することで解決可能であり、Ground Truthのラベルデータ自体に
  (iii)を埋め込む必要性を意味しない)。
- **CategoryD 1:N/N:1判定の一部エッジケースで、構造パターンとしての表現に留めるか、
  部分的に実値相当の情報が必要になるかが未確定**(2.3で指摘)。
- **抽出精度検証(パイプラインが氏名を正しく読み取れたか)という別目的には使えない**。
  これは`tests/golden`(合成データ)が既に部分的にカバーしている目的であり、Approval Gate 1
  (Block/Hybrid/Resolver構造検証)のスコープには含まれていない。

## 4. 個人データを保存しないことによる制約(まとめ)

| 制約 | 深刻度 | 対処の方向性(未確定) |
|---|---|---|
| レビュー時の文脈確認の手間増加 | 低 | (i)の位置参照から元PDF(Git外)を別途参照すればよい |
| CategoryD 1:N/N:1の一部エッジケースの表現力 | 中(未確定) | 構造パターンとしての表現方法を
  ラベリング試行時に個別検討する必要がある可能性 |
| 抽出精度検証への転用不可 | 該当なし | Approval Gate 1のスコープ外であり、制約ではない
  (別目的であり、`tests/golden`が担う) |

---

## 5. Gate 1-A 結論候補(未確定、承認前)

**結論候補**: Approval Gate 1が対象とする4種の検証(Block classification / Hybrid判定 /
CategoryD 1:N,N:1 / Resolver threshold validation)は、いずれも**(i)位置参照+(ii)構造的判定
ラベルのみで、大部分が成立しうる**。(iii)抽出値そのものは、Gate 1の目的においては
**原則として不要**と考えられるが、CategoryD 1:N/N:1の一部エッジケース判定において、
構造パターン表現で代替できるかどうかが未確定のまま残る。

**この結論候補は`Status: APPROVED`ではない。** ユーザー承認を経てはじめて、Gate 1-Bの
格納方式検討における前提として確定的に扱える。

## POSITION AFTER TASK(本文書時点)

- Current Phase: Ground Truth(Gate 1-A完了、結論候補提示。Approval未実施)
- Completed: 4つのApproval Gate(Block/Hybrid/CategoryD/Threshold)それぞれについて、
  (i)(ii)(iii)の必要性を個別に検証し、結論候補を整理
- Newly discovered: CategoryD 1:N/N:1判定の一部エッジケースにおいて、(iii)相当の情報
  (ただし実値そのものではなく構造パターンとして表現できる可能性がある)が必要になるかもしれない
  という留保が新たに識別された。これは実際のラベリング試行を経てはじめて確定できる可能性がある
- Still blocked: Gate 1-B(格納方式)・Gate 1-C(人間承認プロセス)の確定、Ground Truth実データ作成、
  以降のすべての後続作業
- Next approved decision: Gate 1-Aの結論候補(「(i)+(ii)を基本とし、(iii)は原則不要」)を
  承認するか、または修正を要するか
