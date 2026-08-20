# Ground Truth設計オプション比較(Approval Gate 1、詳細版)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Ground Truth設計(6項目の選択肢比較)
- Completed: Corpus identity / ADR-0048 / E14-E17 roadmap / CLAUDE.md運用規則 / Git checkpoint(`37f9fa5`, push済み) / Ground Truth設計提案書初版([`ground-truth-design-proposal.md`](ground-truth-design-proposal.md))
- In Progress: 6項目それぞれについて、confirmed facts / design constraints / available options /
  advantages-disadvantages / unresolved decisions / recommended option(未確定)を整理する本文書の作成
- Blocked: Ground Truthの実データ構築、Block classification定義検証、CategoryDResolver再評価、
  Hybrid-rate discrepancy解消、Resolver threshold validation、Resolver implementation
- This Task's Exit Condition: 6項目すべてについて上記6要素を整理し、最終的な設計判断はユーザー承認待ちとして
  提示すること(Ground Truthの実データは作成しない)

> 本文書は[`ground-truth-design-proposal.md`](ground-truth-design-proposal.md)(Task-E28で作成した
> 初版提案、選択肢の概要提示)を土台に、6項目それぞれを`confirmed facts / design constraints /
> available options / advantages-disadvantages / unresolved decisions / recommended option`の
> 6要素で整理し直したものである。初版提案書の内容を置き換えるものではなく、より詳細な比較を
> 追加するものと位置づける。
>
> **本文書内でもGround Truthの実データ(ラベル付きサンプル)は一切作成しない。** 「recommended
> option」は検討の参考として示すが、確定事項として扱わない。最終判断はユーザー承認を経る。

---

## 1. 対象分類軸

### Confirmed facts

- ADR-0048 §6: Block classification(`self_contained`/`post_only_fragment`/`name_only_fragment`/`other`)。
- ADR-0048 §9: Hybrid Section(同一Section内にself_containedとfragment blockが混在)。
- ADR-0048 §7-8: CMassResolver/CategoryDResolverの出力(最終的なRawRecord候補)。
- Rule E原式(Task-E15復旧、MEDIUM confidence)は`fragment_pairs_min`・`block_separation_ratio`・
  `self_contained_ratio`というBlock集計値を組み合わせたSection単位判定式であり、**Rule Eの検証
  自体がBlock分類レベルの入力を前提とする**(`docs/design/e14-e17-roadmap.md`引用元と同一)。
- Task-E17実データ検証で、CategoryDResolverの1:1前提が崩れるケース(1action:2data等)が
  `2022/0801a.pdf sec20`・`2023/1222d.pdf sec4`で確認済み — この検証にはResolver出力レベルの
  ラベルが必要。

### Design constraints

- Block classification(a)はResolver出力(c)の前提情報であり、依存順序が一方向(a→c)。
  Hybrid判定(b)もBlock集計に基づく式であるため、実質的に(a)に依存する。
- Constitution §4「人間は承認者」原則により、ラベリング作業量は人間のレビュー負荷に直結する。
  3軸同時着手は初期設計コスト・レビュー負荷を最大化する。

### Available options

- 案1: (a)Block classificationのみを先に整備し、(b)(c)は後続段階で追加する。
- 案2: (a)(b)(c)を同一サンプルセットに同時にラベル付けする。
- 案3: (b)Hybrid判定のみを最優先する。

### Advantages / Disadvantages

| 案 | 利点 | 欠点 |
|---|---|---|
| 案1 | 依存順序(a→b,c)に沿っており手戻りが少ない。ADR-0048の4分類は既にAccepted状態で語彙が
  安定している。他の2軸は(a)のラベルから部分的に導出できる可能性がある | Hybrid-rate discrepancy
  (Roadmap上の直近の焦点)を直接解消しない。Section集約ロジック自体が未実装のため、(a)だけでは
  (b)の答えが自動的には出ない |
| 案2 | レビュー対象PDFへのアクセスが1回で済み、労力効率が良い | 3スキーマを同時に確定する必要があり
  初期設計コストが高い。Resolver出力ラベル(c)はCategoryDResolver再設計(未決定)に依存するため、
  先に固定すると再設計後に手戻りが生じるリスクが高い |
