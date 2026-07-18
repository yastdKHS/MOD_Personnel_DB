# Security Architecture

> **本ドキュメントに実装（コード）はない。** セキュリティ設計のみを扱う。方針決定の根拠は[ADR-0026](adr/0026-security-policy.md)（セキュリティポリシー全般）・[ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md)（公開成果物の完全性保証と監査ログ方針）を正とする。本ドキュメントはこの2つのADRが定めた決定を、脅威モデルとして構造化し、各対策領域（Secret・Supply Chain・GitHub Actions等）の設計として具体化するものであり、ADRの決定内容を変更しない。
>
> 本ドキュメントは[`docs/constitution.md`](constitution.md)のCore Principles「Security by Default」に従属する。矛盾する場合はConstitutionが優先される。

## 前提

本プロジェクトは常時稼働サーバーを持たないバッチ実行モデルである（[ADR-0025](adr/0025-deployment-strategy.md)）。公開成果物は静的ファイル配信であり、常時稼働のAPIサーバー・認証基盤を持たない（[ADR-0026](adr/0026-security-policy.md)）。したがって本ドキュメントの主眼は、Webサービス的な侵入防御（WAF、認証・認可基盤の堅牢化等）ではなく、**サプライチェーン全体の完全性**（コード・依存関係・実行基盤・成果物が、意図したものから改変されていないことの保証）と、**秘匿情報の非露出**（Secretがログ・成果物・Git履歴に混入しないこと）に置く。

## Threat Model

### 保護対象資産（Assets）

