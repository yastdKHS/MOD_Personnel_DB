# Review Queue

> `Candidate`状態にある候補を、どの順序でレビュアーに割り当てるか（[`domain.md`](domain.md)の`Candidate --> Assigned`遷移）を決定する優先順位付けの設計。本ドキュメントに実装はない。

## 優先順位の基本方針

ユーザー提示の5要因（Confidence, Layout Unknown, Parser Error, Knowledge Missing, Reviewer Request）を、**単純な固定順序リストではなく、連続値のスコアとして統合する**。理由は以下の通り。

- 固定順序（例: 常にLayout Unknownを最優先）だと、同一要因内での優先度の差（例: confidence 0.05と0.45はどちらも「低confidence」だが緊急度が違う）を表現できない。
- スコア方式にすることで、[`policy.md`](policy.md#再レビュー)の再レビューのような追加要因も同じ枠組みに統合できる。
- 長期間放置された低優先度項目が飢餓状態（starvation）にならないよう、経過時間による補正を組み込む。

## 優先度スコアの算出

```python
BASE_SCORE = {
    "layout_unknown": 1000.0,     # 新様式・未知レイアウト（バッチ全体に影響しうる、最優先）
    "parser_error": 900.0,        # Field Extractor/Normalizer等での例外発生（パイプライン健全性）
    "confidence": 800.0,          # 上限値。実際のスコアは 800 * (1 - confidence_score)
    "knowledge_missing": 500.0,   # error_category in {unknown_alias, knowledge_gap}（ADR-0012）
    "reviewer_request": 300.0,    # 人手による明示的なフラグ立て
}
AGING_BOOST_PER_DAY = 20.0        # 1日あたりの経過時間補正
AGING_CAP = 200.0                 # 経過時間補正の上限（無制限のエスカレーションを防ぐ）


def priority_score(reason: str, now: datetime, created_at: datetime, confidence_score: float | None = None) -> float:
    base = BASE_SCORE[reason]
    if reason == "confidence":
        base = BASE_SCORE["confidence"] * (1.0 - confidence_score)
    age_days = (now - created_at).total_seconds() / 86400
    aging = min(AGING_BOOST_PER_DAY * age_days, AGING_CAP)
    return base + aging
```

- **`reason`**: `ReviewAssignment.priority_reason`（[`domain.md`](domain.md#reviewassignment)）に対応する主要因。1候補が複数の要因を持つ場合（例: 低confidenceかつKnowledge Missing）、**最も高い`reason`のスコアを採用する**（要因ごとの単純合算はしない。理由: 合算すると、複数の軽微な要因を持つ項目が単一の深刻な要因を持つ項目より優先されてしまう逆転が起こり得るため）。
- **`confidence`要因の連続スコア**: `confidence_score`が低いほど`800`に近づき、`1.0`（満点）では`0`になる。[`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール)の`band`区分（`low`/`medium`/`high`/`verified`）とは独立した連続値を用いることで、同じ`band`内での優先順位も表現する。
- **`layout_unknown` / `parser_error`が常に上位**: これらはバッチ全体（同一様式の全PDF、または同一コードバージョンの全処理）に波及しうる系統的な問題であり、個別レコードの正確性（`confidence`）より先に対処すべきという判断（[ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位思想——Layout/Knowledge Baseの欠落は個別対応より上流での解決を優先する——をキューの緊急度にも反映）。
- **経過時間補正（Aging）**: 1日あたり`+20`、上限`+200`（10日で頭打ち）。優先度の低い要因（`reviewer_request`, `knowledge_missing`）が長期間放置されるのを防ぐ一方、上限を設けることで「古いだけの軽微な項目」が`layout_unknown`のような真に緊急な項目を追い抜くことは防ぐ。

### 算出結果の検証（具体例）

上記の式を実際に計算した結果、意図した優先順位（系統的問題 > 低confidence > 経過時間で補正されたその他）が得られることを確認した。

| スコア | シナリオ |
|---|---|
| 1000.0 | `layout_unknown`（新規） |
| 900.0 | `parser_error`（新規） |
| 720.0 | `confidence=0.10`（新規） |
| 700.0 | `knowledge_missing`（20日経過、経過時間補正が上限`200`に到達） |
| 500.0 | `reviewer_request`（10日経過、補正上限到達） / `knowledge_missing`（新規）※同点 |
| 360.0 | `confidence=0.55`（新規） |
| 300.0 | `reviewer_request`（新規） |
| 200.0 | `confidence=0.75`（新規、`high`帯域に近く優先度は低い） |

`knowledge_missing`（新規, 500点）と`reviewer_request`（10日経過, 500点）が同点になるのは意図どおりであり、同点の場合は`created_at`が古い方を先に処理する（安定ソート）。

## 要因の分類基準

| `priority_reason` | 判定条件 | 由来 |
|---|---|---|
| `layout_unknown` | `LayoutDetector.run()`の戻り値`LayoutArtifact`の`.detection.confidence`が閾値未満、または既知の`era_id`に一致しない（[ADR-0037](../adr/0037-layout-detector-produces-layout-artifact.md)、値の意味・算出方法は無変更） | [`docs/api/interfaces.md`](../api/interfaces.md#中核パイプライン6段階) |
| `parser_error` | `PipelineException`（[`docs/api/pipeline.md`](../api/pipeline.md#pipelineexception)）が`document/`〜`validators/`のいずれかの段階で送出された | [`docs/api/pipeline.md`](../api/pipeline.md) |
| `confidence` | `ValidationResult.confidence.band`が`low`または`medium` | [`docs/database/json_schema.md`](../database/json_schema.md#confidenceの算出ルール) |
| `knowledge_missing` | `LearningRecord.error_category`が`unknown_alias`または`knowledge_gap` | [ADR-0012](../adr/0012-error-handling-priority-order.md) |
| `reviewer_request` | レビュアーが`ReviewComment`等で明示的に再確認を要求した、または[`policy.md`](policy.md#再レビュー)の再レビュートリガーに該当 | [`policy.md`](policy.md#再レビュー) |

## キューの消化モデル

- `ReviewAssignment`は、`Scheduler`（[ADR-0019](../adr/0019-workflow-orchestration.md)、[`docs/api/interfaces.md`](../api/interfaces.md#scheduler)）ではなく、レビュアーが`ReviewSession`を開始した時点で`ReviewQueue`（`review/`パッケージ内部の関心事、[`docs/api/package-design.md`](../api/package-design.md)）が優先度上位から払い出す**プル型**とする（レビュアーの作業ペースに関わらず自動でジョブを積み上げるプッシュ型は、少人数運用の初期段階では過剰、[ADR-0021](../adr/0021-review-ui-strategy.md)と同じ判断基準）。
- 1人のレビュアーが同時に保持できる`ReviewAssignment`（`status="pending"`または`"in_progress"`）の上限は、実装時に運用実態を見て決定する（本ドキュメントでは上限値自体は定めない）。
