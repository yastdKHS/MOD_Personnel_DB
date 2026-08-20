# Ground Truth設計提案(Approval Gate 1)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Ground Truth候補データの定義調査・設計選択肢の提示
- Completed: Corpus identity / ADR-0048 / E14-E17 roadmap文書化・CLAUDE.md運用規則(Task-E28、git checkpoint `37f9fa5`、push済み)
- In Progress: Ground Truth仕様・採用基準の設計(本文書)
- Blocked: Block classification定義検証、CategoryDResolver 1:1 assumption再評価、Hybrid-rate discrepancy解消、Resolver threshold validation、Resolver implementation(いずれもGround Truth未確定のため未着手)
- This Task's Exit Condition: Ground Truthの仕様・採用基準に関する選択肢を提示し、確定が必要な事項をユーザー承認事項として明示すること(具体的な仕様値そのものは本文書内で確定しない)

> 本ドキュメントは[`../e14-e17-roadmap.md`](../e14-e17-roadmap.md) Approval Gate 1
> 「Ground Truth整備方法の決定」に対応する。ロードマップの`Task Sequence`第1段階
> 「Ground Truth設計・構築」の設計フェーズ(構築フェーズより前)を扱う。
>
> **本Task内ではGround Truthそのもの(ラベル付きデータ)を一切作成しない。**
> 具体的な採用基準(サンプルサイズ・選定方法・ラベリングスキーマ等)は、いずれも
> 「選択肢の提示」にとどめ、確定はユーザー承認を経てから行う。

## 1. なぜGround Truthが必要か(既存設計からの要求)

ADR-0048・`docs/design/e14-e17-roadmap.md`で確認済みの事実に基づく。

- **CMassResolver判定ロジック**(ADR-0048 §7)は「Rule E（Task-E5起源）による検出結果を前提に、
  ブロック内の断片行を対応付ける」と定義されているが、判定閾値は未確定。
- **Rule Eの原式**(Task-E15復旧、MEDIUM confidence)は
  `(fragment_pairs_min >= 2 OR block_separation_ratio < threshold) AND self_contained_ratio < 0.7`
  であり、過去に「99-section ground truth」に基づき precision 100% / recall 97.9% と評価された
  (Task-E5起源)。**この99-section ground truthの構築方法(どの99 Sectionをどう選定・ラベル付けしたか)
  自体が、Task-E15の網羅的調査でも復旧不能(UNRECOVERABLE)と確認済み**(`/tmp/taskE15/11_unrecoverable_items.md`)。
- **CategoryDResolver**(ADR-0048 §8)の1:1 action↔data行ペア前提は、Task-E17の実データ検証で
  1action:2data・2action:1dataパターンが存在することが判明しており、この再評価にもGround Truthが必要。
- **Resolver threshold候補**(Task-E17 `resolver_threshold_analysis.md`)は、block-level confidence・
  structural evidence・adjacency等いずれの候補についても「Ground Truth不足で閾値設定不能」と
  明記されている。

したがって、**過去のGround Truth(99-section)は復旧できず、新規に構築する以外の選択肢がない**、
という前提は`e14-e17-roadmap.md`のUnresolved Questions §5(Ground Truthをどう整備するか)と一致する。

## 2. 過去のGround Truthに関する既知情報(参考情報、再利用不可)

以下は「過去にどうだったか」の記録であり、**新Ground Truthの仕様として自動的に踏襲しない**
(踏襲するかどうか自体がGate 1の決定事項)。

| 項目 | 過去の値(Task-E5起源) | 備考 |
|---|---|---|
| サンプル規模 | 99 Sections | 母集団(665〜704 PDFs)からの抽出。抽出方法は未復旧 |
| 評価対象ルール数 | 5ルール比較、Rule Eが最良(F1 0.989) | 他4ルールの詳細は未復旧 |
| ラベリング方法 | 不明(人手と推定されるが記録なし) | UNRECOVERABLE |
| 母集団 | 665〜704 PDFs(現1643 corpusとは別、同一性未証明) | `e14-e17-roadmap.md` §6 D |

## 3. 新Ground Truthが対象とすべき範囲(選択肢)

### 3.1 対象とする分類軸

現行corpus(1643 PDFs)・ADR-0048の設計に基づくと、Ground Truthが検証対象となりうる軸は
以下の3種類がある。いずれを対象に含めるかは未確定。

- **(a) Block classification軸**: 各行が`self_contained`/`post_only_fragment`/`name_only_fragment`/`other`
  のいずれに属するか(ADR-0048 §6)。