| 案3 | Roadmap上の直近のボトルネック(78.0% vs 17.6%)に直接対応する | Block分類レベルの内訳データ
  なしにSection単位の二値判定のみを行うと、Rule E自体(Block集計式)の検証には使えず、別軸の
  ラベリングが結局必要になる可能性が高い |

### Unresolved decisions

- どの軸から着手するか、または部分的に同時進行するか。
- (c)Resolver出力軸は、CategoryDResolverの1:1前提再設計(Roadmap Approval Gate 3)が先に固まって
  からラベリングすべきか、それとも先にラベリングして再設計の材料にすべきか(順序が循環しうる)。

### Recommended option(未確定)

案1(Block classificationを先に整備)。理由: 依存順序上もっとも上流であり、他の2軸のいずれの
検証にも再利用できる可能性が高く、手戻りリスクが小さいため。ただし、これは推奨であり、
最終選択はユーザー承認による。

---

## 2. 母集団

### Confirmed facts

- 1643 PDF corpus(683 direct + 960 WARP、bijection確認済み)。
- 1400/1643(85.2%)がSection抽出成功。232 PDFs(14.1%)がlayout confidence不足で0-Section。
  11 PDFs(2018年)がCID font encoding crash。
- 121 encrypted PDFsのうち99件が`cryptography`導入下でSectionまで到達(Task-E14実測)。
  `cryptography`はリポジトリの正式依存関係には未反映(`pyproject.toml`/`uv.lock`変更なし、
  検証用venvへの一時追加のみ)。

### Design constraints

- 232 PDF・11 PDFはSectionそのものが得られないため、Section/Block単位のGround Truth母集団には
  そもそも含まれない(自然に除外される)。
- CLAUDE.mdの「依存ライブラリの新規追加...は要確認」原則により、`cryptography`を正式依存化する
  ことは本Taskの範囲外(別途ADR判断が必要、Task-E14のユーザー承認事項として既に提示済み・未回答)。
- Ground Truth構築自体は(Task-E14が実施したのと同様に)検証用venvへの一時的な`cryptography`追加で
  実施可能であり、正式依存化の可否とは技術的に分離できる。ただし、Ground Truthとして選定した
  サンプルが将来、正式依存化されなかった場合に処理不能な99件を含んでいると、Resolver実装後の
  regression testで扱いに困る可能性がある。

### Available options

- 案A: Section抽出成功1400 PDFs(encrypted PDFを除く)を母集団とする。
- 案B: 1400 + encrypted 99件 = 1499 PDFsを母集団とする(cryptography正式依存化の可否とは切り離す)。

### Advantages / Disadvantages

| 案 | 利点 | 欠点 |
|---|---|---|
| 案A | 依存関係の論点を完全に排除できる。母集団の定義がシンプル | encrypted PDF特有のパターン
  (存在するかは未確認)がGround Truthに反映されない。母集団のカバレッジがやや狭い |
| 案B | より広いカバレッジ。将来`cryptography`が正式依存化された場合に備えられる | 依存関係の
  正式化(未承認事項)とGround Truth構築を事実上結びつけてしまう。`cryptography`が最終的に
  不採用となった場合、99件分のラベルが「処理できないPDF」に対するラベルとして扱いに困る可能性 |

### Unresolved decisions

- encrypted PDFを含めるか。
- `cryptography`正式依存化の判断(Task-E14からの既存未回答事項)をGround Truth構築より先に
  済ませるべきか。

### Recommended option(未確定)

案A(encrypted PDFを含めない、1400 PDFsを母集団とする)。理由: 依存関係の未決事項と
Ground Truth構築を分離することで、後者を先に進められるため。ただし将来的にencrypted PDF
対応が必要になった場合、別途追加ラウンドでのGround Truth拡張を妨げるものではない。

---

## 3. サンプルサイズ・抽出方法

### Confirmed facts

- 過去(Task-E5)は99 Sections。抽出基準・方法は完全にUNRECOVERABLE(`/tmp/taskE15/11_unrecoverable_items.md`)。
- Task-E14実測: 1400 PDFsから2,776 Sections抽出。
- layout_id分布: `2015_2017_format_a` 328 PDFs、`2018_2026_format_a` 1072 PDFs(Task-E14実測)。
- Task-E17 heuristic(未検証)によるBlock構成比率: self_contained 40.0% / post_only_fragment 5.9% /
  name_only_fragment 6.1% / other 48.0%。**この比率自体は本文書のサンプル設計の参考情報として
  扱うが、未検証のheuristicによる値であるため、確定した層化基準としては使用しない**(39.2%・78.0%・
  17.6%等と同様、新しい確定事実として扱わない)。
