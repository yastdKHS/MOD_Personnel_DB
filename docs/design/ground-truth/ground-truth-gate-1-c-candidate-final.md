# Gate 1-C Candidate Final: 候補Cを初期方式として正式採用

Status: APPROVED（候補Cを初期方式として採用。候補Aへの将来移行は別途承認対象）
Approved-by: USER
Approved-at: 2026-08-20
Approved-in-task: Gate-1-B-i-1-C-formalization

> 本文書は[`ground-truth-gate-1-c-final.md`](ground-truth-gate-1-c-final.md)(Task-E30、
> 候補B除外承認)を上書きしない。同文書が「正式な検討対象として残す」とした
> 候補A/Cのうち、候補Cを初期方式として正式採用する決定を記録する。

## 承認された内容

1. Gate 1-Cは**候補Cを初期方式として正式採用**する。
2. 候補Cの定義: **人間がGround Truthの構造ラベルを作成・確定する**。AIは
   候補生成者・承認者にはせず、該当箇所の抽出・整形・参照情報の提示等の
   **補助**に限定する。
3. 候補B(ルールベース自動確定)は**引き続き不採用**(既承認、変更なし)。
4. **将来的に候補A(AI提案+人間承認)へ移行する可能性は残す。** 移行する場合は、
   その時点で別途承認を取得し、AI提案によるanchoring等のリスクと人間承認の
   実質性を設計・検証する。
5. 今回、候補Aへの移行条件・詳細な運用仕様は確定しない。

## 既承認事項との関係

[`ground-truth-gate-1-c-final.md`](ground-truth-gate-1-c-final.md)(Task-E30)が
「候補A/Cを正式な検討対象として残す」「候補Bは不採用」と承認した内容は
**変更しない**。本文書は、その枠内で候補Cを初期方式として選択したことを
追加確定するものである。

## 参考: 候補A/候補Cの性質の違い(既存分析の再掲、変更なし)

[`ground-truth-gate-1-b-i-and-1-c-decision-comparison.md`](ground-truth-gate-1-b-i-and-1-c-decision-comparison.md)
B章で整理済みのとおり、候補Cは:
- Constitution §4「承認という行為を省略・形骸化させる変更は...採用しない」
  という原則に最も忠実な構成である。
- 候補A→候補Cへの移行は高コストである一方、候補C→候補Aへの移行は
  低コストという非対称性が観察されている(既存の論理的推論であり、
  実データでの検証を経たものではない)。**本文書はこの非対称性を
  判断材料の一つとして踏まえた上での採用決定であるが、この観察自体を
  新たな確定事実として扱うものではない。**

## 未承認のまま残る事項

| 項目 | 状態 |
|---|---|
| 候補Aへの移行条件・トリガー | **未確定**(別途承認) |
| 承認単位(PDF/Section/Block/Label、Gate種別ごとに使い分けるか) | **未確定** |
| 8ステップ(Candidate generation/Human review/Approval/Versioning/Audit
  trail/Rejection・correction/Re-review/Gold promotion)の候補C版としての
  具体的な設計 | **未確定** |
| Constitution §4の「Gold Database」「Knowledge Base」がGround Truthに
  どこまで厳密に適用されるかの解釈 | **未確定** |

## 引き続き実装しないことの確認

本文書は人間承認プロセスの**初期方式の選択(候補C採用)**を承認したものであり、
実際のラベリング・承認プロセスの実装・運用開始を承認するものではない。
