# Gate 1-A Final: Ground Truth Content Scope(承認済み)

Status: APPROVED
Approved-by: USER
Approved-at: 2026-08-19
Approved-in-task: E30

> 本文書はTask-E29の[`ground-truth-content-scope-analysis.md`](ground-truth-content-scope-analysis.md)
> を上書きしない。Task-E30で作成した正式化レビュー(`/tmp/taskE30/gate_1_a_final.md`)の内容を、
> ユーザー承認を反映した形でリポジトリへ格納したものである。

## 承認された内容

1. **Block classification・Hybrid判定・Resolver threshold validation**については、
   Ground Truthの内容スコープを**(i)位置参照+(ii)構造的判定ラベル**とする。
   (iii)抽出値そのものは、原則としてGround Truthの必須要件としない。
2. **CategoryD 1:N/N:1**については、(iii)の必要性を**D. 未確認のまま維持**する。
   勝手に「不要(C)」とは確定しない。新たな実証調査を行う場合は、別Taskとして設計し、
   実データの扱いを事前に明示する(この点は承認事項6「CategoryD」としても別途確認済み)。

## 区分表(承認済み)

| 検証対象 | 区分 | 状態 |
|---|---|---|
| Block classification | C. 不要 | **APPROVED** |
| Hybrid判定(Section-level) | C. 不要 | **APPROVED** |
| CategoryD 1:N/N:1パターン | D. 未確認 | **APPROVED**(「未確認のまま維持する」という決定自体が承認事項) |
| Resolver threshold validation | C. 不要 | **APPROVED** |

## 根拠(Task-E29/E30時点の整理、変更なし)

- Block classification: BlockKind判定は構造的特徴の有無の判定であり、氏名・階級の
  具体的な文字列内容に依存しない。
- Hybrid判定: Section内のBlock構成比率という集計情報であり、個々の行の実値と無関係。
- CategoryD 1:N/N:1: 「(旧職)＋新rank＋新name」等のパターンの対応関係判定に、
  部分的に実値相当の情報が必要になる可能性を排除できず、実際のラベリング試行を経ずに
  確定する根拠がない。**具体的な証拠(実値確認が必要という証拠)は現時点で存在しない。**
- Resolver threshold validation: 正解ラベルと予測ラベルの比較のみで成立し、実値に依存しない。

## 未承認のまま残る事項

- CategoryD 1:N/N:1のD区分を将来どう解消するか(承認事項6により、別Taskとして設計し、
  実データの扱いを事前に明示することが条件として付されている)。

## 引き続きGround Truth実データを作成しないことの確認

本文書はGate 1-Aの**内容スコープに関する設計方針**を承認したものであり、
Ground Truth実データそのものの作成・収集・コピーを承認するものではない。
