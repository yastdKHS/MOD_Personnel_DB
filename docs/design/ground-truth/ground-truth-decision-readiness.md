# Ground Truth設計判断: 既存ルール確認・矛盾整理・承認可能な判断材料

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Ground Truth設計判断
- Completed: Corpus identity / ADR-0048 / E14-E17 roadmap / CLAUDE.md運用規則 / Git checkpoint(`37f9fa5`) / 6項目の設計比較([`ground-truth-options-comparison.md`](ground-truth-options-comparison.md))
- In Progress: Ground Truth設計判断(既存資料の確認・矛盾整理・承認可能な判断材料の確定)
- Blocked: Ground Truth作成、Resolver実装
- This Task's Exit Condition: 6項目についてユーザー承認可能な判断材料を確定すること

> 本文書は[`ground-truth-options-comparison.md`](ground-truth-options-comparison.md)を**再作成・
> 上書きしない**。同文書の内容をそのまま基礎資料として扱い、追加調査の結果を本文書に記録する。
> 特に、同文書「6. 保存形式・格納場所」で指摘した「CLAUDE.mdとADR-0008の間の緊張関係」について、
> 関連する既存設計文書（ADR-0007、ADR-0008、AGENTS.md、`sample_pdfs/README.md`、
> `tests/golden`の実際の構成、`docs/review/domain.md`）を追加調査した。
>
> **本文書内でも新しい設計判断は行わない。** 6項目のいずれについても確定・承認済み扱いにしない。

---

## 0. 追加調査で参照した資料

- [`docs/adr/0007-golden-file-testing.md`](../../adr/0007-golden-file-testing.md)（ゴールデンファイルテスト戦略）
- [`docs/adr/0008-data-ethics-policy.md`](../../adr/0008-data-ethics-policy.md)（個人情報・データ倫理方針）
- [`docs/constitution.md`](../../constitution.md) §4 AI Principles(原文の正確な引用)
- [`CLAUDE.md`](../../../CLAUDE.md) 禁止事項節
- [`AGENTS.md`](../../../AGENTS.md) 禁止事項節
- [`sample_pdfs/README.md`](../../../sample_pdfs/README.md)
- `tests/golden/`の実際のファイル構成・内容(`tests/golden/sample_pdfs/2026_format_sample_20260701_synthetic.pdf`、対応する`sample_outputs/*.json`)
- [`docs/review/domain.md`](../../review/domain.md)(Candidate → Gold Databaseのライフサイクル)

---

## 1. 既存ルールで確定している事項

これらは、本Taskの追加調査によって新たに「確定」させたものではなく、**既存の承認済み文書に
既に明記されている事実**であり、Ground Truth設計にそのまま適用される制約として扱ってよい。

| # | 確定事項 | 出典 |
|---|---|---|
| 1 | 実在の人事発令PDF（サンプル目的以外）や、それらから抽出した個人データをリポジトリに
    コミットしない。サンプルは`sample_pdfs/README.md`の基準を満たすもののみ | CLAUDE.md 禁止事項、
    AGENTS.md 禁止事項(「実PDF・実データ（サンプル基準を満たさないもの）のコミット」)— **両文書で
    独立に、同一趣旨が明記されている** |
| 2 | `sample_pdfs/README.md`の収録基準は「`layouts/`の各`era_id`に対して最低1件」という
    レイアウト検証目的の**最小限**サンプルに限定される。網羅的収録は行わない | `sample_pdfs/README.md` |
| 3 | **既存の`tests/golden`実装は、実在の発令PDFではなく合成（synthetic）データを使用している。**
    `tests/golden/sample_pdfs/2026_format_sample_20260701_synthetic.pdf`のゴールデンファイル
    (`sample_outputs/....json`)には`"$comment"`フィールドで「合成データ、実在の発令PDFではない」と
    明記され、記載されている氏名も実在人物ではない架空の値（例: `"髙橋一郎"`）が使われている | 実ファイル確認(本Task) |
| 4 | Gold Database(`DB/personnel.db`)は、Constitution §4が定める「公開・配布されるデータの正」であり、
    人間レビューを経た経路からのみ更新される。AIはGold Databaseを書き換えない | `docs/constitution.md` §4 |
