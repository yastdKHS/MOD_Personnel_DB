# E14/E17 Roadmap — Resolver実装前の設計確定フェーズ

Status: DRAFT（Gate 1は部分的に承認済み、Task-E30。Gate 2〜6は引き続き未承認）
Approval: PENDING

> 本ドキュメントは、Task-E14(1643-PDF実データ検証)・Task-E17(ADR-0048正式化＋Resolver実データ検証)で
> 判明した未解決事項を、場当たり的に処理せず、今後のTaskが常に「設計方針上の現在位置」を参照できるように
> するための正式なロードマップである。作成: Task-E28。
>
> 本ドキュメントはADR-0048([`../adr/0048-block-classification-cmass-category-d-resolver-architecture.md`](../adr/0048-block-classification-cmass-category-d-resolver-architecture.md))
> を上書き・変更するものではない。ADR-0048はアーキテクチャの決定事項(Accepted)として維持し、
> 本ドキュメントはADR-0048に含まれない実データ検証・未解決事項の管理台帳として位置づける。

## 1. 現在位置(サマリ)

```
E14 corpus recovery
    ↓ 完了
E14 real-data validation
    ↓ 部分完了
E17 design recovery
    ↓ 完了
ADR-0048 formalization
    ↓ 完了・main merge済み(PR #88, commit 0af5947)
【現在地】
Resolver実装前の「Ground Truth / classification definition / CategoryD 1:1 assumption /
Hybrid-rate definition」の設計確定フェーズ
    ↓
今後
    1. Ground Truth設計・構築
       1-A. Content Scope(内容スコープ)
            [APPROVED, Task-E30] Block/Hybrid/Threshold検証は(i)位置参照+(ii)構造的判定
            ラベルを基本とし、(iii)抽出値は原則不要。CategoryD 1:N/N:1の(iii)必要性は
            D.未確認のまま維持(勝手に不要と確定しない)。
       1-B. Storage(格納方式)
            [APPROVED(方向性+外部保存先のガバナンス上の位置づけ), Task-E30/
            Gate-1-B-i-1-C-formalization] 実データはGit外で管理し、Gitには
            manifest・構造的判定情報を管理する方式2の方向性を承認(Task-E30)。
            外部保存先は既存PDF Registry(ADR-0018)とはガバナンス上独立した
            位置づけとし、具体的な技術選定は実装時まで先送りする
            (Gate-1-B-i-1-C-formalization)。永続性・バックアップ・アクセス管理・
            再現性・技術選定そのものは別Taskで検討(未確定)。
       1-C. Human Approval Process(人間承認プロセス、1-Bと並行検討可能)
            [APPROVED(候補B除外+候補C初期採用), Task-E30/
            Gate-1-B-i-1-C-formalization] ルールベース自動確定(候補B)は
            不採用(Task-E30)。候補C(人間がラベルを直接作成、AIは抽出・整形等の
            補助のみ)を初期方式として正式採用(Gate-1-B-i-1-C-formalization)。
            候補A(AI提案+人間承認)への将来移行は可能性として残すが、移行時は
            別途承認・設計が必要(未確定)。
       ※ Ground Truth実データ構築自体は、1-Bの副次的設計(永続性等)・技術選定・
         1-Cの候補A移行条件等が確定するまで着手しない(いずれも未承認)。
         詳細: `docs/design/ground-truth/ground-truth-gate-1-approval-record.md`
    2. Block classification定義検証
    3. CategoryDResolver 1:1 assumption再評価
    4. Hybrid 78.0% vs 17.6% discrepancy解消
    5. Resolver threshold validation
    6. Resolver implementation
    7. real-data validation
    8. integration
    9. regression verification
```

この順序を現時点の基本ロードマップとする。ただし、上記順序を実行中に得られた新証拠によって
変更が必要になった場合は、「現在位置」「変更理由」「影響範囲」を明示してから承認を求める
(勝手に順序を変更しない)。

