# Configuration Architecture

> **本ドキュメントに実装（コード）はない。** 設定管理の設計のみを扱う。実装は`config/`パッケージ（[`docs/api/package-design.md`](api/package-design.md#config)）が担う。
>
> `config/`パッケージの型付き設定オブジェクトにPydantic Settingsを採用する決定そのものの背景・代替案・トレードオフは[ADR-0028](adr/0028-pydantic-settings-for-configuration.md)を正とする。本ドキュメントはその決定を前提に、Environment・Secret管理・Validation・Version・Migration・Hot Reloadという運用面の設計を行う。
>
> 本ドキュメントは[`docs/constitution.md`](constitution.md)に従属する。特に「Security by Default」（Core Principles）、「AIはKnowledgeを直接変更しない」等のAI Principlesとは独立した領域だが、矛盾する場合はConstitutionが優先される。

## 位置づけ

設定（Configuration）は、コードやKnowledge Baseとは異なる第4のレイヤーである。

- **コード（`src/`）**: どの環境でも同じロジック。
- **Knowledge Base（`knowledge/`）**: どの環境でも同じ値（階級名・組織名等のドメイン知識、[ADR-0005](adr/0005-knowledge-base-normalization.md)）。
- **データ（Gold Database等）**: 環境ごとに異なる実体を持つが、スキーマは同じ。
- **設定（`config/`）**: 環境ごとに異なる値そのもの（DB接続先、FTP接続先、ログレベル、しきい値等）。コードにもKnowledgeにも属さない。

設定値をコードにハードコードしないこと、Secretをリポジトリに含めないことは、[AGENTS.md](../AGENTS.md)の禁止事項および[ADR-0026](adr/0026-security-policy.md)の秘匿情報管理方針に既に定められている。本ドキュメントはその方針を「どう構造化するか」に具体化する。

## Environment

環境は4種類に固定する。

| Environment | 用途 | 実行主体 | データストア | 外部送信 |
|---|---|---|---|---|
| `dev` | ローカル開発・AIコーディングエージェントによる作業 | 開発者のローカル環境 | 使い捨てのSQLiteファイル（サンプルデータのみ） | 行わない（FTP送信は常に無効化） |
| `test` | CI（自動テスト・ゴールデンファイルテスト） | GitHub Actions（[ADR-0010](adr/0010-ci-cd-and-publish-strategy.md)） | 実行のたびに生成される一時SQLiteファイル | 行わない |
| `staging` | 本番相当の設定でのリハーサル実行（新様式・新Knowledgeの検証） | GitHub Actions（本番とは別のワークフロー/別のSecret） | 本番と分離した永続ストレージ | 行う場合は本番とは別の宛先（検証用FTP等）に限定 |
| `production` | 本番運用（実際の公開） | GitHub Actions（[ADR-0019](adr/0019-workflow-orchestration.md)のスケジュール実行） | 本番の永続ストレージ（[ADR-0018](adr/0018-pdf-registry-and-retention.md)） | 本番のFTP宛先（[ADR-0022](adr/0022-export-policy.md)のExport Policyに従う） |

- **決定方法**: 環境は単一の環境変数（例: `MOD_PERSONNEL_DB_ENVIRONMENT`）で明示的に指定する。デフォルト値は持たせない（未指定時はSettingsの読み込み自体を失敗させる）。「うっかり本番として動く」事故を、暗黙のデフォルトではなく明示必須にすることで防ぐ。
- **昇格順序**: `dev → test → staging → production`。設定値・Knowledge・Layoutの変更は、この順に検証されてから本番に反映されることを既定の運用とする（具体的なリリースフローは`CONTRIBUTING.md`・実装時のRunbookで定める）。
- **環境間の非対称性**: `production`と`staging`のみがFTP送信を行いうる。`dev`・`test`はSecretそのものを保持しない設計とし（後述「Secret管理」）、コード上の分岐ではなく「Secretが存在しないので送信できない」という構造的な制約で事故を防ぐ。

## Pydantic Settings

[ADR-0028](adr/0028-pydantic-settings-for-configuration.md)により、`config/`パッケージの`Settings`はPydantic Settings（`BaseSettings`）を用いて構造化する。

- **階層化**: `Settings`は単一のフラットな構造ではなく、関心事ごとにネストしたサブ設定（例: `DatabaseSettings`, `FtpSettings`, `LoggingSettings`, `WorkflowSettings`, `ObservabilitySettings`）を持つ。各サブ設定は、それぞれが対応する既存設計文書（`DatabaseSettings`なら[`docs/database/schema.md`](database/schema.md)、`ObservabilitySettings`なら[`docs/operations/observability.md`](operations/observability.md)）の運用パラメータ（しきい値・保持期間等）を型付きで表現する受け皿になる。
- **環境変数プレフィックス**: すべての環境変数に共通のプレフィックス（例: `MOD_PERSONNEL_DB_`）を付与し、ネストしたサブ設定は区切り文字（例: `MOD_PERSONNEL_DB_FTP__HOST`）で表現する。他システムの環境変数との衝突を防ぐため。
- **読み込み優先順位**: 明示的な環境変数 > 環境別`.env`ファイル（`.env.dev`, `.env.test`, `.env.staging`, `.env.production`）> コード上のデフォルト値。`production`・`staging`においてはデフォルト値を持つフィールドを極力持たせず、明示的な値の指定を必須にする（「本番でデフォルト値のまま動いていた」事故を防ぐ）。
- **`.env`ファイルの扱い**: `.env`・`.env.*`は`.gitignore`により既にGit管理対象外である。リポジトリにコミットするのは`.env.example`（キー名のみ、値はプレースホルダ）に限る。
- **不変性**: 読み込み後の`Settings`インスタンスは不変（frozen）として扱う。1回のプロセス実行（[ADR-0025](adr/0025-deployment-strategy.md)のバッチ実行モデルにおける1回分の起動）を通じて再代入しない。これは「Hot Reload」節の設計判断（後述）と直接結びつく。
- **合成ルートとの関係**: `Settings`の読み込みはプロセス起動直後、`cli/`（合成ルート、[`dependency-rule.md`](api/dependency-rule.md#合成ルートcomposition-root)）が最初に行う。`config/`パッケージ自身は`utils/`以外のいかなるパッケージにも依存せず（[`package-design.md`](api/package-design.md#config)）、読み込んだ`Settings`の**値**を`cli/`に返すのみで、具体的な`Repository`実装等の**組み立て（配線）**は行わない。この責務分離は[import-graph.md](api/import-graph.md)で検証済みの循環参照回避策と同一の設計原則に基づく。

## Secret管理

Secretは「設定値の一種だが、ログ・エラーメッセージ・Git履歴に一切現れてはならない値」として、通常の設定値と明確に区別する。

### GitHub Secrets

- CI/CD実行時（`test`/`staging`/`production`）のSecretは、GitHub Actions Secrets（[ADR-0019](adr/0019-workflow-orchestration.md)が既に前提とする秘密情報管理機構）に登録し、ワークフロー実行時に環境変数として注入する。
- 環境（`staging`/`production`）ごとに**別々の**GitHub Environmentを設定し、Secretのスコープを分離する。`production`用Secretへのアクセスは、それを必要とするワークフロー（定期実行・Export/公開ジョブ）のみに限定する。
- Secretのリポジトリへの誤コミットは、`.pre-commit-config.yaml`のgitleaks（[ADR-0026](adr/0026-security-policy.md)）で検知する。この既存の仕組みを変更しない。

### FTP Secret

- 公開成果物の配信（[ADR-0022](adr/0022-export-policy.md)のExport Policy）に用いるFTP接続情報（ホスト・ユーザー名・パスワードまたは鍵）は、`FtpSettings`のうち機密性を要するフィールドをPydantic Settingsの`SecretStr`型で表現する。`SecretStr`は文字列表現（`repr()`/`str()`）が既定でマスクされるため、構造化ログ（[`docs/operations/observability.md`](operations/observability.md#logging)）に`Settings`オブジェクトの内容を誤って丸ごと出力しても、値そのものは漏えいしない。
- `dev`・`test`環境では、FTP Secretのフィールドを`None`（未設定）として扱い、Export処理側は「FTP Secretが存在しない場合は送信ステップをスキップする」という構造的な制約を持つ（コード上の環境分岐ではなく、値の有無で自然に安全側に倒れる設計）。
- FTP Secretのローテーション（定期的な認証情報の更新）は、GitHub Secrets側の値を更新するのみで、コード・`Settings`の構造自体は変更を要しない設計とする。ローテーション自体の運用手順（頻度・手順書）は、実装着手後に`docs/operations/`のRunbookとして具体化する。

## Validation Rule

Pydantic Settingsのバリデーションは、プロセス起動時の一度限りの検証として実行し、以降のパイプライン実行中に設定起因のエラーが後から発覚することを防ぐ（fail-fast）。

- **型・必須項目**: 各フィールドの型強制（文字列→数値・真偽値・URL等）と必須項目の欠落は、Pydantic Settingsの標準機能でそのまま検証する。
- **環境間の相互依存ルール**（クロスフィールド検証。標準の型検証では表現できないため、`Settings`側にバリデータとして明示する）:
  - `environment`が`staging`または`production`の場合、`FtpSettings`のSecretフィールドが設定されていることを必須とする（欠落時は起動時エラー）。
  - `environment`が`dev`または`test`の場合、`FtpSettings`のSecretフィールドは未設定でなければならない（誤って本番Secretを開発環境に紛れ込ませる事故を、値の存在自体をエラーにすることで防ぐ）。
  - `DatabaseSettings`が指すSQLiteファイルパスは、`production`では[ADR-0018](adr/0018-pdf-registry-and-retention.md)の永続ストレージ配下であることを要求し、一時ディレクトリ等の揮発性パスを許容しない。
- **失敗時の挙動**: Validation失敗時はプロセスを即座に終了させ、パイプライン実行（`jobs`テーブルへのINSERT）を開始しない。中途半端な設定で実行を開始し、途中で失敗するより安全である。
- **Secretの値そのものは検証ログに出力しない**: 必須項目の欠落は「フィールド名が未設定」というメタ情報のみをエラーメッセージに含め、値（あるいは他フィールドの値の一部）を含めない。

## 設定Version

[`docs/database/json_schema.md`](database/json_schema.md#バージョン管理)が定める3層のバージョン管理（DBスキーマバージョン／データ生成バージョン／公開JSON形式バージョン）に、第4層として**設定スキーマバージョン**を追加する。

| 層 | 対象 | 管理方法 |
|---|---|---|
| 1. DBスキーマバージョン | SQLiteの表構造そのもの | `schema_migrations`テーブル + `PRAGMA user_version`（[`schema.md`](database/schema.md#バージョン管理)） |
| 2. データ生成バージョン | どのコード・知識ベースでデータが生成されたか | `parser_versions.code_version`（[ADR-0023](adr/0023-parser-versioning-policy.md)） |
| 3. 公開JSON形式バージョン | 外部公開インターフェースの契約そのもの | [`json_schema.md`](database/json_schema.md#バージョン管理)のSemVer管理 |
| 4. **設定スキーマバージョン**（本ドキュメント） | `Settings`のフィールド構成そのもの（環境変数のキー名・必須/任意の別・ネスト構造） | 本節で定義 |

この4層は互いに独立して変化する。設定に新しいフィールドを1つ追加しても、DBスキーマや公開JSON形式には影響しない。

- **管理方法**: 設定スキーマバージョンもSemVer（`MAJOR.MINOR.PATCH`）で管理し、`config/`パッケージ内の定数として保持する。
  - **MAJOR**: 既存の環境変数キーの削除・改名・必須化（後方互換を壊す変更）。
  - **MINOR**: 任意項目（デフォルト値を持つフィールド）の追加。
  - **PATCH**: バリデーションルールの文言修正等、構造に影響しない変更。
- **来歴との関連**: `Settings`自体は`jobs`テーブルの行として永続化されないが、実行時に読み込んだ設定スキーマバージョンを`jobs.error_summary`とは別に将来的な来歴フィールドとして残せるよう、既存の`jobs`テーブル・`parser_versions`テーブルへの列追加は、必要になった時点で新規ADR・マイグレーションとして検討する（本ドキュメントでは`docs/database/schema.md`の既存テーブル定義自体は変更しない。スコープ外）。

## Migration

設定スキーマの変更は、Knowledgeのバージョニング・再処理（[ADR-0024](adr/0024-knowledge-versioning-and-backfill.md)）と同様に、「後方互換を保ちながら段階的に移行する」ことを既定の方針とする。

- **キーの改名・削除**: 環境変数キーを改名・削除する場合、旧キーを直ちに削除せず、少なくとも1つのMINORリリースの間は旧キーも読み込み可能にし、旧キー使用時にWARNINGログ（[`docs/operations/observability.md`](operations/observability.md#logging)のログレベル指針）を出力する「非推奨期間」を設ける。非推奨期間の終了とともに、旧キーの削除をMAJORバージョンとしてリリースする。
- **新規必須フィールドの追加**: 新しい必須フィールドを追加する場合、`staging`環境で先に検証してから`production`へのSecret/環境変数登録を行う（「Environment」節の昇格順序に従う）。必須フィールドの追加そのものはMAJOR相当の変更として扱う。
- **Migrationの記録**: 設定スキーマバージョンの変更履歴は、DBマイグレーション（`schema_migrations`テーブル）とは別に、`config/`パッケージのCHANGELOG相当の記録（実装時に具体化）として残す。DBスキーマと設定スキーマを同じ台帳で管理すると、両者が独立して変化するという前提（本ドキュメント冒頭）と矛盾するため、意図的に分離する。
- **既存環境への適用**: `production`の設定変更は、[ADR-0014](adr/0014-development-discipline.md)の1PR1責務の原則に従い、設定スキーマの変更（コード側）とGitHub Secrets/環境変数の実際の値の更新（運用側の作業）を、可能な限り同一のリリース手順内で対にして扱う。値の更新を伴わないスキーマ変更のマージだけでは、`production`環境が新しい必須フィールドの欠落により起動できなくなる場合があるため、リリース手順（非推奨期間中の並行稼働、または値更新の事前完了）を厳守する。

## Hot Reload可否

**不可（Hot Reloadは採用しない）。**

- 本プロジェクトは常時稼働サーバーを持たないバッチ実行モデルである（[ADR-0025](adr/0025-deployment-strategy.md)）。1回のプロセス起動が1回のジョブ実行に対応し、処理が終わればプロセスは終了する。「稼働中のプロセスに対して、再起動なしに設定を反映する」というHot Reloadが解決する問題（長時間稼働するプロセスの可用性を保ったまま設定を更新したい）が、そもそもこの実行モデルには存在しない。
- 設定変更を反映したい場合は、次回のプロセス起動（次回のスケジュール実行、または手動トリガー）を待てばよく、新しいプロセスは起動時に新しい`Settings`を読み込む。これは追加の実装を要さない、実行モデルから自然に得られる性質である。
- 「Pydantic Settings」節で述べた`Settings`インスタンスの不変性（frozen）は、この判断と整合する。1プロセスの生存期間中に`Settings`が変化しないことを前提にできるため、パイプラインの各段階（[`pipeline.md`](api/pipeline.md)の`PipelineStage`）は、実行途中で設定値が変わりうることを考慮した防御的な実装を持つ必要がない。
- **将来の見直し条件**: [`docs/constitution.md`](constitution.md)のEvolution Policyが示す「Review UIをWeb化可能」という方向性が実現し、常時稼働のWebプロセスが導入される場合、そのプロセスに限ってはHot Reloadの要否を新規ADRとして再検討する。ただし、その場合も中核パイプライン（バッチ実行）側の`Settings`不変性の方針は変更しない。

## 関連ADR・ドキュメント

- [ADR-0001](adr/0001-python-packaging.md) — Pythonパッケージング。依存最小化方針。
- [ADR-0002](adr/0002-lint-format-typecheck-tooling.md) — Lint/Format/型チェックツールの選定。
- [ADR-0014](adr/0014-development-discipline.md) — 開発規律（1PR1責務）。Migration節の運用に関連。
- [ADR-0018](adr/0018-pdf-registry-and-retention.md) — PDF Registry・長期保管方針。永続ストレージパスの検証ルールに関連。
- [ADR-0019](adr/0019-workflow-orchestration.md) — 実行オーケストレーション戦略。GitHub Actions Secrets・環境ごとのワークフロー分離の前提。
- [ADR-0022](adr/0022-export-policy.md) — Export Policy。FTP送信の宛先・許可範囲。
- [ADR-0023](adr/0023-parser-versioning-policy.md) — Parserバージョニング方針。設定Version節の4層モデルの前例。
- [ADR-0024](adr/0024-knowledge-versioning-and-backfill.md) — Knowledgeバージョニング・再処理方針。Migration節の後方互換方針の前例。
- [ADR-0025](adr/0025-deployment-strategy.md) — デプロイメント戦略。バッチ実行モデル。Hot Reload不採用の直接の根拠。
- [ADR-0026](adr/0026-security-policy.md) — セキュリティポリシー。Secret管理の上位方針。
- [ADR-0028](adr/0028-pydantic-settings-for-configuration.md) — 設定管理へのPydantic Settings採用（本ドキュメントが前提とする技術選定の決定）。
- [`docs/api/package-design.md`](api/package-design.md#config) — `config/`パッケージの責務・依存禁止ルール。
- [`docs/api/python-contract.md`](api/python-contract.md#pydantic利用可否) — Pydantic利用可否の全体方針（`models/`は不採用、`config/`はADR-0028により例外）。
- [`docs/api/dependency-rule.md`](api/dependency-rule.md#合成ルートcomposition-root) — 合成ルート（`cli/`）と`config/`の関係。
- [`docs/database/json_schema.md`](database/json_schema.md#バージョン管理) — 3層バージョン管理（設定Version節が第4層として拡張する対象）。
- [`docs/operations/observability.md`](operations/observability.md) — Logging方針（Secretの誤出力防止と関連）。
- [`docs/constitution.md`](constitution.md) — Core Principles「Security by Default」。本ドキュメント全体が従属する上位方針。
