# Python Coding Contract

> 実装着手時に従うべきコーディング規約。本ドキュメント自体はコードを含まない（方針決定のみ）。個別のルールは既存ADR（[ADR-0002](../adr/0002-lint-format-typecheck-tooling.md), [ADR-0014](../adr/0014-development-discipline.md)）と`pyproject.toml`の設定を土台とし、本タスクで要求された8項目について、この設計フェーズで初めて明文化する追加の規約を定める。

## 型ヒント必須

- すべての公開関数・メソッド（`interfaces.md`, `repositories.md`, `pipeline.md`で定義したもの全て）は、引数・戻り値に完全な型ヒントを付与する。
- `mypy --strict`（[ADR-0002](../adr/0002-lint-format-typecheck-tooling.md)、`pyproject.toml`の`[tool.mypy] strict = true`）を実装時のCIゲートとする。`# type: ignore`は原則禁止とし、やむを得ず使う場合は理由をコメントで明記する。
- `Any`型の使用は、外部ライブラリの型スタブが存在しない境界（例: PDFパースライブラリの戻り値）に限定し、`models/`・`repositories/`・`pipeline/`の公開APIには登場させない。

## Protocol利用方針

- **`typing.Protocol`を、構造的部分型（duck typing）で表現できるすべての契約に使う。** 本設計フェーズで定義した`PipelineStage`, `Repository`系（8種）, `UnitOfWork`, `ReviewService`等のサービスインターフェース（[`interfaces.md`](interfaces.md), [`repositories.md`](repositories.md), [`pipeline.md`](pipeline.md)）はすべてProtocolとする。
- **理由**: (1) 実装クラスが明示的に継承する必要がなく、テスト用のモック実装が書きやすい。(2) `repositories/sqlite/`と将来の`repositories/postgres/`が、共通の基底クラスを持たずに同じ契約を満たせる（[`repositories.md`](repositories.md)のSQLite非依存の要件と直結）。

## ABC利用方針

- **`abc.ABC`は、複数の具象実装間で共有したい部分実装（テンプレートメソッド）がある場合にのみ使う。** 公開契約（Protocol）とは別の、実装の詳細に属する。
- 想定される利用例: `repositories/sqlite/`内部で、8つのSQLite実装が共有する接続管理・トランザクション処理を、`SqliteRepositoryBase(ABC)`のようなクラスに切り出す（`repositories/`の公開Protocolとは独立した、`repositories/sqlite/`パッケージ内部だけの実装詳細）。
- **Protocolとの使い分けの基準**: 「他パッケージから見た契約」はProtocol、「同一パッケージ内の実装の再利用」はABC。

## dataclass利用方針

- [`models.md`](models.md)の全モデル・値オブジェクトは`@dataclass(frozen=True, slots=True)`とする。
  - `frozen=True`: 生成後に変更不可（本プロジェクト全体の「削除せず追記する」設計思想、[ADR-0006](../adr/0006-pipeline-provenance.md)と対応。値を変えたい場合は新しいインスタンスを作る）。
  - `slots=True`: メモリ効率と、意図しない属性追加の防止（タイプミスの早期検出、[CLAUDE.md](../../CLAUDE.md)の「正しさより先に、間違いに気づける設計」）。
- 検証ロジック（[`models.md`](models.md)の「Validation Rule」節）は`__post_init__`で実施する想定とし、違反時は例外設計（後述）に従った専用例外を送出する。

## Pydantic利用可否

**不採用。** 内部ドメインモデル（`models/`）は標準ライブラリの`dataclasses`のみで表現する。

**理由**:
1. 本プロジェクトは既に外部境界のバリデーションに`jsonschema`（Draft 2020-12）を採用済みである（[`docs/database/json_schema.md`](../database/json_schema.md), [`docs/knowledge/schema.md`](../knowledge/schema.md)）。Pydanticを追加すると、JSON Schemaベースの検証とPydanticベースの検証という**2つの並行するバリデーション手段**が生まれ、[ADR-0001](../adr/0001-python-packaging.md)の依存最小化方針に反する。
2. `models/`は`repositories/`を経由してのみ永続化されるパイプライン内部の値オブジェクトであり、Pydanticが得意とする「外部入力（HTTPリクエスト等）の受け口でのパース＋検証」という用途に本質的に該当しない。
3. `frozen=True`のdataclassで十分に不変性を表現でき、追加の依存を正当化する理由がない。

**外部境界（`knowledge/`のYAMLロード、公開JSONの生成）では、既存方針どおり`jsonschema`ライブラリを使い続ける**（Pydanticではなく）。将来、実装を進める中でPydanticが真に必要な理由（例: 高性能な大量データのシリアライズ）が生じた場合は、新規ADRとして再検討する。

**例外（`config/`パッケージ境界）**: [ADR-0028](../adr/0028-pydantic-settings-for-configuration.md)により、`config/`パッケージの設定オブジェクト（環境変数・`.env`ファイルという外部入力の受け口）に限り、Pydantic Settingsの採用を決定している。これは本節の決定（`models/`へのPydantic不採用）を覆すものではなく、適用範囲を`config/`境界に限定した別決定である。詳細は[`docs/configuration.md`](../configuration.md)を参照。

## Enum利用方針

