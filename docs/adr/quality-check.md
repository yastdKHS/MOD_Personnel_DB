# ADR Quality Check Report

> 実施日: 2026-07-18。対象: `docs/adr/0001-*.md` 〜 `docs/adr/0026-*.md`（全26本）。本レポートは機械的なスクリプト検証と目視レビューを組み合わせて実施した結果であり、発見した問題は本レポート作成と同一の作業の中で修正済みである。

## 検査項目サマリ

| # | 項目 | 結果 | 詳細 |
|---|---|---|---|
| 1 | 重複しているADRはないか | 問題なし（要説明の近接ケース3件） | [重複チェック](#重複チェック) |
| 2 | 矛盾しているADRはないか | 問題なし | [矛盾チェック](#矛盾チェック) |
| 3 | 孤立したADRはないか | **1件発見・修正済み**（ADR-0009） | [孤立したADR](#孤立したadr) |
| 4 | 参照切れはないか | **2件発見・修正済み**（`docs/knowledge/schema.md`） | [参照切れチェック](#参照切れチェック) |
| 5 | SupersededすべきADRはないか | 該当なし | [Supersede候補チェック](#supersede候補チェック) |

---

## 依存関係の抽出方法

各ADRファイル本文から正規表現 `ADR-[0-9]{4}` を抽出し、自己参照（自分自身の番号）を除外して有向グラフを構築した。

```bash
for f in docs/adr/00*.md; do
  num=$(basename "$f" .md | grep -oE '^[0-9]{4}')
  grep -oE 'ADR-[0-9]{4}' "$f" | sort -u | grep -v "ADR-$num"
done
```

抽出結果は26ノード・60エッジであり、[`dependency-map.md`](dependency-map.md)のMermaid図と[被参照数ランキング](dependency-map.md#被参照数in-degreeランキング上位実測値)は、この抽出結果を`Counter`で集計した実測値である（手計算ではなくPythonスクリプトで再検証済み）。

## 重複チェック

**方法**: 全26 ADRのタイトル・コンテキストを比較し、同一の設計判断を独立に2度決定していないかを確認した。

**結果**: 完全な重複は検出されなかった。ただし、一見重複に見えかねない近接した3組について、意図的な役割分担であることを確認した。

| 組 | 一見重複に見える理由 | 実際の役割分担 |
|---|---|---|
| [ADR-0006](0006-pipeline-provenance.md) と [ADR-0011](0011-fixed-core-pipeline.md) | 両方とも「パイプラインの段階構成」を扱う | 0006はステージ分割と来歴管理という**方針**、0011はDocument Analyzer〜Validatorという**具体的な段階名・固定化**。0006のコンテキストは0011を参照するよう既に整理済み（[ADR-0006の関連ADR節](0006-pipeline-provenance.md#関連adr)） |
| [ADR-0013](0013-learning-dataset-not-correction-log.md) と [ADR-0017](0017-learning-dataset-field-expansion.md) | 両方とも「Learning Dataset」を扱う | 0013は「Correction LogではなくLearning Datasetとして設計する」という**方針決定**、0017はその**フィールド仕様・ライフサイクルの詳細化**。0013の関連ADR節が0017を明示的に参照 |
| [ADR-0010](0010-ci-cd-and-publish-strategy.md)・[ADR-0016](0016-public-json-format.md)・[ADR-0022](0022-export-policy.md) | 3本とも「公開・エクスポート」を扱う | 0010は公開フローの**ガバナンス**（人手ゲート）、0016はJSON形式の**詳細契約**、0022はCSV/Parquetを含む**運用ポリシー**（頻度・提供期間）。0022作成時に[Gap Analysis](gap-analysis.md#export-policy)で重複を避けるようスコープを明示的に絞った |

これらは「発展的詳細化」であり「重複」ではないと判定した。

## 矛盾チェック

**方法**: 技術選定・数値基準・運用方針について、ADR間で異なる結論が出ていないかを確認した。

**確認した観点と結果**:

- **ビルド・依存管理方針**: [ADR-0001](0001-python-packaging.md)（setuptools、依存最小化）と、[ADR-0019](0019-workflow-orchestration.md)・[ADR-0022](0022-export-policy.md)・[ADR-0025](0025-deployment-strategy.md)・[ADR-0026](0026-security-policy.md)の新規ツール導入判断（GitHub Actions優先、独自スキーマ言語の不採用等）は、いずれも「枯れた技術・依存最小化」の方針で一貫しており矛盾なし。
- **実行基盤**: [ADR-0019](0019-workflow-orchestration.md)（GitHub Actionsスケジュール実行）と[ADR-0025](0025-deployment-strategy.md)（常時稼働サーバーを持たないバッチ実行）は、相互に補強し合う内容であり矛盾なし。
- **データ削除ポリシー**: [ADR-0006](0006-pipeline-provenance.md)・[ADR-0015](0015-sqlite-schema-finalization.md)（削除せず追記）と[ADR-0024](0024-knowledge-versioning-and-backfill.md)（バックフィルは既定で行わない）は、「過去データを勝手に書き換えない」という同一方針の異なる側面であり矛盾なし。
- **数値基準**: 関数サイズ上限（[ADR-0014](0014-development-discipline.md)）、confidence閾値（[`json_schema.md`](../database/json_schema.md)・[`learning_dataset.md`](../architecture/learning_dataset.md)）等、複数箇所に現れる数値基準はすべて同一の出典を参照しており、値の不一致は見つからなかった。

矛盾は検出されなかった。

## 孤立したADR

**方法**: [依存関係の抽出方法](#依存関係の抽出方法)で構築したグラフに対し、in-degree（被参照数）・out-degree（参照数）を集計し、`in=0 かつ out=0`（ADR間参照が完全にゼロ）のノードを検出した。

**ADR間参照のみで見た結果**: 完全孤立（in=0かつout=0）のノードは存在しない。ただし、新規追加の[0018](0018-pdf-registry-and-retention.md), [0020](0020-benchmark-dataset.md), [0021](0021-review-ui-strategy.md), [0022](0022-export-policy.md), [0023](0023-parser-versioning-policy.md), [0024](0024-knowledge-versioning-and-backfill.md), [0026](0026-security-policy.md)、および既存の[0009](0009-ai-agent-operating-policy.md)は、他ADRから参照されていない（in-degree 0）。新規ADRについては追加直後であるため自然な状態であり、問題とは判定しない。

**発見した問題**: [ADR-0009](0009-ai-agent-operating-policy.md)（AIコーディングエージェント運用方針）について、ADR間参照だけでなく**リポジトリ全体**を対象に参照元を検索したところ、`CLAUDE.md` / `AGENTS.md` のいずれからも直接リンクされていないことが判明した。両ファイルはADR-0009の決定を実装したドキュメントであるにもかかわらず、逆リンクが欠落していた。

```
grep -rl "ADR-0009" --include="*.md" . 2>/dev/null
# → 修正前: 該当なし（自ファイル内にも "ADR-0009" という文字列表現が存在しないため）
```

**修正**: `CLAUDE.md` および `AGENTS.md` の「関連ドキュメント」節に、ADR-0009への直接リンクを追加した（決定内容を変更しない追記のため、[README.mdの更新ルール](README.md#更新ルール)が許容する範囲の修正）。

## 参照切れチェック

**方法**: リポジトリ内の全Markdownファイルから相対リンク `[text](path)` を抽出し、リンク先ファイルが実在するかをPythonスクリプトで機械的に検証した（HTTPリンク・フラグメントのみのリンクは対象外）。

```python
# 簡略版。実際は os.walk で全 .md ファイルを走査し、
# 相対パスを os.path.normpath で解決して os.path.exists を確認した。
```

**1回目の検証（新規ADR追加前）**: 323件の相対リンクを検査し、2件の参照切れを検出。

```
- docs/knowledge/schema.md -> json_schema.md
- docs/knowledge/schema.md -> json_schema.md#draft-2020-12に関する留意事項
```

原因: `docs/knowledge/schema.md` から `docs/database/json_schema.md` への相対パスが `json_schema.md`（同一ディレクトリ想定）のまま誤って記述されていた。正しくは `../database/json_schema.md`。

**修正**: 両箇所を `../database/json_schema.md` に修正。

**2回目の検証（新規ADR追加後、最終確認）**: 446件の相対リンクを検査し、参照切れ0件（[`index.md`](index.md)・[`dependency-map.md`](dependency-map.md)・[`README.md`](README.md)から本ファイルへの新規リンクを含め、すべて解決可能）。

## Supersede候補チェック

**方法**: 新規追加した9本のADR（0018〜0026）が、既存ADR（0001〜0017）のいずれかの決定内容を変更・撤回していないかを確認した。

**結果**: 該当なし。0018〜0026はいずれも[Gap Analysis](gap-analysis.md)で「既存ADRでは決定されていなかった」と判定した領域を新たに決定するものであり、既存ADRの内容と競合・矛盾する決定は含まれない（[矛盾チェック](#矛盾チェック)と合わせて確認済み）。既存ADR（0001〜0017）はステータス・内容ともに変更していない。

## 未対応・今後の観察事項

- 新規ADR（0018〜0026）のin-degreeが0である状態は、今後関連する実装・ドキュメントが追加されるにつれて自然に解消される見込みである。次回のADR追加時、または実装着手時に改めて確認する。
- `docs/adr/README.md` の[レビュー手順](README.md#レビュー手順)に従い、今後ADRを追加・変更する際は本レポートと同様の機械的チェック（重複・矛盾・孤立・参照切れ）を実施することを推奨する。
