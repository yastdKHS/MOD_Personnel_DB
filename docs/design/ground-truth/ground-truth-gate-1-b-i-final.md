# Gate 1-B-i Final: 外部保存先選定方針(独立ガバナンス+技術選定先送りを承認)

Status: APPROVED（保存先のガバナンス上の位置づけのみ。具体的な技術選定は引き続き先送り）
Approved-by: USER
Approved-at: 2026-08-20
Approved-in-task: Gate-1-B-i-1-C-formalization

> 本文書は[`ground-truth-gate-1-b-final.md`](ground-truth-gate-1-b-final.md)(Task-E30、
> 方式2の方向性承認)を上書きしない。同文書が承認した「実データはGit外で管理し、
> Gitにはmanifestおよび構造的判定情報を管理する」という方式2の枠内で、Gate 1-B-i
> (外部保存先選定方針)について新たに承認された内容を記録する。

## 承認された内容

1. Ground Truthの保存先は、既存PDF Registry(ADR-0018)とは**ガバナンス上独立した
   位置づけ**とする。
2. 実PDF・実データ・個人情報等は引き続きGit外で管理する
   (既承認の方式2を変更しない、再確認)。
3. Gitには、manifest・位置参照・構造的判定ラベル等、承認された範囲の非機微な
   メタデータのみを管理する(既承認の方式2の範囲、再確認)。
4. 具体的な外部ストレージ技術・製品の選定は、現時点では行わず、実装時まで先送りする。
5. これは新しい「第4の保存方式」の追加ではない。[`ground-truth-gate-1-b-secondary-design-options.md`](ground-truth-gate-1-b-secondary-design-options.md)が
   提示した選択肢のうち、**「保存先のガバナンス上の位置づけ」(案I-2相当の独立性)と
   「具体的な技術選定」(案I-3相当の先送り)を分離した二段階の意思決定**として
   正式化するものである。**I-1/I-2/I-3という既存の選択肢定義自体は変更・
   再定義しない。**

## 用語の明確化

- 「I-2相当」とは、[`ground-truth-gate-1-b-secondary-design-options.md`](ground-truth-gate-1-b-secondary-design-options.md)
  の案I-2(独立ストレージ)が持つ「PDF Registryとは目的の異なるデータを明確に
  分離する」という**ガバナンス上の性質**を指す。
- 「I-3相当」とは、同文書の案I-3(技術選定の先送り)が持つ「契約(内容アドレス
  方式・SHA-256等)のみを固定し、具体的な製品・サービスの選定は実装時に行う」
  という**時間軸上の性質**を指す。
- 今回の承認は、この2つの性質を組み合わせたものであり、新たな第4の案を
  定義するものではない。

## 既承認事項との関係

- [`ground-truth-gate-1-b-final.md`](ground-truth-gate-1-b-final.md)(Task-E30)が
  承認した「方式2(実データGit外+Gitにはmanifest/構造ラベル)」は**変更しない**。
  本文書は、この方式2の枠内で、外部保存先のガバナンス上の位置づけのみを
  追加確定するものである。

## 副次的に解消される論点(新しい決定ではなく、既存論点の位置づけ変更)

[`ground-truth-gate-1-b-i-and-1-c-decision-comparison.md`](ground-truth-gate-1-b-i-and-1-c-decision-comparison.md)
A-9節が指摘した「ADR-0018の適用範囲をGround Truthへ拡張することが適切か」
という未確定事項は、**独立ガバナンス(PDF Registryとは別)を採用したことにより、
ADR-0018の適用範囲拡張という論点自体が生じない**方向になったと考えられる。
ただし、これは本文書が新たに検証した事実ではなく、独立ガバナンスという
決定から論理的に導かれる帰結の記録にとどまる。

## 未承認のまま残る事項

| 項目 | 状態 |
|---|---|
| 具体的な外部ストレージ技術・製品の選定 | **未確定**(実装時に選定) |
| Gate 1-B-ii(Backup/Recovery/Integrityパラメータ) | **未確定**(別Task) |
| Gate 1-B-iii(manifest schema詳細) | **未確定**(別Task) |
| Gate 1-B-iv(Versioning方針) | **未確定**(別Task) |
| Gate 1-B-v(runbook要否) | **未確定**(別Task) |

## 引き続きGround Truth実データを作成しないことの確認

本文書はGate 1-Bの**外部保存先選定方針**を承認したものであり、Ground Truth
実データの作成・実際のストレージ構築・具体的な技術選定を承認するものではない。