- 既知5ケース(`08_known_case_validation.csv`): `2022/0314a.pdf sec17`(whitespace-collapse)、
  `2022/0801a.pdf sec20`(C-MASS仮説)、`2023/1222d.pdf sec4`(Category D)、`2017/1201a.pdf sec10`
  (representative)はいずれも実在確認済み。`2023/0313a.pdf sec9`は出典不明として除外継続。

### Design constraints

- Constitution §4「人間は承認者」原則により、サンプルサイズは人間のレビュー可能量が実質的な上限。
- layout_id分布に偏り(328 vs 1072)があるため、無作為抽出のみでは少数派(`2015_2017_format_a`)の
  代表性が低くなるリスクがある。
- Task-E17 heuristic自体の妥当性が未検証であるため、これを層化基準に使うと「未検証の分類器で
  ground truthのサンプル設計をする」という循環になりうる。layout_id・年といった客観的に観測可能な
  属性を層化基準に使う方が、この循環を避けられる。

### Available options

- 案X: 過去と同規模(約100 Sections)を無作為抽出する。
- 案Y: layout_id・年別に層化抽出する(客観的に観測可能な属性のみを基準とする)。
- 案Z: 既知4ケース(sec9を除く)を明示的に含め、残りを無作為または層化で補う。

### Advantages / Disadvantages

| 案 | 利点 | 欠点 |
|---|---|---|
| 案X | 実装が単純。過去規模との比較が可能(ただし過去の抽出方法は不明なため比較の意味は限定的) |
  layout_idの偏りを反映せず、少数派eraの代表性が低くなるリスク |
| 案Y | 母集団の構造的な偏り(layout_id・年)を代表させられる。層化基準が客観的でheuristicに依存しない |
  層数×各層のサイズ設計という追加の意思決定が必要になり、単純な無作為抽出よりやや複雑 |
| 案Z | 既存の質的知見(Task-E13/E17で確認済みの代表ケース)をGround Truthに明示的に組み込める |
  4件はいずれも過去Taskでのアドホックな発見であり、体系的な代表性の担保にはならない
  (補助的な位置づけにとどめるべき) |

### Unresolved decisions

- 最終的なサンプルサイズ(規模)。
- 層化を行う場合の層の定義・各層のサイズ配分。
- 既知4ケースを「必須組み込み」とするか「参考情報」にとどめるか。

### Recommended option(未確定)

案Y(layout_id・年による層化抽出)に、既知4ケース(案Zの要素)を追加で組み込むハイブリッド。
規模は過去(99)と同程度からの開始が妥当と考えられるが、最終値はユーザー承認事項とする。

---

## 4. ラベリングスキーマ

### Confirmed facts

- ADR-0048 §6: 4分類(`self_contained`/`post_only_fragment`/`name_only_fragment`/`other`)は
  「復旧された設計の到達点」として明記され、5番目のAMBIGUOUS分類は明示的に不採用とされている。
  ただし、AMBIGUOUS非採用の詳細な論拠自体はTask-E15調査でも復旧できていない(原文書未発見)。
- `BlockEvidence`のフィールド名(`has_paren`・`has_rank_token`・`has_name_tail`・`prefix_length`・
  `column_count`)はMEDIUM confidence(圧縮summary経由)で復旧されているが、各フィールドの
  算出ロジック詳細は未復旧。

### Design constraints

- 本Task-E29(今回)の指示で「Rule E / BlockKindのMEDIUM confidenceを昇格しない」ことが
  明示的に要求されている。`BlockEvidence`のフィールド定義をそのままラベリングスキーマの
  必須項目として採用すると、MEDIUM confidenceの内容を暗黙に「確定仕様」として扱うことになりかねず、
  注意が必要。
- ADR-0048自体は変更しないという制約があるため、ラベリング中に4分類で表現しきれないケースが
  見つかった場合でも、その場でADR-0048を書き換えることはできない(新規ADR起票プロセスが必要)。