- DBの`CHECK`制約（[`docs/database/schema.md`](../database/schema.md)）で表現された閉じた値集合（`pipeline_stage`, `error_category`, `status`系, `category`, `service_branch`等）は、Pythonコード上で`enum.StrEnum`（[`models.md`](models.md)の`LearningStatus`参照）として表現する。
- **`enum.StrEnum`を正式採用する（[ADR-0030](../adr/0030-strenum-adoption.md)）**。従来は「文字列としてシリアライズされる必要があるものは`str, Enum`の多重継承」としていたが、Phase2 Task2の実装で`str, Enum`多重継承が(1) `ruff`のUP042（`enum.StrEnum`への置き換え推奨、`pyproject.toml`が対象Pythonバージョンを3.14としているため常に発火する）、(2) `mypy --strict`での`Enum`メンバーと文字列リテラルの比較に対する`comparison-overlap`警告、という2つの機械的な摩擦を生むことが判明したため、`enum.StrEnum`（Python 3.11+で利用可能、本プロジェクトはPython 3.14を対象とするため利用可能）に統一した。`str, Enum`の多重継承は今後使用しない。
- **同期の規律**: `models/`のEnum定義と、対応するSQLの`CHECK (... IN (...))`制約は、常に同じ値集合を持たなければならない。値集合を変更する場合は、両方を同一PRで更新する（[ADR-0014](../adr/0014-development-discipline.md)の1PR1責務の例外として、「同じ制約の二重表現の同期」は1つの責務とみなす）。将来、この重複自体を解消する自動生成の仕組み（DDLからEnumを生成する等）を検討してもよいが、V2.0インターフェース設計の時点では手動同期とする。
- 単純な真偽的分岐（例: `status: Literal["passed", "failed"]`のような2値）は、`Enum`ではなく`typing.Literal`で表現してよい（[`models.md`](models.md)の`ValidationResult.status`, `CandidateRecord.validation_status`等）。**目安**: 3値以上、かつ複数箇所で再利用される値集合は`Enum`、2値または単一箇所限定の値集合は`Literal`。
- **既存のRepository実装との関係**: `KnowledgeItem.category`, `PdfRecord.status`, `Job.job_type`/`status`, `ExportRecord.format`, `CandidateRecord.validation_status`は、この基準を満たすEnum候補だが、`repositories/sqlite/`が既にDBの生の`str`値を直接読み書きしており、Enum化にはRepository側の読み取り時変換（DB文字列→Enumインスタンス）が必要になる。この変換は実装時に対応するRepositoryの変更と同一PRで行うこと（[ADR-0030](../adr/0030-strenum-adoption.md)）。

## 例外設計

```python
class MODPersonnelDBError(Exception):
    """本プロジェクトの全カスタム例外の基底クラス。"""


class RepositoryError(MODPersonnelDBError):
    """Repository層での永続化エラー（接続断・整合性制約違反等）の基底クラス。"""


class KnowledgeLoadError(MODPersonnelDBError):
    """knowledge/ のファイル読み込み・スキーマ検証エラー。"""


class ValidationBlockedError(MODPersonnelDBError):
    """Validatorの実行に必要なValidationRuleSetが取得できない等、検証自体を実行できない場合。
    ValidationResult.status='failed'（検証した結果NG）とは異なる。"""
```

`PipelineException`（[`pipeline.md`](pipeline.md)）は`MODPersonnelDBError`を継承する、パイプライン実行文脈に特化した例外である。

- **方針**:
  - 標準の`Exception`を直接`raise`しない。必ず`MODPersonnelDBError`の派生クラスを使う。
  - 例外を握りつぶさない。再送出する場合は`raise NewError(...) from original_error`で原因を保持する（[ADR-0006](../adr/0006-pipeline-provenance.md)の来歴思想を例外の因果関係にも適用する）。
  - `pipeline/`（`JobRunner`）は`PipelineException`を捕捉して1件のPDF・1件のレコードの失敗として処理を継続し、他の処理に波及させない（[ADR-0019](../adr/0019-workflow-orchestration.md)）。それ以外の未分類の例外（`MODPersonnelDBError`の派生でないもの）は、想定外のバグとして再送出しジョブ全体を失敗させる。

## Logging設計

- 標準ライブラリの`logging`モジュールを使う。`print()`は本番コードに使わない。
- 各モジュールは`logging.getLogger(__name__)`でロガーを取得する（モジュール単位の粒度）。
- ログ出力形式は構造化ログ（JSON Lines、[`logs/README.md`](../../logs/README.md)の方針）とする。すべてのパイプライン関連ログには`PipelineContext.correlation_id`（[`pipeline.md`](pipeline.md)）を含め、1回の実行に属するログを横断的に追跡可能にする。
- ログレベルの指針:
  - `DEBUG`: 各Stageの入出力の詳細（開発・障害調査用、本番の既定では無効）
  - `INFO`: `PipelineEvent`に対応する開始・完了イベント
  - `WARNING`: `ValidationResult`の`severity="warning"`違反、リトライ発生等
  - `ERROR`: `PipelineException`捕捉、Repository層のエラー
- **個人情報の扱い**: ログに氏名等の個人情報を出力する場合は、公開JSON（[ADR-0016](../adr/0016-public-json-format.md)）で既に公開が許容される範囲を超えないこと（[ADR-0008](../adr/0008-data-ethics-policy.md)）。DEBUGログであっても無制限に個人情報を書き出さない。