**Gate 1(Ground Truth設計・構築)の内部構造(1-A/1-B/1-C)は、Task-E29で識別され、
Task-E30で部分的に承認された。Gate 1-B-i(外部保存先選定方針)・Gate 1-C(候補C
初期採用)は、Task`Gate-1-B-i-1-C-formalization`(2026-08-20)で追加承認された。**
Gate 1-B-ii/iii/iv/v、および候補Aへの移行、Gate 2〜6は本節時点では未承認のまま。

## 2. Confirmed Facts(実測・再現確認済み)

出典の詳細は`e14_e17_fact_reconciliation.md`(Task-E28成果物、`/tmp/taskE28/`)を参照。

### E14由来

| 項目 | 値 | 出典 |
|---|---|---|
| Corpus件数 | 1643 PDFs | Task-E14 `01_baseline.md`、Task-E17 `corpus_verification.md`(再測定一致) |
| URL-PDF対応 | 683 direct URLs + 960 WARP URLs = 1643(完全対応、bijection) | Task-E14R8-RESTART(本ロードマップ以前のTask)、Task-E15 `10_704_vs_1643_context.md` |
| Section到達 | 1400/1643 PDFs(85.2%) | Task-E14 `12_taskE14_summary.md` |
| Raw Record数 | 25,302件 | 同上 |
| CID font encoding crash | 11 PDFs(すべて2018年)、`LookupError: unknown encoding: /90msp-RKSJ-H` | 同上 |
| Layout confidence不足による0-Section | 232 PDFs(14.1%)、全期間に分散 | 同上 |
| Encrypted PDF | 121 PDFs、`cryptography`導入で99件がSectionまで到達 | Task-E14 `10_encrypted_pdf_analysis.csv` |

### E17由来