### Available options

- 案I: ADR-0048の4分類をそのままラベル語彙として採用する。
- 案II: ラベリング作業を進めながら、4分類で表現困難なケースを別途記録し、語彙自体の見直し要否を
  ラベリング完了後にまとめて検討する。

### Advantages / Disadvantages

| 案 | 利点 | 欠点 |
|---|---|---|
| 案I | 既にAccepted状態のADR-0048と完全に整合する。ラベリング開始が早い | 4分類で表現しきれない
  実例が見つかった場合、無理に`other`へ押し込めることで分類の情報量が低下するリスク |
| 案II | 実データから4分類の妥当性そのものを検証できる。ADR-0048改訂の要否判断に資する材料が
  得られる | ラベリング途中でスキーマが変わると、既にラベル付けした分の見直しが必要になる可能性。
  「見直し」自体が新たな設計判断であり、勝手に確定しない運用と整合させる必要がある |

### Unresolved decisions

- ラベリング開始前に語彙を完全固定するか、記録しながら検証を並行するか。
- `BlockEvidence`の各フィールド(算出ロジック未復旧)を、ラベリング時の判断根拠メモとして
  人間が自由記述で残す運用にするか、それとも今回は使わずBlockKindの最終ラベルのみを付与するか。

### Recommended option(未確定)

案I(ADR-0048の4分類をそのまま採用)を起点としつつ、案IIの要素(表現困難ケースの記録)を
安全弁として併用する。`BlockEvidence`の各フィールドはMEDIUM confidenceのため、今回は
必須ラベル項目とせず、任意の判断根拠メモにとどめることを推奨する。

---

## 5. ラベリング主体・承認プロセス

### Confirmed facts

- Constitution §4(原文引用、`docs/constitution.md`ではGold **Database**・Knowledge **Base**という
  具体的な語を用いている):
  > 「AIはGold Databaseを書き換えない」「AIはKnowledge Baseを直接変更しない」「人間は承認者である」
- Ground Truthは、Constitutionが明示的に定義する「Gold Database」(`DB/personnel.db`)・
  「Knowledge Base」(`knowledge/`)のいずれとも、字義どおりには一致しない第三のデータ種別である。
- ADR-0008(個人情報・データ倫理方針): 「この方針を超える利用...は、AGENTS.mdの規定により、
  AIエージェントが独断で実装してはならない」。

### Design constraints

- Constitutionの字義上、Ground Truthは「Gold Database」にも「Knowledge Base」にも該当しないため、
  §4の禁止事項がGround Truthに直接適用されるかどうかは**解釈の余地がある**。ただし、
  「人間は承認者である」「承認という行為を省略・形骸化させる変更は...採用しない」という
  上位原則は、データの種別を問わず適用されると解釈するのが安全側。
- Ground Truthは今後Resolver実装のthreshold決定・regression testの基準として使われる
  (Roadmap Task Sequence 5「Resolver threshold validation」、9「regression verification」)ため、
  実質的にGold相当の役割を担う。

### Available options

- 案P: 人間がラベルを最初から最後まで自ら確定し、AIは候補提示(PDF該当箇所の抽出・整形)のみを行う。
- 案Q: AIが初期ラベル案(4分類のいずれか+根拠メモ)を生成し、人間が全件レビュー・修正して確定する。

### Advantages / Disadvantages

| 案 | 利点 | 欠点 |
|---|---|---|
| 案P | Constitution §4の原則にもっとも厳格に整合する。AI提案への無自覚な追従リスクがない | 人間の
  作業負荷が非常に高く、サンプルサイズによっては現実的に完了しない可能性がある |
| 案Q | 人間の負荷を大幅に低減できる(ゼロから作成ではなくレビュー・修正)。AIの速度を活かせる。
  最終確定は人間が行うため、「人間は承認者」の原則自体は維持される | レビュー担当者がAI案に
  無自覚に追従する(anchoring)リスクがある。この対策(低確信度ケースを別途フラグする等)が
  別途必要になる |

### Unresolved decisions

- Constitution §4の「Gold Database」「Knowledge Base」という具体的な語がGround Truthに
  厳密に適用されるかどうかの解釈そのもの。
