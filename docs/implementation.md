# Implementation Guide

# 目的

本ドキュメントは実装フェーズにおける最上位ガイドラインである。設計フェーズ（[`docs/design-freeze.md`](design-freeze.md)）は完了しており、これ以降のすべての実装判断は、以下の優先順位に従う。

```
Constitution
  ↓
ADR
  ↓
Architecture Contract
  ↓
Implementation Guide（本ドキュメント）
```

上位の文書と本ドキュメントの記述が矛盾する場合、常に上位の文書が優先される。本ドキュメントは新しい設計判断を行う文書ではなく、[`docs/constitution.md`](constitution.md)・既存29本のADR（[`docs/adr/`](adr/)）・[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)・[`docs/api/python-contract.md`](api/python-contract.md)が既に決定した内容を、実装者（人間・Claude Code問わず）が迷わず適用できる形に集約したものである。個々のルールの詳細な根拠は、各節がリンクする元の文書を正とし、本ドキュメントで重複させない。

対象読者は、実装フェーズに参加するすべての人間の開発者・Claude Code・CI/CDである。

## Implementation Philosophy

本プロジェクトの実装は、「動くコードを書く」ことではなく「10年後も安全に変更できるコードを書く」ことを目的とする（[`docs/constitution.md`](constitution.md)のVision）。以下の8つの「〜First」原則・規律が、この目的を具体的な実装判断へと変換する。いずれも[`docs/constitution.md`](constitution.md)のCore Principles / Architecture Principlesの実装フェーズにおける適用形であり、新しい原則を追加するものではない。

## Repository First

永続化を必要とする新しい機能を実装する前に、対応するRepository Protocol（[`docs/api/repositories.md`](api/repositories.md)の8種、または既存の拡張）が要求を満たしているかを確認する。既存Protocolで表現できない永続化要求が見つかった場合、SQLの実装（`repositories/sqlite/`）を書く前に、Protocol定義（`repositories/`の抽象）を更新する。「まずSQLを書いて、後からインターフェースに合わせる」順序を禁止する。これはArchitecture Principlesの「Repository Pattern」（[`docs/constitution.md`](constitution.md)）を、実装の作業順序として具体化したものである。

## Interface First

パイプライン段階・サービス（[`docs/api/interfaces.md`](api/interfaces.md)の15コンポーネント）の実装は、公開契約（`Protocol`定義）を先に確定し、レビューを経てから内部実装に着手する。契約が先になければ、複数のコンポーネントが並行して開発できず、モックによるテストも書けない。[`docs/constitution.md`](constitution.md)のArchitecture Principle「Interface First」の実装フェーズにおける適用。

## Domain First

技術的な実装手段（どのライブラリを使うか等）より先に、扱う対象（`models/`のドメインモデル、[`docs/api/models.md`](api/models.md)の13種）の意味を確定する。新しいフィールド・新しいモデルが必要になった場合、まず`docs/api/models.md`または対応するADRを更新し、ドメインの理解を文書として固めてからコードに反映する。

## Knowledge First

未知のパターン（表記ゆれ・組織名・様式）に遭遇した場合の対応優先順位は、[ADR-0012](adr/0012-error-handling-priority-order.md)が定める「Knowledge Base追加 > Layout追加 > `src/`内の例外処理」を厳守する。この優先順位についての実装固有の詳細は[`docs/parser-guidelines.md`](parser-guidelines.md)を参照。

## Review First

`gold_records`への書き込みは、`ReviewDecision`（[`docs/review/domain.md`](review/domain.md)）を経由する以外の経路を実装しない。これはArchitecture Contractの保証8・9（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)）であり、実装上は`GoldRepository`への書き込み呼び出しを`review/`パッケージ以外から行わないことで担保する（[`docs/api/dependency-rule.md`](api/dependency-rule.md)）。「レビューを経ずに一時的にデータを流し込む」ためのバックドア・デバッグ用の直接書き込み経路を、たとえ開発中であっても実装しない。

## Small Commit

