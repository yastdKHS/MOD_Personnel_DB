# Gate 1 Approval Record(Task-E30承認の記録)

Status: APPROVED（個別項目の承認状態は本文参照）
Approved-by: USER
Approved-at: 2026-08-19
Approved-in-task: E30

> Gate 1-A/1-B/1-C/依存関係それぞれの承認詳細は、以下の各文書を参照。本文書は
> 承認内容の一覧・索引として機能する。
>
> **更新履歴**: 冒頭のStatus/Approved-at/Approved-in-taskはTask-E30時点の
> 初版作成を示す。1-B・1-C行は、Task`Gate-1-B-i-1-C-formalization`
> (2026-08-20)でGate 1-B-i(外部保存先選定方針)・Gate 1-C候補C初期採用の
> 正式承認を反映して更新した。1-A・Gate dependency・Roadmap反映の各行は
> 初版から変更していない。

## 承認一覧

| Gate | 承認された内容 | 未承認のまま残る事項 | 詳細 |
|---|---|---|---|
| 1-A Content Scope | Block/Hybrid/Threshold検証は(i)+(ii)基本、(iii)原則不要。
  CategoryD 1:N/N:1は(iii)必要性をD.未確認のまま維持 | CategoryDのD区分の解消方法
  (別Task) | [`ground-truth-gate-1-a-final.md`](ground-truth-gate-1-a-final.md) |
| 1-B Storage | 方式2(実データGit外+manifest)の**方向性**、および外部保存先の
  **ガバナンス上の独立性**(PDF Registryとは別、I-2相当)+**技術選定の先送り**
  (I-3相当) | 具体的な技術選定、永続性・バックアップ・アクセス管理・再現性等の
  具体的設計(別Task) | [`ground-truth-gate-1-b-final.md`](ground-truth-gate-1-b-final.md)、
  [`ground-truth-gate-1-b-i-final.md`](ground-truth-gate-1-b-i-final.md) |
| 1-C Human Approval | 候補B(ルールベース自動確定)の**不採用**、および
  **候補C(人間が直接作成、AIは補助のみ)を初期方式として正式採用** | 候補Aへの
  移行条件、承認単位、8ステップの具体的設計(別途承認) | [`ground-truth-gate-1-c-final.md`](ground-truth-gate-1-c-final.md)、
  [`ground-truth-gate-1-c-candidate-final.md`](ground-truth-gate-1-c-candidate-final.md) |
| Gate dependency | Gate 1-BとGate 1-Cの並行検討可能な依存構造 | なし(この点自体は
  完全に承認済み) | [`ground-truth-gate-dependency-final.md`](ground-truth-gate-dependency-final.md) |
| Roadmap反映 | 上記承認内容の`docs/design/e14-e17-roadmap.md`への反映 | roadmap本体の
  Status自体は引き続きDRAFT(Gate 2〜6は未承認のため) | `docs/design/e14-e17-roadmap.md`変更履歴参照 |

## 明示的に承認されなかった事項(念のための確認)

Task-E30承認の依頼文で、以下は明示的に「まだ承認しない」とされている。

- Ground Truth実データの作成
- Resolver実装
- src/tests変更
- DB/Knowledge/PDF corpus変更
- ADR-0048変更

これらはいずれも、本文書を含むGate 1関連文書のいずれによっても承認されていない。
