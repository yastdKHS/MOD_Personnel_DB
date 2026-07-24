# Review API

> **本ドキュメントに実装はない。** すべて`typing.Protocol`/`dataclass`による型シグネチャのみ（メソッド本体は`...`）。[`docs/review/domain.md`](../review/domain.md)のドメインモデル、[`docs/review/policy.md`](../review/policy.md)のポリシーを実装可能な契約に落とし込んだもの。[`docs/api/interfaces.md`](interfaces.md)・[`docs/api/repositories.md`](repositories.md)のReviewService/ReviewRepositoryの簡略版を、本ドキュメントが正として置き換える。
>
> **実装状況（2026-07-21時点）**: 本ドキュメントが定める`ReviewService`（キュー・割当・差戻し・再レビュー等を含む広範な契約）は未実装である。実装済みなのは、これとは異なる**Learning Dataset固有の狭い契約**（`src/mod_personnel_db/review/__init__.py`の`ReviewService` Protocol、具象実装`RepositoryReviewService`、Phase4 Task12-0）であり、`list_pending()`/`start_review()`/`approve()`/`reject()`の4メソッドのみを持つ。本ドキュメントは将来この狭い契約を統合・拡張する際の設計目標として保持する（統合の要否・方法は将来のADRで判断する）。

## 対象

`ReviewService`, `ReviewRepository`, `ReviewEvent`, `ReviewDecision`, `ReviewNotification`

---

## 値オブジェクト

### `ReviewDecision`