| 5 | AIはKnowledge Base(`knowledge/`)を直接変更しない。ドメイン知識は人手でレビューされるべき
    正データである | `docs/constitution.md` §4 |
| 6 | ADR-0008により、収集・格納の対象は「防衛省が公務として一般に公表した人事発令情報」に限定され、
    収集する属性も発令PDF記載の職務遂行情報（氏名・階級・官職・所属・発令日等）に限定される。
    利用目的は透明性・検索性向上に限定される | `docs/adr/0008-data-ethics-policy.md` |
| 7 | `docs/review/domain.md`が定める`Candidate`(候補レコード)は、Validatorの出力（検証NG・低confidence）
    であり、Gold Databaseに至る前段のレビュー待ち状態を表す既存スキーマ概念(`candidate_records`)。
    これはResolver設計・Ground Truthの検証目的とは異なる、本番パイプラインのレビューフローに
    固有の概念である | `docs/review/domain.md` |

---

## 2. 既存資料間で矛盾している事項

**明示的な矛盾(相互に反する記述)は見つからなかった。** ただし、以下は「矛盾」ではなく、
**適用範囲が重ならない・どちらの原則がGround Truthに適用されるか未確定**という種類の緊張関係
であるため、区別して記録する。

### 2.1 CLAUDE.mdの禁止事項 vs ADR-0008の許容範囲(緊張関係、矛盾ではない)

- CLAUDE.mdは「実PDF・抽出個人データのコミット禁止（サンプル目的以外）」という**リポジトリへの
  コミットに関する制約**を定める。
- ADR-0008は「公表人事発令情報の収集・格納自体はプロジェクトの目的の範囲内」という**プロジェクト
  全体としての収集・利用方針**を定める。
- 両者は矛盾していない。ADR-0008が許容する収集・格納は、**Gold Database(`DB/personnel.db`)という
  正規の経路(パイプライン→人間レビュー→Gold DB)を前提**にしており、CLAUDE.mdの禁止事項が対象とする
  「サンプル目的以外の実PDF・抽出データの無秩序なコミット」とは異なる経路を指している。
- **つまり「実データをリポジトリに格納すること自体」がADR-0008で無条件に許可されているわけではなく、
  Gold DBという正規経路を経ることが前提**であり、CLAUDE.mdの禁止事項はそれ以外の経路（テスト
  フィクスチャ・一時ファイル等としての無秩序な格納）を防ぐものと解釈するのが整合的である。

### 2.2 「実データでの検証が必要」という目的 vs 既存golden test実装の選択(実務上のトレードオフ、矛盾ではない)

- Ground Truthの目的（Resolver設計の閾値決定・CategoryDResolverの1:N/N:1パターン検証等）は、
  1643件の**実PDF**から得られる実データパターンを対象にすることを前提としている
  （`ground-truth-options-comparison.md` §2 母集団の議論）。
- 一方、既存の`tests/golden`は、レイアウト回帰検知という別目的のために、意図的に**合成データ**を
  選んでいる(ADR-0007はこの選択の理由を明示的には述べていないが、実際の運用は合成データのみ)。
- これは「矛盾」ではなく、**目的が異なれば妥当な設計判断も異なりうる**という一般的な事実の
  確認にすぎない。ただし、Ground Truthが`tests/golden`と同じ格納場所（`sample_pdfs`/`sample_outputs`
  相当の場所）を単純に転用しようとすると、既存の「合成データのみ」という運用実態と衝突する
  可能性がある点は、設計上考慮すべき事実として記録する。

**結論**: 「矛盾」と呼べる既存資料間の対立は見つからなかった。むしろ、既存資料(特に`tests/golden`の
実装実態)は、CLAUDE.mdの禁止事項が実務上どう解釈・運用されてきたかを示す**強い先例**として機能して
おり、Ground Truthの設計に直接示唆を与える。

---

## 3. 追加調査によって明確になったこと(前回報告からの更新)

前回(`ground-truth-options-comparison.md`)では、CLAUDE.mdとADR-0008の関係を「本文書内では
解消できない緊張関係」とだけ記録し、推奨案を示さなかった。今回の追加調査により、以下が
判明した(ただし、これは**選択肢を1つに絞り込む結論ではなく、既存の先例を明確にしたもの**である)。