| 資産 | 何を守るか | 対応する既存設計 |
|---|---|---|
| Gold Database | 公開データの真正性・完全性 | [`docs/database/schema.md`](database/schema.md), Review Domain（[`docs/review/`](review/)） |
| Knowledge Base / Layout定義 | ドメイン知識の正確性（誤った知識が全レコードに波及するリスク） | [`docs/knowledge/schema.md`](knowledge/schema.md), [ADR-0005](adr/0005-knowledge-base-normalization.md) |
| 公開成果物（JSON/CSV/Parquet） | 配布後の改ざん検知・真正性 | [`docs/database/json_schema.md`](database/json_schema.md), [ADR-0022](adr/0022-export-policy.md) |
| Secret（FTP認証情報・署名鍵等） | 非露出、権限を持つ主体のみが利用可能であること | [`docs/configuration.md`](configuration.md#secret管理), [ADR-0026](adr/0026-security-policy.md) |
| CI/CDパイプライン（GitHub Actionsワークフロー定義） | 意図しない改変・悪意あるコード実行の防止 | 本ドキュメント「GitHub Actions」節 |
| 依存ライブラリ | 既知の脆弱性を持つコードの混入防止 | 本ドキュメント「Dependency」節 |
| 個人（発令PDFに記載された人物） | 公表範囲を超える情報の集約・拡散防止 | [ADR-0008](adr/0008-data-ethics-policy.md)（データ倫理方針。本ドキュメントの対象外。セキュリティではなく倫理の関心事として別管理） |

### 脅威アクター（Threat Actors）

| アクター | 想定する脅威 |
|---|---|
| 外部の第三者 | 公開成果物・FTP配布経路上での改ざん、公開リポジトリからのSecret窃取試行 |
| 侵害された依存ライブラリ（サプライチェーン攻撃） | 悪意あるコードの混入、ビルド・実行時の任意コード実行 |
| 侵害されたCIランナー・Actions | ワークフロー実行中のSecret窃取、成果物への不正な変更の混入 |
| 悪意ある、または誤りを犯した内部の担当者・AIエージェント | 権限を超えた変更（Gold Databaseの直接書き換え等）、レビュー未経過での公開 |
| 外部由来の入力（PDF自体） | パーサーの脆弱性を突いたリソース枯渇・任意コード実行（[ADR-0026](adr/0026-security-policy.md)で既に方針決定済み） |

### 脅威と対策の対応表

以下は、上記の資産・アクターから導かれる主要な脅威と、それに対応する本ドキュメントの各節の関係を示す。

| # | 脅威 | 対策領域（本ドキュメントの節） |
|---|---|---|
| T1 | Secretがリポジトリ・ログ・成果物に混入し、外部の第三者に窃取される | Secret |
| T2 | 依存ライブラリまたはGitHub Actions自体が侵害され、悪意あるコードが実行される | Supply Chain, GitHub Actions, Dependency |
| T3 | 配布経路（FTP等）上で公開JSON/CSV/Parquetが改ざんされる | JSON改ざん, FTP, Checksum, Hash, 署名 |
| T4 | 誰が・いつ・何を変更したかを事後的に追跡できず、不正な変更が発見されない | Audit Log |
| T5 | 必要以上の権限を持つ主体（人・AIエージェント・CIジョブ）が、意図しない変更を行う | 最小権限 |
| T6 | 新たなリスクを持つ変更（新依存・新Secret種別・Export/FTP変更）が、レビューされずに紛れ込む | Security Review |

`Constitution`のAI Principles（AIはGoldを書き換えない、AIはKnowledgeを直接変更しない）は、T5（内部主体による権限超過）に対する最上位の統制として既に機能している。本ドキュメントの「最小権限」節はこれをCIジョブ・GitHub権限レベルまで具体化する。

## Secret

Secretの種類・管理方法・環境ごとの扱いは[`docs/configuration.md`](configuration.md#secret管理)を正とする（重複定義しない）。本節ではセキュリティの観点を補足する。

- **漏えい時の被害範囲（Blast Radius）**: Secretの種類ごとに、漏えいした場合に何が起こりうるかを明確にしておく。FTP認証情報の漏えいは「第三者が公開成果物の配布経路を汚染できる」ことを意味し、署名鍵（「署名」節）の漏えいは「第三者が正規の成果物として偽のデータを配布できる」ことを意味する。後者の方が影響が大きいため、署名鍵は他のSecretより厳格なアクセス制御（後述「最小権限」）の対象とする。
- **検知**: `.pre-commit-config.yaml`のgitleaksによる誤コミット検知（[ADR-0026](adr/0026-security-policy.md)）を維持する。検知はコミット前（ローカル）とCI（プッシュ後の保険）の二段構えとし、CI側の検知が作動した場合はSecretが既に漏えいした可能性があるとみなし、直ちにローテーションする。
- **ローテーション**: 定期ローテーション（頻度は実装時にRunbookで具体化）に加え、担当者の異動・退職時、漏えいの疑いが生じた時点での即時ローテーションを必須とする。

## Supply Chain

サプライチェーンは「コードそのもの」だけでなく、「コードを実行するために経由するすべてのもの」（依存ライブラリ、CIのActions、ビルド環境）を含む。

- **範囲**: Pythonの依存ライブラリ（「Dependency」節）、GitHub Actions（「GitHub Actions」節）、PDFパースライブラリ等の外部由来入力を処理するライブラリ（[ADR-0026](adr/0026-security-policy.md)で選定基準を既に決定済み）を対象とする。
- **来歴の追跡**: [ADR-0023](adr/0023-parser-versioning-policy.md)が定めるリリースタグベースのバージョニングにより、「どのコミット・どのリリースで生成されたデータか」は既に追跡可能である。サプライチェーンの観点からは、これに加えて「そのリリースが、どの依存ライブラリ・Actionsのバージョンでビルド・実行されたか」も再現性の一部として重要になる。依存関係のロック（`pyproject.toml`のロックファイル、実装時に確定）は、この再現性を保証する基盤である。
- **将来の拡張**: SBOM（Software Bill of Materials）の生成や、より形式的なプロベナンス証明（SLSA等の枠組み）の採用は、本プロジェクトの規模（小規模・低頻度リリース）に対して現時点では過剰投資と判断し、採用しない。処理規模・関与者数が拡大した場合に、新規ADRとして再検討する（[ADR-0001](adr/0001-python-packaging.md)の「枯れた技術・保守負荷最小化」の方針と整合）。

## GitHub Actions

[ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md)が決定したハードニング方針を以下に具体化する。

- **Actionsのピン留め**: サードパーティ製Actionsは、可変なタグ（`@v4`等）ではなく、コミットSHAへのピン留めを既定とする。タグは公開後に指し先を差し替えられる可能性があり、ピン留めされていないActionsへの依存は、その提供元が侵害された場合にワークフロー実行時の任意コード実行につながりうる。GitHub公式の`actions/checkout`等についても、同様のピン留めへの移行を推奨する。既存の`.github/workflows/ci.yml`は現時点ではタグ参照のままであり、実装フェーズで段階的に移行する（[ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md)の「結果（トレードオフ）」を参照。本ドキュメントの作成をもって既存ワークフローファイルを直ちに書き換えることはしない）。
- **`GITHUB_TOKEN`権限の最小化**: 各ワークフローが必要とする最小の権限（例: lint/testのみを行うワークフローには`contents: read`のみ）を明示的に指定し、既定の広い権限に依存しない。
- **Secretへのアクセス範囲**: `production`用のSecret（FTP認証情報、署名鍵）は、それを必要とするワークフロー（定期実行・Export/公開ジョブ）専用のGitHub Environmentに紐づけ、他のワークフロー（CI上のlint/test等）からはアクセスできないようにする（[`docs/configuration.md`](configuration.md#github-secrets)のEnvironment分離設計と一致させる）。
- **Pull Requestからの実行に関する注意**: 外部からのPull Requestに対してSecretを要するワークフローを自動実行しない（フォークからのPRは、Secretへのアクセスを要しないジョブ、例えば通常のlint/testのみを実行する）。これは本プロジェクトが公開リポジトリであり、第三者からのPRを受け付ける可能性を考慮した予防的な制約である。

## Dependency

- **脆弱性スキャン**: [ADR-0026](adr/0026-security-policy.md)が既に決定したとおり、CIに依存ライブラリの脆弱性自動スキャンを組み込む。既知の重大な脆弱性を持つ依存の追加・放置を防ぐ。
- **バージョン固定**: `pyproject.toml`（[ADR-0001](adr/0001-python-packaging.md)）における依存バージョンは、ロックファイルにより固定し、意図しないマイナー・パッチアップデートによる予期しない挙動変化を防ぐ。固定されたバージョンの更新は、脆弱性スキャンの結果か、明示的な機能要件に基づいて行い、自動追従はしない。
- **新規依存追加の審査**: 新しい依存ライブラリの追加は、`AGENTS.md`の変更ガードレール（依存ライブラリの新規追加は着手前にADR確認）に従う。本ドキュメントはこの既存ルールを変更しない。

## JSON改ざん

公開成果物（JSON/CSV/Parquet、[ADR-0016](adr/0016-public-json-format.md), [ADR-0022](adr/0022-export-policy.md)）に対する改ざんは、以下の2段階で対策する。

1. **破損検知**: `exports.checksum`（内容のSHA-256ハッシュ、[`docs/database/schema.md`](database/schema.md)）により、転送中の偶発的な破損・不完全なダウンロードを検知する。
2. **真正性検証**: チェックサムのみでは、配布経路そのものが侵害された場合（チェックサムとファイルを同時に差し替えられた場合）の改ざんを検知できない。[ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md)が決定したとおり、チェックサムに対する署名（「署名」節）を追加し、公開鍵を保持する第三者が独立に真正性を検証できるようにする。

利用者（成果物のダウンロード側）に対しては、チェックサムと署名の両方を検証する手順を、実装時に公開ドキュメント（利用者向けREADME等）として提供する。

## FTP

- [ADR-0022](adr/0022-export-policy.md)が定める配布経路としてのFTPは、平文FTPではなく、暗号化された経路（FTPS、またはSFTP）を既定とする。既存のADR・設計文書は転送方式の暗号化有無に言及していなかったため、本ドキュメントで明示する。認証情報が経路上で平文送信される平文FTPは、本プロジェクトの利用対象としない。
- FTP認証情報の管理は[`docs/configuration.md`](configuration.md#ftp-secret)の設計（`SecretStr`型、`production`/`staging`限定、ログへの誤出力防止）に従う。
- FTP接続先ホストの検証（意図しないホストへの誤送信防止）を、Export/公開ジョブの`Settings`検証（[`docs/configuration.md`](configuration.md#validation-rule)のValidation Rule）の一部として行う。

## Checksum / Hash

既存の設計に、SHA-256をハッシュアルゴリズムとして用いるチェックサム・ハッシュフィールドが複数存在する。これらを本ドキュメントで一覧化し、単一の標準に統一されていることを確認する。

| フィールド | 対象 | 用途 |
|---|---|---|
| `pdfs.content_hash` | 取得したPDFファイルの内容 | 重複排除（内容アドレス方式）・来歴の起点（[`docs/database/schema.md`](database/schema.md)） |
| `layouts.manifest_checksum` | Layout定義ファイル | Layout定義自体の改変検知 |
| `candidate_records.source_checksum` | 抽出元セクションの内容 | 再現性の検証 |
| `learning_dataset.knowledge_snapshot_checksum` | 修正時点のKnowledge Baseスナップショット | どの版のKnowledgeで判断されたかの追跡（[ADR-0024](adr/0024-knowledge-versioning-and-backfill.md)） |
| `parser_versions.git_commit_hash` | リリース時点のソースコード | データ生成バージョンの来歴（[ADR-0023](adr/0023-parser-versioning-policy.md)） |
| `exports.checksum` | 生成された公開成果物本体 | 破損検知、署名の対象（「署名」節） |

- **アルゴリズムの統一**: すべてSHA-256（64桁16進文字列）に統一する。既存設計（[`docs/database/json_schema.md`](database/json_schema.md)）が`pdfs.content_hash`に対してこの形式を既に採用しており、他のチェックサムフィールドも同一の形式・アルゴリズムに揃える。アルゴリズムを分散させると、検証ツールの実装・監査の複雑さが増すため、意図的に単一アルゴリズムに統一する。
- **チェックサムの限界**: 上表のいずれのチェックサムも「改変されていないことの検知」はできるが「誰が作ったかの証明（真正性）」はできない。真正性が必要な唯一の対象（`exports.checksum`、外部の第三者に配布される成果物）にのみ、署名を追加で適用する。他のチェックサム（内部処理のみで用いる`content_hash`等）には署名を要求しない。過剰な統制はコストに見合わない。

## 署名

[ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md)の決定に基づき、公開成果物の`exports.checksum`に対してデタッチド署名を付与する。

- **署名対象**: `exports.checksum`（成果物本体のSHA-256ハッシュ）。成果物本体そのものを毎回署名するのではなく、既に存在するチェックサムに対して署名することで、署名処理自体は軽量に保つ。
- **鍵管理**: 署名鍵は`production`環境専用のGitHub Secretsとして保管し、Export/公開ジョブ以外のいかなるワークフローからもアクセスできないようにする（「最小権限」節）。公開鍵はリポジトリ内（`docs/`配下、想定パスは実装時に確定）に平文で公開し、誰でも取得・検証できるようにする。
- **アルゴリズム**: 実績があり鍵長・署名サイズが実用的な非対称鍵暗号方式（例: Ed25519）を候補とするが、具体的な署名ツール・ライブラリの確定は実装着手時に行う（[ADR-0026](adr/0026-security-policy.md)が依存ライブラリの個別選定を実装時に委ねているのと同じ方針）。
- **鍵のローテーションと紛失**: 署名鍵のローテーションは、旧鍵で署名済みの過去の成果物の検証可能性を損なわないよう、旧公開鍵を削除せず「失効済み」として残す運用とする（[ADR-0006](adr/0006-pipeline-provenance.md)の「削除せず追記する」来歴管理の思想と整合）。鍵の紛失・侵害時の対応手順は、実装着手時に`docs/operations/`のRunbookとして具体化する。
- **検証は利用者側の任意操作**: 署名検証は成果物のダウンロード側が任意に行うものであり、本システム自体が検証を強制する仕組み（利用者側の検証を必須化する認証機構等）は持たない。静的ファイル配信という性質上（[ADR-0025](adr/0025-deployment-strategy.md)）、これは妥当な範囲である。

## Audit Log

[ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md)が決定したとおり、監査ログは新規の専用テーブルとしてではなく、既存のドメイン別来歴データの集合として扱う。

- **セキュリティ上重要な操作の分類**:
  - Gold Databaseへの書き込み: `review_changes` / `ReviewHistory`（[`docs/review/domain.md`](review/domain.md#reviewhistory)）に記録済み。誰の`ReviewDecision`に基づき、いつ、どのレコードが変更されたかを追跡できる。
  - パイプライン実行: `jobs`テーブル（[`docs/database/schema.md`](database/schema.md)）に記録済み。
  - 公開・Export・FTP送信: `exports`テーブル・対応する`jobs`行に記録済み。
  - Secretの利用: GitHub Actionsの実行ログ（GitHub側が保持する監査ログ、[`docs/operations/observability.md`](operations/observability.md)のLogging/Tracing設計とも接続する）を一次情報源とする。プロジェクト独自のSecret利用ログは重複して持たない。
  - 設定・権限の変更: リポジトリ設定・GitHub Environment・CODEOWNERSの変更は、Gitのコミット履歴自体が監査証跡になる（`CODEOWNERS`によりこれらのファイルへの変更は必須レビュー対象）。
- **横断的な参照**: 上記は個々には既に設計済みだが、「あるレコード・ある期間について、セキュリティ上重要な操作をすべて時系列で追える」ことを保証するため、実装時に`services/`層に、これらを`candidate_id` / `job_id` / `pdf_id`等の共通IDで串刺しにクエリする薄い参照層を用意する（[`docs/review/domain.md`](review/domain.md#reviewhistory)の`ReviewHistory`が「独立して永続化しないread-model」として設計されているのと同じ考え方を、Review以外の監査証跡にも適用する）。
- **改ざん耐性**: これらの記録は追記のみ（append-only）であり、[ADR-0006](adr/0006-pipeline-provenance.md)の「削除せず追記する」来歴管理方針により、事後的な書き換え・削除を行わない。監査ログとしての信頼性は、この不変性そのものに由来する。
- **保持期間**: 各テーブルの既存の保持期間方針（`docs/database/schema.md`が定める「永久保持（監査証跡）」等）をそのまま踏襲する。監査目的専用の別の保持期間は設けない。

## 最小権限

| 主体 | 権限範囲 | 根拠 |
|---|---|---|
| AIコーディングエージェント | Gold Databaseを直接書き換えない。Knowledge Baseを直接変更しない。人間の承認を経ない変更を確定させない | [`docs/constitution.md`](constitution.md)のAI Principles、`CLAUDE.md`/`AGENTS.md` |
| CIワークフロー（lint/test） | リポジトリの読み取りのみ（`contents: read`）。いかなるSecretにもアクセスしない | 「GitHub Actions」節 |
| CIワークフロー（Export/公開/FTP送信） | `production`/`staging`のFTP Secret・署名鍵にのみアクセス可能。他のワークフローとは別のGitHub Environmentに分離 | 「GitHub Actions」節、[`docs/configuration.md`](configuration.md#github-secrets) |
| レビュー担当者（Human Review） | `ReviewDecision`を通じてのみGold Databaseへの反映を発生させられる。直接のSQL実行・DBファイル編集は想定しない | [`docs/review/policy.md`](review/policy.md), Architecture Contractの「Reviewだけがgold_recordsを書き換えられる」保証（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)） |
| リポジトリの管理者・コードオーナー | `docs/adr/` / `CLAUDE.md` / `AGENTS.md` / `pyproject.toml` / `.github/`等、影響範囲の大きいパスへの変更承認権限 | `CODEOWNERS` |
| 一般のコントリビューター（PR作成者） | Secretへのアクセス権を持たない。フォークからのPRはSecretを要するワークフローを実行しない | 「GitHub Actions」節 |

最小権限の原則は、「ある主体が事故または悪意により誤った操作をした場合に、影響範囲が本来必要な範囲を超えて広がらないこと」を目的とする。上表の各行は、Threat Modelの脅威T5（権限超過による意図しない変更）に対する具体的な統制である。

## Security Review

セキュリティ上のリスクを伴う変更は、通常のコードレビュー（[ADR-0014](adr/0014-development-discipline.md)）に加えて、Security Reviewの対象とする。既存の[Architecture Review](architecture-review-package.md)と同様、専用の重い手続きを新設するのではなく、レビュー観点のチェックリストとして運用する。

**Security Reviewが必要な変更（トリガー条件）**:

- 新しい外部依存ライブラリの追加（「Dependency」節、`AGENTS.md`の既存ルールと同一のトリガー）
- 新しい種類のSecretの導入、またはSecretのスコープ・アクセス範囲の変更
- Export/FTP送信の宛先・方式の変更
- GitHub Actionsワークフローの権限（`GITHUB_TOKEN`のpermissions、Secretへのアクセス範囲）の変更
- 署名鍵・チェックサムの仕組み自体の変更

**チェックリスト（レビュー観点）**:

1. この変更は、Threat Modelのどの脅威（T1〜T6）に関係するか。新たな脅威を生んでいないか。
2. 新たに追加される権限・アクセス範囲は、実際に必要な最小限か（「最小権限」節）。
3. Secretがログ・成果物・エラーメッセージに混入する経路が新たに生まれていないか。
4. 変更はAudit Logの追跡可能性を損なわないか（記録の欠落を生む変更でないか）。

**実施者**: `CODEOWNERS`に基づき、該当パス（`.github/`, `pyproject.toml`, `docs/adr/`等）のコードオーナーが実施する。専任のセキュリティ担当ロールは、現状の体制規模では設置せず、既存のレビュー体制に統合する。将来、体制規模が拡大した場合は、専任ロールの新設を新規ADRとして検討する。

## 関連ADR・ドキュメント

- [ADR-0001](adr/0001-python-packaging.md) — Pythonパッケージング。依存最小化・ロックファイルの前提。
- [ADR-0006](adr/0006-pipeline-provenance.md) — パイプライン段階分割と来歴管理。Audit Logの「削除せず追記する」思想の根拠。
- [ADR-0008](adr/0008-data-ethics-policy.md) — 個人情報・データ倫理方針。本ドキュメントのセキュリティとは別軸の関心事。
- [ADR-0014](adr/0014-development-discipline.md) — 開発規律。Security Reviewの位置づけの前提。
- [ADR-0016](adr/0016-public-json-format.md) — 公開JSON形式。改ざん検知・署名の対象契約。
- [ADR-0019](adr/0019-workflow-orchestration.md) — 実行オーケストレーション戦略。GitHub Actions Secretsの前提。
- [ADR-0022](adr/0022-export-policy.md) — Export Policy。FTP送信の対象・頻度。
- [ADR-0023](adr/0023-parser-versioning-policy.md) — Parserバージョニング方針。Supply Chainの来歴追跡と関連。
- [ADR-0025](adr/0025-deployment-strategy.md) — デプロイメント戦略。バッチ実行モデル、認証・認可を最小限とする根拠。
- [ADR-0026](adr/0026-security-policy.md) — セキュリティポリシー全般（本ドキュメントが具体化する上位決定）。
- [ADR-0029](adr/0029-export-integrity-and-audit-log-policy.md) — 公開成果物の完全性保証と監査ログ方針（署名・GitHub Actionsハードニング・Audit Logの決定）。
- [`docs/configuration.md`](configuration.md) — Secret管理・Validation Ruleの詳細設計。
- [`docs/operations/observability.md`](operations/observability.md) — Logging/Tracing方針。Secretの誤出力防止・Audit Logとの接続点。
- [`docs/review/domain.md`](review/domain.md) — `ReviewHistory`。Audit Logの一部として参照。
- [`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md) — 「Reviewだけがgold_recordsを書き換えられる」保証。最小権限の構造的な裏付け。
- [`docs/constitution.md`](constitution.md) — Core Principles「Security by Default」、AI Principles。本ドキュメント全体が従属する上位方針。
