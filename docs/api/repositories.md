# Repository Pattern 設計

> **本ドキュメントに実装はない。** すべて`typing.Protocol`による型シグネチャのみ。`sqlite3`・SQL文字列・SQLite固有の型は一切登場しない。将来PostgreSQLへ移行する場合、本ドキュメントのインターフェースは変更せず、`repositories/sqlite/`と並ぶ`repositories/postgres/`を追加するだけで済む設計を意図している。

## SQLite非依存を実現する設計原則

1. **インターフェースの引数・戻り値は、[`models.md`](models.md)のモデル／値オブジェクト、または標準ライブラリの型（`str`, `int`, `date`, `datetime`, `tuple`, `dict`）のみを用いる。** `sqlite3.Connection`・`sqlite3.Cursor`・SQL文字列・SQLite固有のプレースホルダ構文は登場しない。
2. **ID型は不透明な値オブジェクト**（`NewType`によるラップ、[`models.md`](models.md#補助的な値オブジェクト)参照）とする。内部表現が`INTEGER`（SQLite `rowid`）か`SERIAL`（PostgreSQL）かはRepositoryの実装詳細であり、呼び出し側はIDの生成方法を意識しない。
3. **日時は`datetime.date` / `datetime.datetime`型で受け渡す。** SQLite側でのISO8601文字列表現（[`docs/database/schema.md`](../database/schema.md#設計方針命名規約)）は`repositories/sqlite/`内部の変換関心事であり、インターフェースには現れない。
4. **JSON列（`raw_fields`等）は、パース済みのモデル型として受け渡す。** 生のJSON文字列をRepositoryの引数・戻り値として扱わない。
5. **トランザクションは`UnitOfWork`（後述）で抽象化する。** SQLiteの`BEGIN`/`COMMIT`、PostgreSQLの`BEGIN`/`COMMIT`はいずれも`UnitOfWork.__enter__`/`commit`/`rollback`の背後に隠蔽される。
6. **ページネーションは`limit: int` / `offset: int`等の単純な引数で表現し、`LIMIT`/`OFFSET`のSQL構文をインターフェースに漏らさない。**

## スコープに関する補足

[`docs/database/schema.md`](../database/schema.md)は12の業務テーブルを定義するが、本タスクが列挙する8 Repositoryには`personnel_sections` / `layouts` / `parser_versions`に対応する専用Repositoryが含まれていない。これらは以下のように既存8 Repositoryのスコープに含める（9個目以降のRepositoryを新設しない、過剰設計を避ける判断、[ADR-0014](../adr/0014-development-discipline.md)）。

| DBテーブル | 担当Repository | 理由 |
|---|---|---|
| `personnel_sections` | `CandidateRepository` | セクションは常に候補レコードの親であり、同一の書き込みトランザクションで扱われるため |
| `layouts` | `KnowledgeRepository` | レイアウト定義も「起動時にロードされ参照される読み取り中心の参照データ」という性質が`knowledge_items`と共通するため |
| `parser_versions` | `JobRepository` | パーサーバージョンの記録はリリース・ジョブ実行と密結合するため（[ADR-0023](../adr/0023-parser-versioning-policy.md)） |

---

## `CandidateRepository`

`candidate_records` と `personnel_sections` を担当する。

```python
from typing import Protocol
from mod_personnel_db.models import (
    PersonnelSection, PersonnelSectionId, RawRecord, NormalizedRecord,
    ValidationResult, CandidateId, CandidateRecord,
)


class CandidateRepository(Protocol):
    def add_section(self, section: PersonnelSection) -> PersonnelSectionId: ...
    def get_section(self, section_id: PersonnelSectionId) -> PersonnelSection | None: ...

    def add_raw(self, section_id: PersonnelSectionId, record: RawRecord) -> CandidateId: ...
    def attach_normalized(self, candidate_id: CandidateId, normalized: NormalizedRecord) -> None: ...
    def update_validation(self, candidate_id: CandidateId, result: ValidationResult) -> None: ...

    def get(self, candidate_id: CandidateId) -> CandidateRecord | None: ...
    def list_by_section(self, section_id: PersonnelSectionId) -> tuple[CandidateRecord, ...]: ...
    def list_pending_validation(self) -> tuple[CandidateRecord, ...]: ...
    def list_failed_validation(self) -> tuple[CandidateRecord, ...]: ...
```

- **不変性**: `add_raw`で作成された行の`raw_fields`は以後変更しない（[`docs/database/schema.md`](../database/schema.md#4-candidate_records)のINSERT-only設計）。`attach_normalized`・`update_validation`は追加情報の付与のみであり、既存フィールドの上書きではない。

## `GoldRepository`

```python
from typing import Protocol
from datetime import date, datetime
from mod_personnel_db.models import (
    CandidateId, NormalizedRecord, GoldRecordId, GoldRecord,
)


class GoldRepository(Protocol):
    def add_version(
        self,
        candidate_id: CandidateId,
        record: NormalizedRecord,
        person_key: str,
        effective_date: date,
        appointment_type: str,
    ) -> GoldRecordId: ...

    def supersede(self, old_id: GoldRecordId, new_id: GoldRecordId) -> None:
        """旧バージョンをis_current=Falseにし、superseded_byを新バージョンに設定する。"""
        ...

    def get_current(self, person_key: str, effective_date: date) -> GoldRecord | None: ...
    def get_history(self, person_key: str) -> tuple[GoldRecord, ...]: ...
    def list_current(self, as_of: datetime | None = None) -> tuple[GoldRecord, ...]: ...
```

- **不変性**: `gold_records`はSCD Type 2で管理する（[ADR-0015](../adr/0015-sqlite-schema-finalization.md)）。既存バージョンへの直接UPDATEは提供せず、`add_version` + `supersede`の2操作のみで訂正履歴を表現する。

## `KnowledgeRepository`

`knowledge_items` と `layouts` を担当する。

```python
from typing import Protocol
from datetime import date
from mod_personnel_db.models import KnowledgeItem, Layout


class KnowledgeRepository(Protocol):
    def upsert_item(self, item: KnowledgeItem) -> None:
        """knowledge/ファイルの内容をロードし、対応する行を追加または無効化する（一方向同期）。"""
        ...

    def get_item(self, category: str, item_key: str, as_of: date | None = None) -> KnowledgeItem | None: ...
    def list_items(self, category: str) -> tuple[KnowledgeItem, ...]: ...

    def get_layout(self, era_id: str, version: int | None = None) -> Layout | None: ...
    def list_active_layouts(self, as_of: date | None = None) -> tuple[Layout, ...]: ...
```

- **不変性**: `knowledge/`ディレクトリのファイルが正（source of truth）であり、本Repositoryへの書き込みは常にファイル読み込みの結果としてのみ行われる（[`docs/knowledge/schema.md`](../knowledge/schema.md)、[ADR-0005](../adr/0005-knowledge-base-normalization.md)）。

## `LearningRepository`

```python
from typing import Protocol
from mod_personnel_db.models import LearningRecord, LearningRecordId, LearningStatus, ParserVersionId


class LearningRepository(Protocol):
    def add(self, record: LearningRecord) -> LearningRecordId: ...

    def update(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        """ライフサイクル遷移に伴うフィールド更新（docs/architecture/learning_dataset.md参照）。"""
        ...

    def get(self, record_id: LearningRecordId) -> LearningRecord | None: ...
    def list_by_status(self, status: LearningStatus) -> tuple[LearningRecord, ...]: ...
    def list_by_error_category(self, category: str) -> tuple[LearningRecord, ...]: ...
    def list_by_parser_version(self, parser_version_id: ParserVersionId) -> tuple[LearningRecord, ...]: ...
```

## `PDFRepository`

```python
from typing import Protocol
from mod_personnel_db.models import PdfRecord, PdfId


class PDFRepository(Protocol):
    def add(self, pdf: PdfRecord) -> PdfId: ...
    def get(self, pdf_id: PdfId) -> PdfRecord | None: ...
    def get_by_hash(self, content_hash: str) -> PdfRecord | None:
        """内容アドレス方式の重複排除に用いる（ADR-0018）。"""
        ...
    def update_status(self, pdf_id: PdfId, status: str) -> None: ...
    def list_by_status(self, status: str) -> tuple[PdfRecord, ...]: ...
```

## `JobRepository`

`jobs` と `parser_versions` を担当する。

```python
from typing import Protocol
from mod_personnel_db.models import Job, JobId, ParserVersion, ParserVersionId


class JobRepository(Protocol):
    def add(self, job: Job) -> JobId: ...
    def update_status(
        self, job_id: JobId, status: str, processed_count: int, failed_count: int
    ) -> None: ...
    def get(self, job_id: JobId) -> Job | None: ...
    def list_running(self) -> tuple[Job, ...]: ...

    def record_parser_version(self, version: ParserVersion) -> ParserVersionId:
        """CIのリリースタグ付与をトリガーに呼ばれる（ADR-0023）。"""
        ...
    def get_parser_version(self, code_version: str) -> ParserVersion | None: ...
    def get_latest_parser_version(self) -> ParserVersion | None: ...
```

## `ExportRepository`

```python
from typing import Protocol
from mod_personnel_db.models import ExportRecord, ExportId


class ExportRepository(Protocol):
    def add(self, export: ExportRecord) -> ExportId: ...
    def get(self, export_id: ExportId) -> ExportRecord | None: ...
    def list_recent(self, limit: int = 10) -> tuple[ExportRecord, ...]: ...
    def get_latest(self, format: str) -> ExportRecord | None: ...
```

## `ReviewRepository`

```python
from typing import Protocol
from mod_personnel_db.models import ReviewItem, ReviewItemId, ReviewSessionId


class ReviewRepository(Protocol):
    def create_session(self, reviewer: str, reason: str) -> ReviewSessionId: ...
    def close_session(self, session_id: ReviewSessionId, status: str) -> None: ...
    def add_change(self, session_id: ReviewSessionId, item: ReviewItem) -> ReviewItemId: ...
    def list_changes(self, session_id: ReviewSessionId) -> tuple[ReviewItem, ...]: ...
    def list_open_sessions(self) -> tuple[ReviewSessionId, ...]: ...
```

---

## `UnitOfWork`

複数Repositoryにまたがる操作（例: `ReviewService.promote_to_gold`が`GoldRepository`・`ReviewRepository`・`LearningRepository`を同時に更新する）の原子性を保証する、Repository Patternの標準的な随伴パターン。8 Repositoryのいずれにも明示的に列挙されていないが、Task 3の要求（複数Repositoryを横断する整合性の担保）を満たすために必要な補助インターフェースとして定義する。

```python
from typing import Protocol
from types import TracebackType
from mod_personnel_db.repositories import (
    CandidateRepository, GoldRepository, KnowledgeRepository, LearningRepository,
    PDFRepository, JobRepository, ExportRepository, ReviewRepository,
)


class UnitOfWork(Protocol):
    candidates: CandidateRepository
    gold: GoldRepository
    knowledge: KnowledgeRepository
    learning: LearningRepository
    pdfs: PDFRepository
    jobs: JobRepository
    exports: ExportRepository
    reviews: ReviewRepository

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

`repositories/sqlite/`での実装は、`sqlite3.Connection`を1つ共有する8つのRepository実装を束ね、`commit()`/`rollback()`をSQLiteのトランザクション制御にマッピングする。`repositories/postgres/`（将来）も同じ`UnitOfWork` Protocolを満たす限り、呼び出し側（`review/`, `pipeline/`等）のコードは一切変更不要である。

---

## PostgreSQL移行時に変更が必要な範囲（参考）

| 変更が必要 | 変更が不要 |
|---|---|
| `repositories/sqlite/` の実装（新規`repositories/postgres/`を追加） | 本ドキュメントのProtocol定義 |
| `config/`（接続文字列・ドライバ選択） | `document/`〜`validators/`, `knowledge/`, `learning/`, `review/`, `export/`, `pipeline/`等、Repositoryを利用する全パッケージ |
| DDL（[`docs/database/schema.md`](../database/schema.md)のSQLite固有構文、例: `STRFTIME`関数、`INTEGER PRIMARY KEY`の意味論） | [`models.md`](models.md)のドメインモデル定義 |

この表自体が、Repository Patternによる抽象化がSQLite依存を正しく閉じ込められているかの検証基準になる。
