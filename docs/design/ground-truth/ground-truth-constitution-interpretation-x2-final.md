# Constitution Ground Truth Interpretation Final: X-2(原記録中心解釈)採用

Status: APPROVED（Constitution解釈のみ。Gate 1-B-ii〜v・Gate 1-Cの承認ではない）
Approved-by: USER
Approved-at: 2026-08-28
Approved-in-task: Constitution-X2-Interpretation

> 本文書は[`ground-truth-constitution-ground-truth-interpretation-decision.md`](ground-truth-constitution-ground-truth-interpretation-decision.md)
> (Status: DRAFT、X-1/X-2/X-3の比較分析および非拘束の提案)を上書きしない。同文書が
> 提示した3候補のうち、ユーザーがX-2を正式に採用したことを記録する。同文書は
> 分析・比較の履歴として、内容を変更せずそのまま保持する。

## Decision ID

`Constitution-X2-Interpretation`

## Decision

**X-2（原記録中心解釈）を採用する。**

Constitution §3「Gold Database is Truth」に記載された不変性原則(「過去の記録は
基本的に不変であり、修正は新しい版を積み重ねる形で行う」)は、まずGold Databaseに
保存される原記録を中心として適用する。

この原則を、Ground Truthに関連するすべての派生物・設計文書・manifest・外部
ストレージ・Resolver・技術実装等へ自動的に拡張しない。これらについて不変性・
versioning・audit trail等を要求する場合には、それぞれ別途の設計Decisionを必要とする。

このDecisionはConstitution本文そのものを変更するものではなく、既存Constitutionの
適用範囲についての解釈を正式化するものである。

## Rationale

- Constitution本文との直接整合性: 不変性原則の文言(「過去の記録は基本的に不変」)は
  §3「Gold Database is Truth」節の内部にあり、文法上Gold Database内の記録を
  対象とする。X-2はこの本文の実際の適用範囲に忠実であり、Ground Truth全体への
  無条件な拡張を行わない。
- 不要な拡張解釈を避けられる: Ground TruthはConstitutionが明示的に定義する
  「Gold Database」に字義上該当しない(既存分析、`ground-truth-decision-readiness.md`
  §4.2以来複数Taskで確認済み)。X-2はこの非該当性と整合する。
- Gold Databaseの役割との整合: Gold Database本体への適用はそのまま維持し、
  Ground Truthへの適用は精神の類推(承認を経た記録への段階的な適用)にとどめる。
- 既存precedentとの整合: `docs/database/schema.md`の`candidate_records`
  (INSERT中心、`validation_status`のみ限定的にUPDATE許容)と`gold_records`
  (SCD Type 2、`superseded_by`自己参照、物理削除・上書きなし)という、承認前後で
  可変性の扱いを変える既存の段階的設計パターンと構造的に一致する([Inference]、
  precedentの存在自体はConstitutionが義務付けているものではなく、実装上の
  参考情報である)。
- Gate 1-B-ivの技術設計自由度を不必要に拘束しない: X-1(強い不変性)のように
  Ground Truth全体をGold Database相当として扱う解釈と比較し、将来のVersioning
  方式(案IV-1/IV-2/IV-3)の選択余地を過度に狭めない。

## 適用範囲

- **原記録**: X-2の中心的適用対象。Gold Database内の確定記録(`gold_records`
  相当)、およびConstitutionが「Truth」として位置づける原記録。
- Gate 1-Cの「承認」を経たGround Truth記録について、Gold Database is Truthの
  精神(承認後の軽々しい書き換えを避ける)を**類推適用する余地を残す**(自動的な
  適用ではなく、将来のGate 1-B-iv/Gate 1-C個別Decisionにおける検討材料)。

## 非適用範囲

- **派生物**: manifest、Resolverによる派生結果、index、cache、export、view等。
  X-2によって自動的にimmutableとはしない。
- **設計文書**: `docs/design/`配下の設計文書。X-2によって自動的に不変とはしない
  (既存運用上の「`-final.md`は一度APPROVEDになったら編集しない」という慣行は、
  本Decisionとは別の運用ルールであり、Constitution由来の要求ではない)。
- **技術実装**: immutable object storage、append-only DB、audit log、
  version ID方式、retention、backup/recovery等の具体的実装方式。X-2はこれらを
  一切確定しない。Gate 1-B-ii〜v等の別Decision対象とする。

