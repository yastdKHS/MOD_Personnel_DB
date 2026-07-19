# Coding Style Guide

> 本ドキュメントは[`docs/implementation.md`](implementation.md)（Implementation Guide）に従属する、コーディングスタイルの詳細規約である。`docs/api/python-contract.md`が定める型・Protocol・例外・ログ設計とは重複させず、命名・構文選択・可読性に関する規約に専念する。実装は含まない。

## 命名規則

Python標準の命名規則（PEP 8）を基本とし、`ruff`の`N`ルール（[`pyproject.toml`](../pyproject.toml)の`[tool.ruff.lint] select`に含まれる`pep8-naming`相当）で機械的に検証する。本節以下は、本プロジェクト固有の命名パターンを定める。

### Module命名

- 全て`snake_case`。
- パッケージ名は[`docs/api/package-design.md`](api/package-design.md)が定める21パッケージの名称をそのまま用いる（`document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`, `repositories/`, `knowledge/`, `learning/`, `features/`, `review/`, `export/`, `ftp/`, `fetch/`, `pipeline/`, `services/`, `config/`, `utils/`, `models/`, `cli/`）。
- 複数の具象実装を束ねるパッケージ（`extractors/`, `normalizers/`, `validators/`, `repositories/`のように、将来複数の実装が並ぶ、または概念上複数形が自然なもの）は複数形、単一の概念・機能を表すパッケージ（`config/`, `pipeline/`, `knowledge/`）は単数形とする。既存のパッケージ一覧の形をそのまま踏襲し、新規パッケージ追加時もこの慣例に従う。

### Class命名

- `PascalCase`。
- ドメインモデル（[`docs/api/models.md`](api/models.md)）は名詞句（`Document`, `PersonnelSection`, `RawRecord`等）。動詞・動作を含む名前にしない。
- パイプライン段階の実装クラスは、その役割をそのまま名詞化する（`DocumentAnalyzer`, `LayoutDetector`, `SectionParser`, `FieldExtractor`, `Normalizer`, `Validator`）。段階名を省略・短縮しない。

### Protocol命名

- `Protocol`を実装するクラスは、Hungarian記法の`I`接頭辞（`IRepository`等）を付けない。役割そのものを表す名詞をそのまま使う（`PipelineStage`, `CandidateRepository`, `ReviewService`等、[`docs/api/interfaces.md`](api/interfaces.md), [`docs/api/repositories.md`](api/repositories.md)）。
- `Protocol`であることを名前で区別する必要はない（型チェッカーが構造的部分型として扱うため、命名上の区別は不要）。

### ABC命名