- **(b) Section-level Hybrid判定軸**: Sectionが同一Section内に`self_contained`と
  `post_only_fragment`/`name_only_fragment`を混在させる「Hybrid Section」かどうか(ADR-0048 §9)。
  Hybrid Section率78.0%(Task-E17)vs 17.6%(Task-E4)の乖離解消にはこの軸のラベルが必要。
- **(c) Resolver出力軸**: CMassResolver/CategoryDResolverが生成すべき最終的なRawRecord候補
  (どのBlock/行の組がどのRecordへ統合されるべきか)。1:N/N:1パターンの検証にはこの軸が必要。

**選択肢**:
- 案1: (a)のみを先に整備し、(b)(c)は(a)が確定してから段階的に追加する。
- 案2: (a)(b)(c)を同一サンプルセットに対して同時にラベル付けする(1回のラベリング作業で
  3軸すべてを付与)。
- 案3: (b)のみを最優先する(Hybrid-rate discrepancy解消がRoadmap上の直近ボトルネックのため)。

**承認が必要な事項**: どの軸から着手するか、または同時に行うか。

### 3.2 サンプル抽出母集団・方法

- 母集団候補: 現1643 PDF corpus(683 direct + 960 WARP、bijection確認済み)。704/665 corpusは
  同一性未証明のため母集団として使用しない(roadmap既定路線)。
- 232 PDF(layout confidence gap)・11 PDF(CID font crash)は、そもそもSectionが得られないか
  pipeline自体がクラッシュするため、Ground Truthサンプル母集団から自然に除外される
  (Section抽出成功PDFのみが対象になりうる)。
- 121 encrypted PDFのうち、`cryptography`導入下で成功する99件は母集団に含めうるが、
  依存追加が正式化されていない状態でサンプル抽出対象に含めるかは未確定。

**選択肢**:
- 案A: Section抽出成功済み1400 PDFs(cryptography依存PDFを除く)を母集団とする。
- 案B: encrypted PDF(99件)も母集団に含める(ただし依存追加のADR判断が前提条件になる)。

**承認が必要な事項**: 母集団の範囲、および暗号化PDFを含めるかどうか。

### 3.3 サンプルサイズ・抽出方法

過去(Task-E5)は99 Sectionsだったが、抽出基準は復旧不能なため、新たに設計が必要。

**選択肢**:
- 案X: 過去と同規模(概ね100 Sections程度)を無作為抽出する。
- 案Y: 層化抽出(layout_id別・年別・self_contained比率別等で層を作り、各層から一定数抽出する)により、
  母集団の多様性をより代表させる。
- 案Z: 既知5ケース(`2022/0314a.pdf sec17`・`2022/0801a.pdf sec20`・`2023/1222d.pdf sec4`・
  `2017/1201a.pdf sec10`、および出典不明として引き続き除外する`2023/0313a.pdf sec9`)を
  Ground Truthの一部として明示的に含め、残りを無作為または層化抽出で補う。

**承認が必要な事項**: サンプルサイズ、抽出方法(無作為/層化)、既知5ケースの扱い。

**確認**: `2023/0313a.pdf sec9`は、roadmap・ADR-0048いずれでも「出典不明、設計根拠から除外」の
扱いが一貫している。本提案でもGround Truthのpositiveケースとして採用しない(除外を継続)。
これは新しい決定ではなく、既存の承認済み方針の踏襲である。

### 3.4 ラベリングスキーマ

- (a)Block classification軸を対象に含める場合、ADR-0048 §6の4分類
  (`self_contained`/`post_only_fragment`/`name_only_fragment`/`other`)をそのままラベル語彙として
  使うことが、既存設計との整合性の観点で自然な選択肢である。ただし、これは選択肢の1つであり、
  本文書内で確定しない。
- (b)Hybrid判定軸を対象に含める場合、「Hybrid / Non-Hybrid」の二値に加えて、Task-E17 heuristic
  (78.0%)とTask-E4定義(17.6%)のどちらの粒度に合わせるか(またはどちらとも異なる第三の定義を
  新規に立てるか)が未確定。

**選択肢**:
- 案I: ADR-0048の4分類をそのままラベル語彙として採用する。
- 案II: ラベリング作業を通じて、4分類では表現しきれないケースが見つかった場合、
  ラベリング後に語彙自体の見直しを検討する(ADR-0048改訂の要否判断につながる可能性がある)。

**承認が必要な事項**: ラベル語彙の確定方法(先に固定するか、ラベリングをしながら検証するか)。