1つのコミットは、それ単独でビルド・型チェックが通る一貫した単位とする。「作業途中の壊れた状態」のコミットを積み重ねない。コミットメッセージは[Conventional Commits](https://www.conventionalcommits.org/)（[`CONTRIBUTING.md`](../CONTRIBUTING.md)）に従う。1コミットが複数の無関係な変更を含む場合は分割する。

## Small Pull Request

1つのPull Requestは1つの責務のみを変更する（[ADR-0014](adr/0014-development-discipline.md)、[`CONTRIBUTING.md`](../CONTRIBUTING.md)）。詳細な運用は「Pull Request Rule」節を参照。

## 100% Type Hints

すべての公開関数・メソッドは、引数・戻り値に完全な型ヒントを付与する。`mypy --strict`をCIゲートとする。詳細規約は[`docs/api/python-contract.md`](api/python-contract.md#型ヒント必須)を正とする。

## No Business Logic in Repository

Repository実装（`repositories/sqlite/`）は、永続化されたデータへのCRUD・クエリ変換のみを行い、ドメイン判断（Confidenceの算出、Validation合否の判定、Knowledge適用の要否判断等）を含めない。これらの判断は`services/`・`pipeline/`・`review/`等の呼び出し元が行い、Repositoryにはその結果（値）のみを渡す。[`docs/api/repositories.md`](api/repositories.md#sqlite非依存を実現する設計原則)の「SQLite非依存を実現する設計原則」を、ロジックの置き場所という観点から補足する規約である。Repositoryのメソッドに`if`文がドメイン判断のために現れた場合は、設計違反の兆候として扱う。

## No SQLite Dependency Outside Infrastructure

`repositories/sqlite/`（インフラストラクチャ層）以外のいかなるパッケージも、`sqlite3`モジュールおよびSQLite固有の型・エラーを直接importしない。合成ルート（`cli/`、後述）のみが`repositories/sqlite/`を具体的にimportして構築する例外を持つ。詳細な依存グラフは[`docs/api/dependency-rule.md`](api/dependency-rule.md)を正とする。

## Dependency Inversion

上位の方針（`pipeline/`, `review/`, `services/`）は、下位の実装詳細（`repositories/sqlite/`）に直接依存せず、共有された抽象（`repositories/`のProtocol）に依存する。[`docs/api/dependency-rule.md`](api/dependency-rule.md)の全パッケージ依存グラフ（21ノード・47エッジ、循環参照なしを検証済み、[`docs/api/import-graph.md`](api/import-graph.md)）がこれを構造的に強制する。

## Composition Root

実行時にどのRepository実装（SQLite/将来のPostgreSQL）を使うかを決定し、`UnitOfWork`を組み立てて注入する箇所は`cli/`のみである。他のいかなるパッケージにもこの配線責務を持たせない。詳細は[`docs/api/dependency-rule.md`](api/dependency-rule.md#合成ルートcomposition-root)を正とする。

## Protocol First

コンポーネント間の契約（他パッケージから見た公開API）は`typing.Protocol`で表現する。`ABC`は同一パッケージ内部の実装再利用にのみ使う。判断基準・具体例は[`docs/api/python-contract.md`](api/python-contract.md#protocol利用方針)を正とする。

## ABC利用方針

複数の具象実装間で共有する部分実装（テンプレートメソッド）がある場合にのみ`abc.ABC`を使う。詳細は[`docs/api/python-contract.md`](api/python-contract.md#abc利用方針)を正とする。

## dataclass利用方針

`models/`の全モデル・値オブジェクトは`@dataclass(frozen=True, slots=True)`とする。詳細は[`docs/api/python-contract.md`](api/python-contract.md#dataclass利用方針)を正とする。

## Pydantic利用方針

`models/`にはPydanticを採用しない。`config/`パッケージ境界に限り、Pydantic Settingsを採用する（[ADR-0028](adr/0028-pydantic-settings-for-configuration.md)）。詳細は[`docs/api/python-contract.md`](api/python-contract.md#pydantic利用可否)・[`docs/configuration.md`](configuration.md)を正とする。この境界を実装時に拡大しない。

## Logging Rule

標準ライブラリの`logging`を使い、`print()`は本番コードに使わない。ログレベル・構造化ログ形式・個人情報の扱いは[`docs/api/python-contract.md`](api/python-contract.md#logging設計)を正とし、運用面（保存先・保持期間・相関ID）は[`docs/operations/observability.md`](operations/observability.md)を正とする。

## Exception Rule

すべてのカスタム例外は`MODPersonnelDBError`を継承する。標準の`Exception`を直接`raise`しない。例外を握りつぶさず、再送出時は`raise ... from ...`で原因を保持する。詳細な例外階層は[`docs/api/python-contract.md`](api/python-contract.md#例外設計)を正とする。

## Version Rule

本プロジェクトは複数の独立したバージョン軸を持つ。実装時に、これらを混同・省略しないこと。

| バージョン軸 | 管理方法 | 正となる文書 |
|---|---|---|
| DBスキーマバージョン | `PRAGMA user_version` + `schema_migrations` | [`docs/database/schema.md`](database/schema.md#バージョン管理) |
| Parserバージョン（データ生成バージョン） | リリースタグ（SemVer） | [ADR-0023](adr/0023-parser-versioning-policy.md) |
| 公開JSON形式バージョン | `schema_version`フィールド（SemVer） | [`docs/database/json_schema.md`](database/json_schema.md#バージョン管理) |
| 設定スキーマバージョン | `config/`パッケージ内定数（SemVer） | [`docs/configuration.md`](configuration.md#設定version) |
| Knowledgeバージョン（エントリ単位） | `VersionInfo`（`version`/`updated_at`） | [`docs/knowledge/schema.md`](knowledge/schema.md) |

これら5つの軸は互いに独立して変化する。あるコード変更が複数の軸に影響する場合、それぞれを個別に更新する。

## Parser Rule

Parser（中核パイプラインの`document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`各パッケージ）固有の規約は、専用文書[`docs/parser-guidelines.md`](parser-guidelines.md)を正とする。要点のみ再掲する: Parserは`Repository`・SQLite・FTP・JSON・Reviewのいずれも知らず、公開APIは`run()`のみである。

## Layout Rule

PDFレイアウト依存の値（座標・列位置・見出し文字列等）を`src/`内のPythonコードに直接埋め込まない。必ず`layouts/`のレイアウト定義を経由する（[ADR-0003](adr/0003-layout-definition-strategy.md)、[`CLAUDE.md`](../CLAUDE.md)）。新様式追加時の詳細手順は[`docs/parser-guidelines.md`](parser-guidelines.md)・[`docs/operations/release.md`](operations/release.md#parser-upgrade)を参照。

## Knowledge Rule

階級名の表記ゆれ・組織名の改称履歴・氏名の異体字等のドメイン知識は`src/`のロジックではなく`knowledge/`のデータとして表現する（[ADR-0005](adr/0005-knowledge-base-normalization.md)、8カテゴリ、[`docs/knowledge/schema.md`](knowledge/schema.md)）。`knowledge/`配下のデータを一括置換・自動生成で書き換えない（[`CLAUDE.md`](../CLAUDE.md)）。AIコーディングエージェントはKnowledgeを直接変更せず、提案のみを行う（[`docs/constitution.md`](constitution.md)のAI Principles）。

## Review Rule

`ReviewDecision`が`Approved`状態を作る唯一の手段である（[`docs/review/policy.md`](review/policy.md)）。レビュー担当者の承認権限・差戻し・再レビュー・Confidence Override・Knowledge追加条件・Gold更新条件の7ポリシーは[`docs/review/policy.md`](review/policy.md)を正とする。

## Testing Rule

各テスト種別（Unit/Integration/Golden/Regression/Performance/Acceptance/Benchmark/Mutation）の目的・実行タイミング・成功条件・Coverage目標は、専用文書[`docs/testing/test-policy.md`](testing/test-policy.md)を正とする。新機能には対応するテストを追加し、パーサー関連の変更には可能な限りゴールデンファイルテストを追加する（[`CONTRIBUTING.md`](../CONTRIBUTING.md)）。

## Code Review Rule

- `CODEOWNERS`に基づくレビュー担当者の承認を得る（[`CONTRIBUTING.md`](../CONTRIBUTING.md)）。
- データモデル・レイアウトフォーマット・ドメイン知識のスキーマに影響する変更は、最低1名の追加レビューを必須とする。
- **AIコーディングエージェントが生成したコードも、人間によるコードレビューを必ず経る**（[`docs/constitution.md`](constitution.md)のAI Principles「AIは提案者、人間は承認者」）。AI生成であることはレビュー省略の理由にならない。
- レビュー観点は、機能の正しさだけでなく、本ドキュメントおよび[`docs/coding-style.md`](coding-style.md)の規約遵守を含む。

## Pull Request Rule

- `.github/PULL_REQUEST_TEMPLATE.md`に従って記述する（[`CONTRIBUTING.md`](../CONTRIBUTING.md)）。
- 関連ADRへのリンクを含める。新規ADRが必要な変更は、実装着手前にADRを追加してからPRを作成する。
- 1つのPRは1つの責務のみを変更する（[ADR-0014](adr/0014-development-discipline.md)）。
- CI（lint・型チェック・テスト）がグリーンであることを確認する。
- 詳細な流れは[`docs/developer-workflow.md`](developer-workflow.md)を参照。

## Definition of Done

ある変更が「完了」したとみなすための必要条件を以下に列挙する。1つでも欠けている場合は未完了として扱う。

1. コードが実装され、`mypy --strict`・`ruff`のチェックを通過している。
2. 対応するテスト（該当する種別は[`docs/testing/test-policy.md`](testing/test-policy.md)を参照）が追加され、CIでグリーンである。
3. 影響するドキュメント（`docs/`配下、モデル・API定義を含む）が更新されている。
4. Architecture Contract（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)）のいずれの保証も侵害していない。
5. データモデル・パイプライン構成・技術選定に関わる変更の場合、対応するADRが存在する。
6. `CODEOWNERS`に基づくレビューを経て承認されている。
7. `main`へのマージ後、CI/CDパイプライン（[`docs/developer-workflow.md`](developer-workflow.md)）が正常に完了する。

具体的なチェック項目は[`docs/implementation-checklist.md`](implementation-checklist.md)を参照。

## 関連ドキュメント

- [`docs/constitution.md`](constitution.md) — Project Constitution（最高位）
- [`docs/adr/`](adr/) — Architecture Decision Records
- [`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md) — Architecture Contract
- [`docs/coding-style.md`](coding-style.md) — Coding Style Guide
- [`docs/testing/test-policy.md`](testing/test-policy.md) — Test Policy
- [`docs/parser-guidelines.md`](parser-guidelines.md) — Parser Development Guidelines
- [`docs/implementation-checklist.md`](implementation-checklist.md) — Implementation Checklist
- [`docs/developer-workflow.md`](developer-workflow.md) — Developer Workflow
- [`docs/design-freeze.md`](design-freeze.md) — Design Freeze Review