[`docs/review/domain.md`](../review/domain.md#reviewdecision)のドメインモデルをそのまま型として表す。

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NewType

ReviewDecisionId = NewType("ReviewDecisionId", int)
ReviewAssignmentId = NewType("ReviewAssignmentId", int)
ReviewCommentId = NewType("ReviewCommentId", int)
ReviewNotificationId = NewType("ReviewNotificationId", int)


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    id: ReviewDecisionId | None
    session_id: ReviewSessionId
    candidate_id: CandidateId
    decision: Literal["approve", "return"]
    confidence_override: Confidence | None
    reason: str
    decided_by: str
    decided_at: datetime
```

### `ReviewAssignment`

```python
@dataclass(frozen=True, slots=True)
class ReviewAssignment:
    id: ReviewAssignmentId | None
    candidate_id: CandidateId
    assigned_to: str
    priority_score: float
    priority_reason: Literal[
        "layout_unknown", "parser_error", "confidence", "knowledge_missing", "reviewer_request"
    ]
    assigned_at: datetime
    session_id: ReviewSessionId | None
    status: Literal["pending", "in_progress", "completed", "returned", "expired"]
    due_at: datetime | None
```

### `ReviewComment`

```python
@dataclass(frozen=True, slots=True)
class ReviewComment:
    id: ReviewCommentId | None
    target_type: Literal["candidate", "session"]
    target_id: CandidateId | ReviewSessionId
    author: str
    body: str
    created_at: datetime
```

### `ReviewEvent`

観測可能性（[`docs/api/pipeline.md`](pipeline.md)の`PipelineEvent`と対になる、Review Domain版のイベント記録）。

```python
@dataclass(frozen=True, slots=True)
class ReviewEvent:
    event_type: Literal[
        "assigned",
        "session_started",
        "field_modified",
        "commented",
        "decided",
        "promoted_to_gold",
        "returned",
    ]
    candidate_id: CandidateId
    actor: str
    timestamp: datetime
    detail: str | None
```

### `ReviewNotification`

```python
@dataclass(frozen=True, slots=True)
class ReviewNotification:
    id: ReviewNotificationId | None
    recipient: str
    notification_type: Literal["new_assignment", "sla_breach", "re_review_required"]
    payload: str
    created_at: datetime
    sent_at: datetime | None
```

- **不変条件**: `sent_at is None`は未送信を意味する。`notification_type == "sla_breach"`は`ReviewAssignment.due_at`超過時に生成される（[`docs/review/queue.md`](../review/queue.md)）。

---

## `ReviewService`

[`docs/review/policy.md`](../review/policy.md)の全ポリシーを実装する公開API。

```python
from typing import Protocol
from mod_personnel_db.models import CandidateId, GoldRecordId
from mod_personnel_db.review import (
    ReviewAssignment,
    ReviewAssignmentId,
    ReviewComment,
    ReviewDecision,
    ReviewDecisionId,
    ReviewEvent,
    ReviewHistory,
    ReviewSessionId,
    ReviewStatistics,
)


class ReviewService(Protocol):
    """Review Domainの公開窓口。docs/review/policy.mdの全条件をここで強制する。"""

    # --- キュー・割当（docs/review/queue.md） ---
    def next_assignment(self, reviewer: str) -> ReviewAssignment | None:
        """優先度スコア上位の未割当候補をreviewerへ払い出す（プル型、queue.md）。"""
        ...

    def list_assignments(
        self, reviewer: str, status: str | None = None
    ) -> tuple[ReviewAssignment, ...]: ...

    # --- セッション ---
    def open_session(self, reviewer: str, reason: str) -> ReviewSessionId: ...
    def close_session(self, session_id: ReviewSessionId) -> None: ...

    # --- フィールド修正・コメント ---
    def submit_field_change(
        self,
        session_id: ReviewSessionId,
        candidate_id: CandidateId,
        field_name: str,
        old_value: str | None,
        new_value: str,
        reason: str | None,
    ) -> None:
        """ReviewItemを1件記録する。policy.mdのLearning Dataset登録条件を評価する。"""
        ...

    def add_comment(self, comment: ReviewComment) -> None: ...

    # --- 決定 ---
    def decide(
        self, session_id: ReviewSessionId, candidate_id: CandidateId, decision: ReviewDecision
    ) -> ReviewDecisionId:
        """承認/差戻しを確定する。policy.mdの『誰が承認できるか』『差戻し』の条件を検証する。"""
        ...

    def promote_to_gold(self, decision_id: ReviewDecisionId) -> GoldRecordId:
        """承認済みのReviewDecisionに基づきGold Databaseへ昇格する。
        policy.mdのGold更新条件をすべて満たさない場合は例外を送出する。
        GoldRepositoryへの書き込みを行えるのはこのメソッド経由のみ
        （docs/architecture/architecture-contract.mdの保証）。"""
        ...

    # --- 再レビュー（policy.md） ---
    def trigger_re_review(self, candidate_id: CandidateId, reason: str) -> ReviewAssignmentId: ...

    # --- 参照系 ---
    def get_history(self, candidate_id: CandidateId) -> ReviewHistory: ...
    def get_statistics(
        self, period_start: object, period_end: object, reviewer: str | None = None
    ) -> ReviewStatistics: ...
```

- **例外設計**: `promote_to_gold()`が[`docs/review/policy.md`](../review/policy.md#gold更新条件)の条件を満たさない場合、`ReviewPolicyViolationError`（[`docs/api/python-contract.md`](python-contract.md#例外設計)の`MODPersonnelDBError`派生）を送出する。

## `ReviewRepository`

[`docs/api/repositories.md`](repositories.md#reviewrepository)を拡張し、`ReviewAssignment` / `ReviewDecision` / `ReviewComment`を追加で扱う。SQLite非依存の原則（[`docs/api/repositories.md`](repositories.md#sqlite非依存を実現する設計原則)）は変わらない。

```python
from typing import Protocol
from mod_personnel_db.models import CandidateId, ReviewItem, ReviewItemId


class ReviewRepository(Protocol):
    # --- 既存（docs/api/repositories.md） ---
    def create_session(self, reviewer: str, reason: str) -> ReviewSessionId: ...
    def close_session(self, session_id: ReviewSessionId, status: str) -> None: ...
    def add_change(self, session_id: ReviewSessionId, item: ReviewItem) -> ReviewItemId: ...
    def list_changes(self, session_id: ReviewSessionId) -> tuple[ReviewItem, ...]: ...
    def list_open_sessions(self) -> tuple[ReviewSessionId, ...]: ...

    # --- 追加: Assignment ---
    def add_assignment(self, assignment: ReviewAssignment) -> ReviewAssignmentId: ...
    def update_assignment_status(self, assignment_id: ReviewAssignmentId, status: str) -> None: ...
    def list_pending_assignments(self, limit: int | None = None) -> tuple[ReviewAssignment, ...]:
        """priority_score降順で返す（queue.mdの優先順位）。"""
        ...

    def get_active_assignment(self, candidate_id: CandidateId) -> ReviewAssignment | None:
        """docs/review/domain.mdの一意割当制約（pending/in_progressは同時に1件）を検証するために使う。"""
        ...

    # --- 追加: Decision ---
    def add_decision(self, decision: ReviewDecision) -> ReviewDecisionId: ...
    def get_decision(self, decision_id: ReviewDecisionId) -> ReviewDecision | None: ...
    def list_decisions_by_candidate(
        self, candidate_id: CandidateId
    ) -> tuple[ReviewDecision, ...]: ...

    # --- 追加: Comment ---
    def add_comment(self, comment: ReviewComment) -> ReviewCommentId: ...
    def list_comments(self, target_type: str, target_id: object) -> tuple[ReviewComment, ...]: ...
```

- **スコープに関する補足**: [`docs/api/repositories.md`](repositories.md#スコープに関する補足)は8 Repositoryの範囲を`docs/database/schema.md`の既存12テーブルに限定していた。`ReviewAssignment` / `ReviewDecision` / `ReviewComment`はまだテーブル化されていない新設概念（[`docs/review/domain.md`](../review/domain.md#既存スキーマとの関係)）のため、`ReviewRepository`の担当範囲を実装時に`review_assignments` / `review_decisions` / `review_comments`テーブルの新設として拡張する想定である。

## `ReviewNotification`関連の通知ディスパッチ

`ReviewNotification`（値オブジェクト、[前述](#reviewnotification)）を送出する経路。専用の`NotificationDispatcher`をProtocolとして定義する（`ReviewService`とは独立、[`docs/api/package-design.md`](package-design.md)の`review/`パッケージ内部の一関心事）。

```python
class NotificationDispatcher(Protocol):
    def notify(self, notification: ReviewNotification) -> None: ...
    def list_unsent(self) -> tuple[ReviewNotification, ...]: ...
```

具体的な配信手段（メール・チャット通知等）は実装時に選定する。`NotificationDispatcher`自体は配信手段を知らない抽象であり、[`docs/api/dependency-rule.md`](dependency-rule.md)の一般原則（具体的な技術は抽象を経由する）に従う。

---

## 関連ドキュメント

- [`docs/review/domain.md`](../review/domain.md) — ドメインモデル・ライフサイクル
- [`docs/review/policy.md`](../review/policy.md) — 本APIが強制するポリシー
- [`docs/review/queue.md`](../review/queue.md) — `next_assignment()`の優先順位ロジック
- [`docs/api/repositories.md`](repositories.md) — Repository Patternの一般原則
- [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) — `promote_to_gold()`の排他性保証