- **既存の先例(`tests/golden`)は、「実データでの検証が必要な場面でも、実在PDFの抽出データを
  そのままリポジトリに格納しない」という運用を一貫して取っている。** 合成データに架空の氏名を
  使うという具体的な手法まで含めて、CLAUDE.mdの禁止事項を厳格に遵守する形で実装されている。
- **したがって、「Ground Truthがリポジトリにコミットされる」という前提を取る場合、実PDFから
  抽出した実際の氏名・階級等の値をそのまま含める形式は、既存の先例と矛盾する可能性が高い。**
- 一方で、Ground Truthの目的(1643件の実PDF・実データパターンの検証)は、合成データでは
  代替できない性質を持つ(合成データは「作成者が想定した範囲のパターン」しか含まないため、
  未知の実データ上の例外パターン(1action:2data等)を発見・検証する目的には原理的に不向き)。
- **この2つの要求(実データが必要／実データをリポジトリにそのまま置けない)は、根本的に
  両立しない可能性がある。** これは新たに作られた矛盾ではなく、既存ルールの帰結として
  今回初めて明示的に浮かび上がった構造的な緊張である。

---

## 4. ユーザー判断が必要な事項

以下は、既存資料の調査だけでは解決できない、新しい設計判断を要する事項である。
**本Task内では、いずれについても判断を確定しない。**

### 4.1 [最優先] 実データを扱うGround Truthの格納方針そのもの

上記3章の構造的緊張(実データが必要／実データをそのまま置けない)をどう解決するかについて、
以下のような方向性が考えられる(列挙であり、いずれかへの誘導ではない)。

- 方向i: Ground Truthをリポジトリ外(別ストレージ)で管理し、リポジトリには参照情報
  (PDF名・Section番号・ラベル種別等、実際のフィールド値を含まない)のみを残す。
- 方向ii: Ground Truthの正解値を、実際の氏名・階級の文字列そのものではなく、
  「抽出結果が正しいか否か」という判定ラベルのみに限定する(実データの再掲を避ける)。
- 方向iii: `sample_pdfs`と同様の「基準を満たすサンプル」という位置づけを再定義し、
  Ground Truth用に限定的に拡張したサンプル基準を`sample_pdfs/README.md`の改訂として
  別途提案する(この場合、`sample_pdfs/README.md`自体の変更が必要になり、既存の
  「レイアウト検証目的の最小限サンプル」という基準の見直しを伴う、比較的大きな決定になる)。
- 方向iv: Gold Database(`DB/personnel.db`)が既に「防衛省公表情報の構造化格納」の正規経路として
  存在することを踏まえ、Ground Truthを独立した新しいデータ種別として作らず、既存のGold DB/
  Candidateパイプラインの枠組みを何らかの形で再利用する(ただし、Ground Truthは「Resolverの
  アルゴリズムを検証するための正解データ」であり、「公開されるべき人事データそのもの」とは
  目的が異なるため、単純な再利用が適切かは別途検討が必要)。

**この判断は、6項目のうち他の5項目(対象分類軸・母集団・サンプルサイズ・ラベリングスキーマ・
ラベリング主体)すべてに先行して必要になる可能性が高い。** 格納方針が決まらなければ、
「どのPDFを何件、どんな形式でラベル付けするか」という残り5項目の設計自体が具体化できない。

### 4.2 Constitution §4「Gold Database」「Knowledge Base」の適用範囲の解釈

Ground Truthは、Constitution §4が明示的に定義するいずれの語(Gold Database・Knowledge Base)にも
字義どおりには該当しない(`ground-truth-options-comparison.md` §5で既指摘)。この解釈自体を
ユーザーに確認する必要がある。「人間は承認者である」という上位原則が語の定義を問わず適用される
という解釈でよいか、それとも別の整理が必要かは未確定。

### 4.3 (前回文書からの継続) 対象分類軸・母集団・サンプルサイズ・ラベリングスキーマ・ラベリング主体

`ground-truth-options-comparison.md`で整理済みの5項目についても、追加調査によって既存ルールとの
新たな矛盾は見つからなかった一方、確定にも至っていない。4.1の格納方針が決まった後に、
具体的な選択が可能になる。