- 案Qを採る場合の、anchoring対策の具体的な設計(例: AI案の確信度が低い項目は「レビューのみ」ではなく
  「独立判断」を人間に求める、等)。

### Recommended option(未確定)

案Q(AI案生成+人間全件レビュー・確定)を、anchoring対策(低確信度ケースの独立判断要求)と
セットで採用することを推奨する。ただしConstitution §4の解釈自体は本文書内で確定できる事項では
なく、ユーザーの判断を仰ぐ必要がある。

---

## 6. 保存形式・格納場所

### Confirmed facts

- `docs/design/e14-e17-roadmap.md` §12は、Ground Truthそのもの(データ)を`docs/design/`配下に
  保存しないことを既に規定している。
- CLAUDE.md禁止事項: 「実在の人事発令PDF（サンプル目的以外）や、それらから抽出した個人データを
  リポジトリにコミットしない。サンプルは`sample_pdfs/README.md`の基準を満たすもののみ」。
- `sample_pdfs/README.md`: 収録基準は「`layouts/`の各`era_id`に対して最低1件」という
  レイアウト検証目的の最小限サンプルに限定されており、Ground Truth用途(層化抽出された
  100件規模のサンプル)とは目的・規模が異なる。
- ADR-0008: 収集・格納対象は「防衛省が公務として一般に公表した人事発令情報」に限定、
  利用目的は透明性・検索性向上に限定。
- `DB/personnel.db`は既にリポジトリにcommitされている(本セッションで繰り返しhash確認済み)— 
  すなわち、構造化された人事発令データそのものをリポジトリで保持すること自体は、
  既存の設計(Gold Database)として認められている。

### Design constraints(重要な発見)

**Ground Truthのラベルには、実際の氏名・階級・所属等のフィールド値そのもの(正解値として)を
含める必要が生じる可能性が高い。** これは「発令PDFから抽出した個人データ」に該当しうる。
CLAUDE.mdの禁止事項は「サンプル目的以外」の実PDF・抽出データのコミットを禁じており、
Ground Truthはレイアウト検証(`sample_pdfs`の目的)とは異なる目的(Resolver検証)のデータで
あるため、**この禁止事項に文字どおり抵触する可能性がある**。

一方で、ADR-0008は「防衛省が公務として一般に公表した人事発令情報」の収集・格納自体は
プロジェクトの目的の範囲内と位置づけており、`DB/personnel.db`という前例が既に存在する。
したがって、Ground Truthを「新たな種類の氏名・階級データの集積」として`knowledge/`や
`tests/fixtures/`に置くことは、CLAUDE.mdの禁止事項の趣旨(無秩序なPDF・個人データの増殖防止)と
ADR-0008の許容範囲(公表データの構造化格納自体は目的内)のどちらを優先すべきかという、
**本文書内では解決できない緊張関係**がある。

### Available options

- 案i: `knowledge/`配下に格納する。
- 案ii: `tests/fixtures/`または`tests/golden`に準じた形で格納する(Resolver実装後の
  regression testとの親和性を意図)。
- 案iii: リポジトリ外の別ストア(既存の`docs/adr/0035`等が触れる「Storage Abstraction」的な
  発想に近い)に格納し、リポジトリには参照情報(どのPDF・どのSection・ラベル種別か、実際の
  フィールド値は含まない)のみを残す。
- 案iv(本文書で新たに識別): ラベルを「正誤判定のみ」(氏名・階級の実値を含めず、抽出結果が
  正しいかどうかの二値/分類ラベルのみ)にとどめ、実値の再掲を避ける形式にする。

### Advantages / Disadvantages

| 案 | 利点 | 欠点 |
|---|---|---|
| 案i | `knowledge/`は既に人手レビュー対象データの前例がある | 用途がドメイン知識(表記ゆれ等)と
  異なり、CLAUDE.mdの「knowledge/配下のデータを一括置換・自動生成で書き換えない」という
  運用ルールとの整合を別途整理する必要がある |
| 案ii | `tests/golden`という既存の「PDF→期待出力」比較の前例と概念的に近く、Roadmap終盤の
  regression verificationと自然に接続する | CLAUDE.mdの「実在PDFからの抽出データコミット禁止」の
  対象になりうる点は解消しない。tests/配下だからといって同ルールの例外にはならない |