### 3.5 ラベリング主体・プロセス

- 過去(Task-E5)のラベリング主体(人手か自動か)は未復旧。
- Constitution([`docs/constitution.md`](../../constitution.md))の「4. AI Principles」
  (AIは提案者、人間は承認者、AIはGoldを書き換えない)に照らすと、Ground TruthはGoldに準ずる
  性質のデータであり、**AIが単独でラベルを確定してはならない**可能性が高い。

**選択肢**:
- 案P: 人間(ユーザーまたはレビュー担当者)が最終ラベルを確定し、AIは候補提示・叩き台作成のみを行う。
- 案Q: AIが初期ラベル案を生成し、人間が全件レビュー・修正する(AIの提案+人間の承認、という
  Constitutionの原則に最も忠実な形)。

**承認が必要な事項**: ラベリングの主体・レビュープロセス。これはConstitution §4との整合性に
関わる重要な判断であり、本Task内では確定しない。

### 3.6 保存形式・格納場所

- `docs/design/e14-e17-roadmap.md` §12(保存対象外の事項)は「Ground Truthそのもの」を
  `docs/design/`に保存しないことを既に規定している。
- したがって、Ground Truthの実データ(ラベル付きサンプル)は`docs/design/`配下には置かない。

**選択肢**:
- 案i: `knowledge/`配下(ドメイン知識と同様、人手レビューされる正データベースとして)に置く。
  ただしCLAUDE.mdの禁止事項「`knowledge/`配下のデータを一括置換・自動生成で書き換えない」との
  関係整理が必要(Ground Truthは`knowledge/`が想定する「表記ゆれ・別名」等とは性質が異なる)。
- 案ii: `tests/fixtures/`や`tests/golden/`に近い、テスト専用データとして格納する
  (Resolver実装後の回帰テストとの親和性が高い)。
- 案iii: リポジトリ外(別の管理場所)に置き、リポジトリには参照情報のみを残す。

**承認が必要な事項**: Ground Truthの格納場所。特に案iはCLAUDE.mdの既存禁止事項との関係を
明確にする必要があり、単純にどちらか一方を選べば済む話ではない可能性がある。

## 4. 本文書で決定していない事項(すべて)

上記3.1〜3.6の選択肢は、いずれも本文書内で確定していない。加えて、以下も未決定。

- Ground Truthの実際の構築作業をいつ開始するか。
- Ground Truth構築を単一Taskで行うか、複数Taskに分割するか。
- Ground Truth完成の「完了条件」(何件揃えば十分とするか)。

## 5. ユーザー承認事項(まとめ)

1. **対象分類軸**(3.1): (a)Block classification / (b)Hybrid判定 / (c)Resolver出力のうち、
   どれから着手するか、または同時に行うか。
2. **母集団**(3.2): Section抽出成功1400 PDFsのみか、encrypted PDF(99件)を含めるか。
3. **サンプルサイズ・抽出方法**(3.3): 規模、無作為/層化、既知5ケースの明示的組み込み。
4. **ラベリングスキーマ**(3.4): ADR-0048の4分類をそのまま採用するか、ラベリングをしながら
   語彙自体を検証するか。
5. **ラベリング主体・プロセス**(3.5): AI提案+人間承認の具体的な運用形態。Constitution §4との
   整合性確認を含む。
6. **保存形式・格納場所**(3.6): `knowledge/`・`tests/fixtures/`・リポジトリ外のいずれか
   (またはそれ以外)。

これらが確定した後に、初めてGround Truthの実際の構築(サンプル抽出・ラベリング実施)に着手できる。

## POSITION AFTER TASK

- Current Phase: Ground Truth(設計選択肢の提示段階)
- Completed: Ground Truth設計提案書の作成(本文書、`Status: DRAFT`)
- Newly discovered: 過去の99-section Ground Truthの構築方法はUNRECOVERABLEであることを
  Task-E15が既に確認済みであり(新規発見ではなく既存確認事項の再整理)、新規Ground Truthを
  ゼロから設計する以外の選択肢がないことを改めて確認した。またGround Truthのラベリング主体に
  関する論点(Constitution §4との関係)が、本Taskで新たに明確化された。
- Still blocked: Ground Truthの実際の構築(上記6件のユーザー承認事項が確定するまで未着手)、
  Block classification定義検証、CategoryDResolver再評価、Hybrid-rate解消、Resolver threshold、
  Resolver実装。
- Next approved decision: 上記「ユーザー承認事項」6件のいずれか(または全て)についてのご判断。