---

## 5. 判断しない場合に後続Taskへ与える影響

| 項目 | 判断保留を続けた場合の影響 |
|---|---|
| 4.1 格納方針 | 後続の「Ground Truth構築」Taskが着手不能なまま。Roadmap Task Sequence第1段階
  (Ground Truth設計・構築)がブロックされ続け、第2段階以降(Block classification定義検証等)も
  連鎖的に着手できない |
| 4.2 Constitution適用範囲の解釈 | ラベリング主体・承認プロセス(既存比較文書の項目5)の確定が
  できないため、仮に格納方針(4.1)が決まっても、「誰が・どう承認するか」が未定のままラベリング
  作業を始めることになり、後から「Constitution違反ではないか」という手戻りリスクが残る |
| 4.3 残り5項目 | 4.1・4.2の解決を待つ形で自然にブロックされる。個別に先行して仮決定しても、
  4.1の結論次第で無効になる可能性が高いため、先行決定は非推奨(既存比較文書のrecommended optionは
  あくまで参考情報として維持) |

**総合的な影響**: 4.1(格納方針)の判断が、事実上Ground Truth設計全体のボトルネックになっている。
これを保留し続けると、Roadmap全体(Ground Truth → Block classification検証 → CategoryDResolver
再評価 → Hybrid-rate解消 → Resolver threshold → Resolver実装 → ...)が、実質的に最初の段階で
停止したままになる。

---

## 6. 明確に確定できる事項(参考、承認不要)

以下は、既存ルールから直接導かれる、Ground Truth設計における「争いのない前提」であり、
改めてユーザー承認を要しない(既存の承認済み方針の単純な適用にすぎないため)。

- `2023/0313a.pdf sec9`は引き続きGround Truthの根拠から除外する(ADR-0048・roadmap・
  Task-E15/E17と一貫)。
- 39.2%・78.0%・17.6%のいずれも、Ground Truth設計の確定した前提数値としては使用しない
  (未検証のheuristic由来、または出典・定義が未解決のため)。
- Rule E原式・BlockKindの`BlockEvidence`フィールドはMEDIUM confidenceのまま扱い、
  Ground Truthラベリングスキーマの必須項目として無条件に採用しない
  (`ground-truth-options-comparison.md` §4で既指摘、変更なし)。
- ADR-0048は変更しない。Ground Truth設計・格納方針の検討結果、ADR-0048の改訂が必要と
  判断される場合は、別途新規ADR起票プロセスを経る(CLAUDE.mdの既存手順どおり)。

---

## POSITION AFTER TASK

- Current Phase: Ground Truth(設計判断の準備段階。既存ルール確認・矛盾整理を完了、
  最終判断はユーザー承認待ち)
- Completed: 既存資料(ADR-0007・ADR-0008・Constitution・CLAUDE.md・AGENTS.md・
  `sample_pdfs/README.md`・`tests/golden`実装実態・`docs/review/domain.md`)の追加調査、
  既存ルールで確定している事項(7件)の整理、既存資料間の関係整理(矛盾ではなく緊張関係と判明)、
  ユーザー判断が必要な事項の階層化(4.1格納方針が他項目に先行するボトルネックであることの明確化)
- Newly discovered: 既存の`tests/golden`実装が、実在PDFではなく合成データ(架空の氏名を含む)を
  意図的に使用していることを実ファイル確認により発見した。これは、CLAUDE.mdの禁止事項が
  実務上どう厳格に運用されているかを示す直接的な先例であり、「実データが必要なGround Truthを
  リポジトリにそのまま格納すること」と「実PDF由来データのコミット禁止」という2つの要求が、
  既存の運用実態に照らすと根本的に両立しない可能性がある、という構造的な緊張が新たに明確になった。
- Still blocked: Ground Truthの実際の構築、6項目(特に4.1格納方針)の最終決定、Block classification
  定義検証、CategoryDResolver再評価、Hybrid-rate解消、Resolver threshold、Resolver実装。
- Next approved decision: 4.1(実データを扱うGround Truthの格納方針、4つの方向性のいずれを
  検討の起点とするか)についてのご判断が、他のすべての判断に先行して必要。次点で4.2
  (Constitution §4の適用範囲の解釈)。
