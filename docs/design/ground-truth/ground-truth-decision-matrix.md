# Ground Truth Decision Matrix(3 Gate結論候補の統合)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: 3 Gateの結論候補統合(承認判断の一覧化)
- Completed: Gate 1-A/1-B/1-C/Gate依存関係の個別文書化
- In Progress: 結論候補の統合一覧作成
- Blocked: Ground Truth実データ作成、以降のすべての後続作業
- This Task's Exit Condition: 3 Gateの結論候補を1つの表に整理し、ユーザーが一覧で
  承認判断できる形にすること

> 本文書は[`ground-truth-content-scope-analysis.md`](ground-truth-content-scope-analysis.md)・
> [`ground-truth-storage-decision.md`](ground-truth-storage-decision.md)・
> [`ground-truth-human-approval-process.md`](ground-truth-human-approval-process.md)・
> [`ground-truth-gate-dependency.md`](ground-truth-gate-dependency.md)の結論候補を
> 一覧化したものであり、新しい分析を追加するものではない。詳細な根拠は各文書を参照。

## 統合一覧

| Gate | 論点 | 結論候補(未確定) | Status |
|---|---|---|---|
| 1-A | 内容スコープ | (i)位置参照+(ii)構造的判定ラベルを基本とし、(iii)抽出値そのものは
  原則不要。ただしCategoryD 1:N/N:1の一部エッジケースで留保あり | DRAFT / PENDING |
| 1-B | 格納方式 | 方式2(実データGit外+Gitにはmanifest/schema)が既存の2先例
  (`.gitignore`の`/data/`、`pdfs.file_path`)と最も整合。ただし永続性・バックアップ等の
  副次的設計が未着手のままでは方式2の決定を完了したとみなさない | DRAFT / PENDING |
| 1-C | 人間承認プロセス | 候補B(ルールベース自動確定)はConstitution §4との整合性に
  明確な懸念があり除外を推奨。候補A(AI提案+全件人間レビュー)・候補C(人間が直接作成)の
  いずれかへの絞り込みが必要 | DRAFT / PENDING |
| 依存関係 | Gate間の進行順序 | Gate 1-A→1-B(概念)は直列。Gate 1-C(概念、特に候補B除外)は
  Gate 1-Bと並行検討可能。Gate 1-Bの副次的設計とGate 1-Cの技術的実装は、いずれも
  Gate 1-B格納場所確定後に着手 | DRAFT / PENDING |

## 未解決事項の集約(各Gate文書からの再掲、優先度順)

1. **[最優先]** Gate 1-Aの結論候補((i)+(ii)基本、(iii)原則不要)を承認するか。
2. Gate 1-Bの格納場所(方式1〜4)をどれにするか、および方式2の場合の副次的設計を
   別Taskとして切り出すことへの承認。
3. Gate 1-Cの候補(A/B/C/D)をどれにするか(候補B除外の可否を含む)。
4. Constitution §4の「Gold Database」「Knowledge Base」がGround Truthにどこまで
   適用されるかの解釈。
5. Gate間の進行順序を、修正案(並行検討可能)とするか、当初想定(厳密な直列)のままとするか。

## 本文書内で確定した事項

**なし。** 上記はすべて結論候補であり、いずれも`Status: APPROVED`ではない。

## POSITION AFTER TASK(本文書時点)

- Current Phase: Ground Truth(3 Gateの結論候補統合完了。Approval未実施)
- Completed: Gate 1-A/1-B/1-C/依存関係の結論候補を1つの表に統合
- Newly discovered: なし(既存4文書の統合のみ)
- Still blocked: Ground Truth実データ作成、以降のすべての後続作業
- Next approved decision: 上記「未解決事項の集約」5件
