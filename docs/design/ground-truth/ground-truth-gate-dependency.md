# Ground Truth Gate Dependency(3 Gateの依存関係)

Status: DRAFT
Approval: PENDING

DESIGN POSITION
- E14/E17 Roadmap: Phase 2 / Resolver実装前設計確定
- Current Phase: Ground Truth
- Current Subtask: Gate 1-A/1-B/1-Cの依存関係整理
- Completed: Gate 1-A(内容スコープ、結論候補)、Gate 1-B(格納方式、結論候補)、
  Gate 1-C(人間承認プロセス、結論候補)
- In Progress: 3 Gateの依存関係整理
- Blocked: Ground Truth実データ作成、以降のすべての後続作業
- This Task's Exit Condition: 想定された順序(Gate 1-A → Gate 1-B → Gate 1-C)が実際に
  成立するかを検証し、異なる点があれば現在位置・変更理由・影響範囲を明示すること

---

## 1. 想定された順序(Task指示より)

```
Gate 1-A(内容スコープ)
    ↓
Gate 1-B(格納方式)
    ↓
Gate 1-C(人間承認プロセス)
```

## 2. 実際の調査結果に基づく依存関係の検証

各Gate文書の作成を通じて確認した、実際の依存関係は以下のとおりである。

### 2.1 Gate 1-A → Gate 1-B の依存(想定どおり成立)

`ground-truth-storage-decision.md` §1で確認したとおり、Gate 1-Aの結論候補
((i)+(ii)を基本とし(iii)は原則不要)は、Gate 1-Bの「個人データリスク」評価に直接影響する。
**この依存関係は想定どおり成立している。**

### 2.2 Gate 1-B → Gate 1-C の依存(部分的に想定と異なる)

調査の結果、Gate 1-Bと Gate 1-Cの関係は、想定されていた単純な「1-B確定後に1-Cを検討する」
という一方向の順序よりも、**やや複雑な構造**であることが判明した。

- **概念レベル(候補A/B/C/Dのいずれを採用するか)は、Gate 1-Bの結論に依存しない。**
  Constitution §4「人間は承認者である」という原則は、Ground Truthの物理的な格納場所
  (リポジトリ内か外か、Gold DB経由か)を問わず適用される上位原則であり、候補Bが
  Constitution上の懸念を持つという`ground-truth-human-approval-process.md`の結論候補は、
  格納方式の選択とは独立に成立する。
- **技術的な実装レベル(disagreement処理・reviewer identity・version管理の具体的な
  記録方法)は、Gate 1-Bの格納方式に依存する。** 例えば、方式1(Git管理)であればGitの
  commit author/timestampをそのまま転用できるが、方式2(Git外)であれば、reviewer identityや
  approval timestampを記録する独自の仕組み(manifestのフィールド等)を別途設計する
  必要がある。

**したがって、「Gate 1-C全体がGate 1-B確定後でなければ着手できない」という想定は、
一部修正が必要である。** Gate 1-Cの概念的な選択(候補A/B/C/Dのどれを軸とするか、
候補Bを除外するか等)は、Gate 1-Bと並行して、あるいはGate 1-Bに先行して検討可能である。
一方、Gate 1-Cの技術的な実装詳細(具体的なフィールド設計等)は、Gate 1-B確定後でなければ
具体化できない。

## 3. 修正後の依存構造(提案、未確定)

```
Gate 1-A(内容スコープ)
    ↓ (個人データリスク評価に影響)
Gate 1-B(格納方式・概念レベル)
    │
    ├─ (並行可能) Gate 1-C(人間承認プロセス・概念レベル: 候補A/B/C/Dの選択)
    │
    ↓ (格納方式確定後)
Gate 1-B(格納方式・副次的設計: 永続性/バックアップ/manifest等、`ground-truth-
  storage-decision.md` §3で識別済み、未着手)
    ↓
Gate 1-C(人間承認プロセス・技術的実装: reviewer identity/timestamp/version等の
  具体的な記録方法)
```

**この修正は、Gate 1-A/1-B/1-Cという3つのGate自体の存在や、それぞれの結論候補の内容を
変更するものではない。** あくまで「どの順序で承認・着手できるか」という進行順序についての
整理であり、Task指示section 7が想定する「変更理由・影響範囲の明示」に該当する事項として
記録する。

## 4. 変更理由

- Gate 1-Cの概念的選択(Constitution §4適合性の評価)が、格納場所という物理的な実装詳細に
  依存しない上位原則の適用であることが、Gate 1-Cの文書作成過程で明確になったため。

## 5. 影響範囲

- Gate 1-Cの承認について、Gate 1-Bの確定を待たずに、候補Bの除外(Constitution上の懸念)
  および候補A/Cの選択については先行して判断可能である、という選択肢がユーザーに生まれる。
- ただし、Gate 1-Cの技術的実装詳細(reviewer identity記録方法等)は、引き続きGate 1-Bの
  確定を待つ必要があり、全体としてGround Truthの実データ作成に着手できる時期への影響はない
  (いずれにせよGate 1-Bの副次的設計まで完了する必要があるため)。

## 6. Gate Dependency 結論候補(未確定、承認前)

**結論候補**: Gate 1-A → Gate 1-B(概念レベル)は想定どおりの順序で成立する。Gate 1-C
(概念レベル、候補A/B/C/Dの選択)はGate 1-Bと並行検討可能である。ただし、Gate 1-Bの
副次的設計(永続性等)とGate 1-Cの技術的実装は、いずれもGate 1-Bの格納場所確定後に
着手する、という構造を提案する。**これは提案であり、確定した進行順序ではない。**

## POSITION AFTER TASK(本文書時点)

- Current Phase: Ground Truth(3 Gateの依存関係整理完了、結論候補提示。Approval未実施)
- Completed: Gate 1-A→1-B→1-Cという想定順序の検証、Gate 1-B/1-Cの関係が「概念レベル」
  「技術的実装レベル」に分解できることの整理
- Newly discovered: Gate 1-C(人間承認プロセス)の概念的選択(特に候補Bの除外)は、
  Gate 1-Bの格納方式確定を待たずに検討・承認可能であるという、当初想定より柔軟な
  進行順序が存在することが判明した
- Still blocked: Ground Truth実データ作成、Gate 1-Bの副次的設計、Gate 1-Cの技術的実装、
  以降のすべての後続作業
- Next approved decision: 修正後の依存構造(3章)を採用するか、当初の想定順序
  (Gate 1-A→1-B→1-Cの厳密な直列)のまま進めるか