| 案iii | CLAUDE.mdの禁止事項(個人データのリポジトリコミット)を根本的に回避できる | リポジトリ外
  ストアの消失リスク(本セッションで既に経験した`/tmp`データ消失と同種のリスク)がある。
  参照情報のみのリポジトリ管理は、Task-E15のような復旧困難な状態を再現しかねない |
| 案iv | 個人データそのものの再掲を避けつつ、リポジトリ内(`docs/design/`に準じた場所や
  `tests/fixtures/`)に格納できる可能性がある | 「正誤判定のみ」のラベルでは、後続のRule E
  検証(fragment_pairs_min等の集計)や、なぜ誤りと判定したかの根拠追跡が難しくなる可能性がある |

### Unresolved decisions

- CLAUDE.mdの「実PDF・抽出個人データのコミット禁止」がGround Truthに適用されるかどうかの解釈。
- 案iv(実値を含めない正誤判定形式)で、Resolver threshold検証に必要な情報量が確保できるかの
  技術的検証。
- リポジトリ内外どちらに格納するか、および消失リスクへの対策。

### Recommended option(未確定)

**本項目は6項目の中で唯一、明確な推奨案を示さない。** CLAUDE.mdの禁止事項とADR-0008の
許容範囲との緊張関係(上記Design constraints参照)が本文書内では解消できないためである。
この解釈自体をユーザー承認事項として提示する(下記まとめ参照)。

---

## まとめ: ユーザー承認事項

1. **対象分類軸**: 案1(Block classification先行)を推奨するが、着手順序の最終決定が必要。
2. **母集団**: 案A(encrypted PDF除く1400 PDFs)を推奨するが、`cryptography`正式依存化の
   判断(Task-E14からの既存未回答事項)との関係整理も含め、最終決定が必要。
3. **サンプルサイズ・抽出方法**: 案Y+既知4ケースのハイブリッドを推奨するが、規模・層の定義の
   最終決定が必要。
4. **ラベリングスキーマ**: 案I(ADR-0048の4分類採用)を起点とすることを推奨するが、
   `BlockEvidence`フィールドの扱い(必須項目化しない)を含め、最終決定が必要。
5. **ラベリング主体・承認プロセス**: 案Q(AI案+人間全件レビュー)を推奨するが、
   Constitution §4の「Gold Database」「Knowledge Base」という語がGround Truthに
   どこまで適用されるかの解釈自体が、まず必要。
6. **保存形式・格納場所**: **推奨案なし。** CLAUDE.mdの実PDF・個人データコミット禁止と
   ADR-0008の許容範囲との関係整理が、他のすべての項目に先立って必要になる可能性がある
   (この整理次第で、案i〜ivの実行可能性そのものが変わる)。

**特に6番目は、他の5項目よりも先に解決すべき前提問題である可能性が高い**(格納場所が
決まらなければ、案i/iiのいずれも実PDFの抽出データをどこにも安全に置けないことになりかねない)。
この点を含め、次の判断をユーザーに仰ぐ。

## POSITION AFTER TASK

- Current Phase: Ground Truth(6項目の選択肢比較完了、確定はいずれも未実施)
- Completed: 6項目それぞれについてconfirmed facts / design constraints / available options /
  advantages-disadvantages / unresolved decisions / recommended option(未確定)の整理
  (本文書、`Status: DRAFT`)
- Newly discovered: Ground Truthの保存形式・格納場所について、CLAUDE.mdの「実PDF・個人データ
  コミット禁止」原則とADR-0008の「公表データの構造化格納は目的内」という許容範囲の間に、
  本文書内では解消できない緊張関係があることが判明した。これは他の5項目に先立って解決すべき
  可能性がある前提問題である。また、Constitution §4が明示的に定義する「Gold Database」
  「Knowledge Base」のいずれにもGround Truthが字義どおりには該当しないという解釈上の論点も
  新たに識別した。
- Still blocked: Ground Truthの実際の構築(6項目の最終決定待ち)、Block classification定義検証、
  CategoryDResolver再評価、Hybrid-rate解消、Resolver threshold、Resolver実装。
- Next approved decision: 上記6項目、特に「6. 保存形式・格納場所」の解釈(CLAUDE.mdとADR-0008の
  関係整理)についてのご判断。