| 項目 | 内容 | 出典 |
|---|---|---|
| ADR-0048 | 正式化・main merge済み(PR #88、merge commit `0af5947`) | Task-E22 |
| Integration Option A | Block classification foundation + CMassResolver + CategoryDResolver(分離) | ADR-0048 §4 |
| `FieldExtractionResult.blocks` | 現行コードに不存在 | ADR-0048 §20、Task-E17 |
| Hybrid Section率(Task-E17 heuristic定義) | 78.0% | Task-E17 `block_classification_real_data.md` |
| CategoryDResolverの1:1前提の限界 | `2022/0801a.pdf sec20`(1action:2data等)、`2023/1222d.pdf sec4`(2action:1data等)で実データ上のパターンを確認 | Task-E17 `representative_case_verification.md` |
| Resolver threshold | 現時点で設定不能(Ground Truth・隣接関係解析ロジックいずれも未整備) | Task-E17 `resolver_threshold_analysis.md` |

## 3. Recovered Design(過去セッションから復旧された設計、HIGH/MEDIUM confidence)

- Block classification: `self_contained` / `post_only_fragment` / `name_only_fragment` / `other`
  (Task-E12/E13由来、HIGH confidence — verbatim復旧)。
- CMassResolver / CategoryDResolver の責務分離(Integration Option A)。
- Rule E(Task-E5〜E7由来設計、MEDIUM confidence — 圧縮summary経由。99-section ground truthの
  構築方法自体は未復旧)。

いずれもADR-0048 §19「証拠強度・出典分類」の分類を正とする。本ドキュメントはこの分類を変更しない。

## 4. Hypotheses(未確定・仮説)

- Hybrid Section率78.0%(Task-E17 heuristic)と17.6%(Task-E4既存値)の乖離原因 — 定義の粒度差か
  サンプリング差か、いずれかまたは両方の可能性があるが未特定。**このTaskでは新しい事実として確定しない。**
- 39.2% overlap — Task-E17時点で`NOT_MEASURABLE`(candidate生成ロジック未実装のため)。**過去値として
  参照するのみで、確定値として扱わない。**
- 232 PDF(14.1%)のlayout confidence gapが全期間に分散して発生している原因 — 未調査の仮説。

## 5. Unresolved Questions

1. Ground Truthをどう整備するか(Task-E5の99-section ground truthは復旧不能。新規構築が必要)。
2. CategoryDResolverの「隣接する1:1 action↔data行ペア」という前提を、1action:2data・2action:1data
   パターンに対応させるにはどう再設計するか。
3. Hybrid Section率の定義差(78.0% vs 17.6%)をどう解消するか。
4. Resolver threshold(判定閾値)をどのデータ・手法で決定するか。
5. 704 vs 1643corpusの同一性(未証明のまま。旧母集団定義ファイル`/tmp/taskH/pdf_level_summary.csv`は
   消失済みで復旧不能。追加のユーザー提供情報がない限り、これ以上の調査は非現実的)。
6. 232 PDF layout confidence gap、11 PDF CID font crash、121 encrypted PDFの`cryptography`依存化 —
   いずれもE14 upstream issue(下記6章参照)として、Resolver設計とは別枠で扱う。

## 6. E14 Upstream Issues(Resolver問題と混同しない)

Resolver設計(下記7章)とは独立した、pipeline上流(LayoutDetector/DocumentAnalyzer)の課題。

| 区分 | 内容 | 件数/比率 | 分類 |
|---|---|---|---|
| A | LayoutDetector confidence gap | 232 PDFs / 14.1% | upstream pipeline issue |
| B | CID font encoding crash(`/90msp-RKSJ-H`) | 11 PDFs / 2018年 | upstream parser/layout issue |
| C | Encrypted PDF | 121 PDFs(大部分は`cryptography`導入で処理可能) | dependency化は別途ADR判断が必要 |
| D | 704 vs 1643 discrepancy | — | 704の母集団定義ファイル消失、現1643corpusとの関係は未証明。推測で同一視しない |

これらはADR-0048 §18「スコープ外の課題」の記載と整合しており、本ロードマップでも同様に
「別管理」の扱いを維持する。

## 7. E17 Resolver-Pre-Design Issues(Resolver実装前に確定すべき事項)

Resolverを実装してから問題を発見するのではなく、**実装前に実データ上のclassification semanticsを
確定する**ことを原則とする(Task-E28指示より)。

1. Block classification(operational definitionの検証)
2. Ground Truth(整備方法の決定・構築)
3. CMassResolver(責務・candidate生成ロジック)
4. CategoryDResolver(責務・candidate生成ロジック)
5. 1:1 assumption(CategoryDResolverの前提の妥当性)
6. 1:N / N:1 patterns(実データ上の変則パターンへの対応方針)
7. 39.2% overlap(再測定・再定義の要否)
8. Hybrid Section definition(78.0% vs 17.6%の解消)
9. Resolver threshold(決定手法・根拠データ)

## 8. Approval Gates(承認ゲート)

以下の判断は、ユーザー承認を経ずに次段階へ進まない。

| ゲート | 内容 | 状態 |
|---|---|---|
| Gate 1 | Ground Truth整備方法(新規人手ラベル付け / 別手法)の決定 | **部分的に承認済み**
  (Task-E30、Gate-1-B-i-1-C-formalization)。内訳: 1-A(内容スコープ)承認済み、
  1-B(格納方式)方向性+外部保存先のガバナンス上の独立性・技術選定先送りは承認済み・
  Gate 1-B-ii/iii/iv/vの副次的設計・具体的な技術選定は未承認、1-C(人間承認プロセス)
  候補B除外+候補C初期採用は承認済み・候補Aへの移行は未承認。
  詳細は`docs/design/ground-truth/ground-truth-gate-1-approval-record.md` |
| Gate 2 | Block classification operational definitionの確定方法 | 未承認 |
| Gate 3 | CategoryDResolver 1:1 assumptionの再設計方針 | 未承認 |
| Gate 4 | Hybrid Section率78.0% vs 17.6%のどちらを設計基準とするか(または両論併記のまま保留するか) | 未承認 |
| Gate 5 | Resolver threshold決定手法 | 未承認 |
| Gate 6 | E14 upstream issues(232 PDF/11 PDF/121 PDF/704 vs 1643)への対応要否・優先順位 | 未承認 |

## 9. Task Sequence(基本ロードマップ)

1. Ground Truth設計・構築
2. Block classification定義検証
3. CategoryDResolver 1:1 assumption再評価
4. Hybrid 78.0% vs 17.6% discrepancy解消
5. Resolver threshold validation
6. Resolver implementation
7. real-data validation
8. integration
9. regression verification

この順序は、Ground Truthなしに閾値設計・実装に進むことを防ぐために設計されている
(Task-E17の`resolver_threshold_analysis.md`が明示した制約)。順序の変更が必要になった場合は
本ドキュメントの改訂(かつユーザー承認)を経る。

## 10. ADR-0048との関係

ADR-0048は既にmainへmerge済みであり、現行アーキテクチャの設計基盤として扱う。本ドキュメントは
ADR-0048を変更しない。ただし、ADR-0048に含まれない以下の事項は、本ドキュメントおよび将来の
`docs/design/`配下の個別ドキュメント(下記11章)で管理する。

- Ground Truth specification
- Block classification operational definition
- CategoryD 1:N/N:1 handling
- Hybrid Section definition
- 78.0% vs 17.6% discrepancy
- Resolver threshold determination

これらが十分に確定した段階で、ADR-0048の更新(Supersededまたは追記)が必要かを別途判断する。
ADRを変更する場合は、変更理由と既存設計への影響を明示した上で、通常のADR起票プロセス
([`docs/adr/README.md`](../adr/README.md))に従う。

## 11. 関連ドキュメント・今後の個別ドキュメント配置

- [`docs/adr/0048-block-classification-cmass-category-d-resolver-architecture.md`](../adr/0048-block-classification-cmass-category-d-resolver-architecture.md) — アーキテクチャ決定(Accepted)
- [`docs/roadmap.md`](../roadmap.md) — 実装変更を伴わない将来の設計改善候補一覧(本ドキュメントとは別軸。`docs/roadmap.md`はADR起票済み事項の再評価候補、本ドキュメントはADR-0048配下の未確定事項の管理)
- `docs/design/ground-truth/` — Ground Truth整備の設計・進捗。Gate 1-A/1-B/1-C比較
  (Task-E29)・承認記録(Task-E30、[`ground-truth-gate-1-approval-record.md`](ground-truth/ground-truth-gate-1-approval-record.md))・
  Gate 1-B-i外部保存先承認([`ground-truth-gate-1-b-i-final.md`](ground-truth/ground-truth-gate-1-b-i-final.md))・
  Gate 1-C候補C初期採用承認([`ground-truth-gate-1-c-candidate-final.md`](ground-truth/ground-truth-gate-1-c-candidate-final.md))
  (いずれもGate-1-B-i-1-C-formalization)を格納済み
- `docs/design/block-classification/` — Block classification operational definitionの検証記録(Gate 2確定後に作成)
- `docs/design/category-d/` — CategoryDResolver 1:1 assumption再評価の記録(Gate 3確定後に作成)
- `docs/design/hybrid-section/` — Hybrid Section定義乖離解消の記録(Gate 4確定後に作成)
- `docs/design/resolver/` — Resolver threshold validation・実装設計の記録(Gate 5以降に作成)

上記サブディレクトリは、対応するGateが承認された段階で作成する。本Task(E28)時点では
空ディレクトリの先行作成は行わない(内容のない空ディレクトリをgitへコミットする実益がないため)。

## 12. 保存対象外の事項(本ドキュメントに含めないもの)

- 未承認の実装コード
- 仮説を確定仕様として扱う記述
- Ground Truthそのもの(データ)
- 一時的な大量生成データ
- 1643 PDFのコピー

---

Status: DRAFT（Gate 1は部分的に承認済み、Task-E30。Gate 2〜6は引き続き未承認）
Approval: PENDING