- 同一パッケージ内部で共有する部分実装には`Base`接尾辞を付ける（例: `repositories/sqlite/`内部の`SqliteRepositoryBase`、[`docs/api/python-contract.md`](api/python-contract.md#abc利用方針)）。
- `Base`接尾辞のクラスは、他パッケージから直接importされない実装詳細であることを名前で示す。

### Repository命名

- `<Entity>Repository`（Protocol、[`docs/api/repositories.md`](api/repositories.md)の8種: `CandidateRepository`, `GoldRepository`, `KnowledgeRepository`, `LearningRepository`, `PDFRepository`, `JobRepository`, `ExportRepository`, `ReviewRepository`）。
- SQLite具象実装は`Sqlite<Entity>Repository`（例: `SqliteGoldRepository`）とし、`repositories/sqlite/`パッケージ内に置く。将来のPostgreSQL実装は同じ命名パターンで`Postgres<Entity>Repository`とする。

### Service命名

- `<Domain>Service`（[`docs/api/interfaces.md`](api/interfaces.md)の`ReviewService`, `ExportService`, `FTPService`, `KnowledgeService`, `LearningService`）。
- サービス名がパッケージ名（`review/`, `export/`等）と対応することを常に維持する。

### Interface命名

- 本プロジェクトにおける「Interface」（他パッケージから見た契約全般、`Protocol`・公開関数シグネチャを含む）は、実装の詳細を名前に含めない。「何をするか」ではなく「何であるか」を表す名詞で命名する。
- インターフェースを構成するメソッド名は動詞（`run()`, `get_by_id()`, `save()`等）とし、インターフェース自体の型名（クラス名）とは明確に区別する。

### Enum命名

- Enumクラス名は`PascalCase`（例: `LearningStatus`）。
- メンバー名（Python識別子）は`UPPER_SNAKE_CASE`。
- メンバー値（`enum.StrEnum`の場合の文字列値、[ADR-0030](adr/0030-strenum-adoption.md)）は、対応するDBの`CHECK`制約の値と1対1で一致する小文字`snake_case`とする。

  ```python
  class LearningStatus(StrEnum):
      OPEN = "open"
      IN_REVIEW = "in_review"
      REFLECTED = "reflected"
      VERIFIED = "verified"
  ```

  （[`docs/api/models.md`](api/models.md)の`LearningStatus`が既存の正例）

### Exception命名

- 全て`<内容>Error`の`PascalCase`（`RepositoryError`, `KnowledgeLoadError`, `ValidationBlockedError`等）。基底は`MODPersonnelDBError`（[`docs/api/python-contract.md`](api/python-contract.md#例外設計)）。
- `Exception`接尾辞は使わない（`Error`に統一し、表記ゆれを作らない）。

### Logger命名

- 各モジュールは`logging.getLogger(__name__)`で取得する（[`docs/api/python-contract.md`](api/python-contract.md#logging設計)）。モジュールパスと異なる独自のロガー名を付けない。

### 変数命名

- `snake_case`。省略語は一般的なもの（`pdf`, `id`, `url`, `db`）に限り許可し、プロジェクト固有の略語を新たに作らない。
- 真偽値変数は`is_` / `has_` / `should_`等の接頭辞を持つ（例: `is_valid`, `has_knowledge_match`）。

### 定数命名

- モジュールレベル定数は`UPPER_SNAKE_CASE`。
- Enumで表現すべき閉じた値集合（[`docs/api/python-contract.md`](api/python-contract.md#enum利用方針)の判断基準）と、単一の閾値・上限値等の定数は区別する。後者の例: Confidence band閾値（`CONFIDENCE_HIGH_THRESHOLD = 0.85`等、[`docs/database/json_schema.md`](database/json_schema.md#confidenceの算出ルール)の値を定数化したもの）。

## 関数長

1関数あたり最大30文・最大分岐数8・最大循環的複雑度8・最大引数5・最大return文数6。`pyproject.toml`の`ruff`設定（`C90`, `PLR09xx`）で機械的に検出する（[ADR-0014](adr/0014-development-discipline.md)）。閾値内でも複数責務を持つ関数は分割する。

## クラス長

機械的な行数上限は設けない（`dataclass`のように、多くのフィールドを持つが振る舞いを持たないクラスに一律の行数制限は適さないため）。代わりに以下を目安とする。

- 公開メソッドが10個を超えるクラスは、単一責務原則（SRP）への違反を疑い、分割を検討する。
- `dataclass`（[`docs/api/python-contract.md`](api/python-contract.md#dataclass利用方針)）はこの目安の対象外とする（属性のみで振る舞いを持たないため）。
- 判断はコードレビュー（[`docs/implementation.md`](implementation.md#code-review-rule)）に委ね、`ruff`等での機械的強制は行わない。

## ファイル長

機械的な上限は設けない。目安として400行を超えるファイルは分割の余地がないか確認する（ソフトガイドラインであり、CIではブロックしない）。1ファイルが複数の無関係なクラス・関数を含む場合は、[`docs/api/package-design.md`](api/package-design.md)のパッケージ境界に沿って分割する。

## コメント方針

- コメントは既定で書かない。識別子（変数名・関数名・クラス名）が十分に説明的であれば、コメントは不要である。
- コメントを書くのは、**非自明なWHY**（隠れた制約、特定のバグの回避策、一見不要に見えるが必要なコード等）に限る。コードが「何をしているか」を説明するコメントは書かない（識別子で表現する）。
- 実装のタスク番号・PR番号・呼び出し元への参照をコメントに含めない（コミット履歴・PR説明に属する情報であり、コードとともに古くなる）。

## Docstring方針

- すべての公開モジュール・クラス・関数には、最低1行の要約Docstringを付与する。
- 単純な`dataclass`のフィールドや、シグネチャから自明な単純関数は、1行Docstringのみで足りる（[`docs/api/python-contract.md`](api/python-contract.md#例外設計)の例外クラスDocstringが正例）。
- 複雑な事前条件・事後条件・例外を持つ関数は、追加のセクション（Args/Returns/Raises相当）を持つDocstringを付与する。書式は実装着手時にプロジェクト全体で統一する（Google styleを既定候補とする）。
- プライベート関数（`_`接頭辞）で、呼び出し元から見て自明なものにはDocstringを必須としない。

## 型ヒント方針

100%型ヒント必須、`mypy --strict`をCIゲートとする。詳細は[`docs/api/python-contract.md`](api/python-contract.md#型ヒント必須)を正とする。本節では構文選択のみ補足する。

### Optional利用

- `typing.Optional[X]`ではなく、PEP 604構文`X | None`を使う（Python 3.12を前提とする[ADR-0001](adr/0001-python-packaging.md)により利用可能）。

### Union利用

- `typing.Union[X, Y]`ではなく`X | Y`を使う。
- 3値以上、かつ複数箇所で再利用される閉じた値集合は`Enum`、2値または単一箇所限定の値集合は`Literal`とする（[`docs/api/python-contract.md`](api/python-contract.md#enum利用方針)の判断基準をそのまま適用）。

## match文利用

- `match`-`case`文（PEP 634、Python 3.10+）は、Enum・`Literal`の値に基づく網羅的な分岐に使う（`if`/`elif`の連鎖より意図が明確な場合）。
- 網羅性を型チェッカーに保証させるため、`case _:`のフォールバックで`typing.assert_never()`を呼び出し、将来Enum/Literalに値が追加された際に型チェックが失敗するようにする。

## Pattern Matching利用

- `dataclass`のクラスパターン（例: `case PipelineEvent(event_type="failed"):`）による構造的な分岐は、複数の属性を同時に確認する場合に、個別の`isinstance`・属性アクセスの連鎖より優先する。
- 単一属性の単純な比較（`if x.status == "open":`）にまで`match`文を強制しない。過剰な適用は可読性を下げる。

## Context Manager利用

- 確保・解放が対になるリソース（SQLite接続、ファイルハンドル、トランザクション）は、必ずContext Manager（`__enter__`/`__exit__`）として実装する。
- `UnitOfWork`（[`docs/api/repositories.md`](api/repositories.md#unitofwork)）が正例であり、`__enter__`/`__exit__`と`commit()`/`rollback()`を持つ。

## with文利用

- `UnitOfWork`を含むContext Managerは、必ず`with`文を通じて使う。`__enter__()`/`__exit__()`を手動で呼び出さない。
- `with`文を使わない手動のtry/finally相当のリソース管理は、Context Manager化できない外部要因がある場合を除き行わない。

## async使用方針（現時点では使用しない理由を含む）

**本プロジェクトは現時点でasync/awaitを使用しない。**

理由:
1. 本プロジェクトは常時稼働サーバーを持たないバッチ実行モデルである（[ADR-0025](adr/0025-deployment-strategy.md)）。1プロセスが1回のジョブを同期的に処理して終了する構成であり、非同期処理が解決する「多数の同時リクエストをI/O待ちの間に切り替えて処理する」という課題がそもそも存在しない。
2. データストアであるSQLite（[ADR-0004](adr/0004-sqlite-as-datastore.md)）の標準ドライバ（`sqlite3`）は同期APIである。非同期化には`aiosqlite`等の追加依存が必要になり、対応する並行処理上の利益なしに依存を増やすことになる（[ADR-0001](adr/0001-python-packaging.md)の依存最小化方針に反する）。
3. PDF取得・FTP送信は低頻度・低並行度の処理であり、非同期I/Oによる並行実行の恩恵が乏しい。
4. 同期コードは非同期コードよりも読みやすく、10年規模の保守を前提とした本プロジェクトの「枯れた技術を選ぶ」方針（[ADR-0001](adr/0001-python-packaging.md)）に合致する。

**将来の見直し条件**: [`docs/constitution.md`](constitution.md)のEvolution Policyが示すReview UIのWeb化が実現し、常時稼働のWebプロセスが同時に多数のリクエストを処理する必要が生じた場合、そのコンポーネントに限定してasync/awaitの採用を新規ADRとして検討する。中核パイプライン（バッチ実行部分）の同期方針はその場合も維持する。

## Import順序

- 標準ライブラリ → サードパーティ → ファーストパーティ（`mod_personnel_db`）の順。各グループ内はアルファベット順。
- `ruff`の`isort`統合（[`pyproject.toml`](../pyproject.toml)の`[tool.ruff.lint.isort] known-first-party = ["mod_personnel_db"]`）で機械的に強制する。
- 絶対importを既定とする。相対importは、同一パッケージ内の隣接モジュール間に限り許容する。

## 循環参照禁止

パッケージ間の循環参照を禁止する。全21パッケージの依存グラフとその検証方法は[`docs/api/dependency-rule.md`](api/dependency-rule.md)・[`docs/api/import-graph.md`](api/import-graph.md)を正とする。実装着手時には`import-linter`等の静的解析ツールをCIに組み込み、機械的に強制することを推奨する（[`docs/api/dependency-rule.md`](api/dependency-rule.md#機械的な検証将来の推奨事項)）。

## Magic Number禁止

コード中に意味の説明されていない数値・文字列リテラルを埋め込まない。名前付き定数（本ドキュメントの「定数命名」節）として定義する。特に以下は、既存設計文書に登場する値であり、実装時にコード中へ直接埋め込まず、定数として1箇所に定義すること。

- Confidence band閾値（`0.85`, `0.5`、[`docs/database/json_schema.md`](database/json_schema.md#confidenceの算出ルール)）
- 関数サイズ制限（`30`文・`8`分岐等、[ADR-0014](adr/0014-development-discipline.md)。ただしこれらはlintルールの設定値であり、ランタイムコードの定数化対象ではない）
- リトライ回数・タイムアウト秒数（[`docs/workflow/state-machine.md`](workflow/state-machine.md#retry-policy)）

## 巨大Regex禁止

- ドメイン固有のパターン（階級名の表記ゆれ、組織名の略称等）をハードコードした正規表現を書かない。これは`Normalizer`が正規表現を持たないという構造的保証（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)）そのものである。
- 複数の選択肢（`|`）やlookaround等、可読性を大きく損なう複雑な正規表現が必要になった時点で、[ADR-0012](adr/0012-error-handling-priority-order.md)の優先順位に従い、`knowledge/`または`layouts/`への追加を検討する。正規表現の複雑さの増大は、Knowledge/Layoutへの移動を検討すべきシグナルとして扱う。
- 構造的な区切り（PDFのレイアウト由来の列・座標）は正規表現ではなく`layouts/`のレイアウト定義で表現する。

## print禁止

- `print()`を本番コード（`src/`配下）で使わない。デバッグ目的の一時的な`print()`もコミットしない。詳細は[`docs/api/python-contract.md`](api/python-contract.md#logging設計)を正とする。

## logging使用必須

- 標準ライブラリ`logging`の使用を必須とする。ログレベル・構造化ログ形式は[`docs/api/python-contract.md`](api/python-contract.md#logging設計)、運用面は[`docs/operations/observability.md`](operations/observability.md)を正とする。

## 関連ドキュメント

- [`docs/implementation.md`](implementation.md) — Implementation Guide（本ドキュメントが従属する上位文書）
- [`docs/api/python-contract.md`](api/python-contract.md) — Python Coding Contract（型・Protocol・例外・ログの詳細規約）
- [`docs/adr/0002-lint-format-typecheck-tooling.md`](adr/0002-lint-format-typecheck-tooling.md) — Lint/Format/型チェックツールの選定
- [`docs/adr/0014-development-discipline.md`](adr/0014-development-discipline.md) — 開発規律
- [`pyproject.toml`](../pyproject.toml) — Lint/型チェック設定の唯一の情報源