## Precedentとの関係

[Fact] `gold_records`はSCD Type 2的設計(新版`INSERT`、旧版`is_current=0`・
`superseded_by`へ`UPDATE`、物理削除・上書きなし、永久保持)。

[Fact] `candidate_records`は`INSERT`のみを原則とし、`validation_status`
フィールドのみ限定的に`UPDATE`を許容する。

[Inference] 両テーブルは、Constitution §3の不変性原則を実装レベルで具体化した
precedentと考えられるが、**Constitution自体がこの実装方式を名指しで要求している
わけではない**。「precedentが存在すること」と「Constitutionがその仕様を義務付けて
いること」は区別する。X-2はこのprecedentとの構造的整合性を採用理由の一つとするが、
precedentをそのままGround Truthへ適用することを義務付けるものではない。

## Gate 1-B-ii〜vへの影響

**X-2採用 ≠ Gate 1-B-iv承認。** X-2はConstitution解釈の一つの前提条件を解消するに
すぎず、Gate 1-B-iv自体は以下がいずれも未決定のまま、**引き続き未承認**である。

- immutable / mutable / hybrid(案IV-1/IV-2/IV-3)の選択
- version ID方式
- audit trail方式
- revision workflow
- retention

Gate 1-B-iiについても、backup frequency・generation count・verification cycle・
recovery policy等はいずれも未決定のまま、**引き続き未承認**である。

Gate 1-B-iiiについても、manifest schemaの具体的構造(案III-1/III-2/III-3)・
approval statusフィールドの意味論(Gate 1-Cの8ステップに依存)は未決定のまま、
**引き続き未承認**である。structural label等の部分先行確定の可能性は既存分析
(前々Task)で示されているが、本Decisionはこれを正式に確定させるものではない。

Gate 1-B-vについても、runbookの要否・構成・内容はii〜ivの確定を待つ下流事項として
未決定のまま、**引き続き未承認**である。

## Gate 1-Cへの影響

X-2はGate 1-Cの8ステップ設計を変更しない。以下を維持する。

- Gate 1-C候補C初期採用(既承認、変更なし)
- 候補B不採用(既承認、変更なし)
- 8ステップ具体設計は引き続き未確定
- Gate 1-Cの再承認・再定義は行っていない

X-2はGate 1-Cに対する入力条件の一つとしてのみ扱う。

## Citation Correction(記録のみ、修正はしない)

[Fact] 前Task群で確認済みの引用箇所の状況を記録として維持する。

- DRAFT文書5件(`ground-truth-gate-1-b-ii-to-v-detailed-analysis.md`・
  `ground-truth-external-storage-design.md`・
  `ground-truth-gate-1-b-secondary-design-options.md`・
  `ground-truth-gate-1-b-approval-sequence-analysis.md`・
  `ground-truth-decision-readiness.md`)は、不変性原則本体を「Constitution §4」と
  引用しているが、実際には§3に存在する。**確定した誤引用**。本Decisionでは
  修正しない。
- main掲載済みAPPROVED文書2件(`ground-truth-gate-1-c-candidate-final.md`・
  `ground-truth-gate-1-c-final.md`)の「Constitution §4の『Gold Database』
  『Knowledge Base』」という引用は、両語とも§4にも実在するため、**不正確だが
  誤りとまでは言えない**。本Decisionでは修正しない。
- これらの修正要否は将来の別Taskの検討事項として残す。

## Non-Decisions

本Decisionでは以下を決定していない。

- Backup/Recovery方式(Gate 1-B-ii)
- manifest schema(Gate 1-B-iii)
- Versioning方式(Gate 1-B-iv、immutable/mutable/hybridの選択)
- audit trail方式
- external storage technology(Gate 1-B-i技術選定、引き続き先送り)
- Resolver behavior
- runbook(Gate 1-B-v)
- Gate 1-C 8-step workflowの具体的設計
- Ground Truth実データの構造・作成
- Category D(CategoryD 1:N/N:1)の解消方法

## 既承認事項との関係(変更なし)

- Gate 1-A(内容スコープ): 変更なし。
- Gate 1-B(方式2の方向性): 変更なし。
- Gate 1-B-i(独立ガバナンス+技術選定先送り): 変更なし。
- Gate 1-C(候補C初期採用、候補B不採用): 変更なし。
- Gate dependency(1-B/1-C並行検討可能): 変更なし。
