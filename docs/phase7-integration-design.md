# Phase7 Integration Design

> **本ドキュメントに実装（コード）はない。** Phase7（Task16-1〜16-4）で実装済みとなった`ftp/`・`fetch/`・`features/`・`services/`を、既存のComposition Root（`cli/bootstrap.py`、[ADR-0046](adr/0046-composition-root-dependency-injection-contract.md)）へ統合するための設計をTask17-0として確定する。実装そのもの（`cli/bootstrap.py`・`cli/commands.py`等の変更）は本ドキュメントの対象外であり、着手する場合は本ドキュメントが定める前提条件（新規ADR起票を含む）に従う別タスクで行う。
>
> 対象読者・関連ドキュメントとの関係は[`docs/phase7-implementation-roadmap.md`](phase7-implementation-roadmap.md)と同じ扱いに準じる。各パッケージの詳細な責務・依存先は[`docs/api/package-design.md`](api/package-design.md)、依存方向のグラフは[`docs/api/dependency-rule.md`](api/dependency-rule.md)、Protocol定義は[`docs/api/interfaces.md`](api/interfaces.md)を正とし、本ドキュメントはこれらと矛盾しない**統合計画**のみを記述する。

## 1. 位置づけ・Non-goal

- Phase7 Task16-0（[`docs/phase7-implementation-roadmap.md`](phase7-implementation-roadmap.md)）は4パッケージの**設計方針・依存方向**を確定し、Task16-1〜16-4がそれぞれを**単独パッケージとして**実装した。いずれも`cli/bootstrap.py`（Composition Root）からは一切参照されておらず（Task16-5最終監査・Task16-6 Document Synchronizationで確認済み）、CLIから利用できない状態にある。
- 本Task17-0は、この「実装済みだが未配線」の状態を解消するための**統合設計**を確定する。対象は生成位置・生成順序・既存コードとの整合性であり、実装の実施そのものではない。
- **Non-goal**: 本ドキュメントに登場する関数名・シグネチャ例（`build_fetch_client()`等）は設計意図を明確にするための**予定案**であり、確定した実装契約ではない。実装着手時は、本ドキュメントを起点としつつ、実装レベルの詳細（引数名・例外処理等）は当該タスクのレビューで確定する。CLAUDE.mdの「大きな設計変更（データモデル、パイプライン段階、技術選定）を行う場合は、先にADRを追加してから実装する」規律に従い、特に4のFeatureStore統合・7のScheduler導入は新規ADR起票を前提とする（詳細は各節）。

## 2. Composition Rootへの統合方針（全体像）

**加算的統合（Additive Integration）**を基本方針とする。既存の合成ルート関数（`build_settings()` / `build_sqlite_repositories()` / `build_knowledge_service()` / `build_learning_service()` / `build_review_service()` / `build_export_service()` / `build_application()` / `build_job_runner()`、いずれも`cli/bootstrap.py`、Task11-5〜Task12-2で確立）は**シグネチャ・戻り値型を一切変更しない**。Phase7統合は、これらの後段に新しい`build_*`関数を追加し、それらの成果物を新設の`build_job_orchestrator()`が束ねる形で行う（詳細は[4](#4-joborchestrator生成位置)）。

この方針を取る理由:

- 既存コマンド（`init-db` / `run-pending` / `run-job` / `version` / `review *` / `export *`）・既存の結合テスト（`tests/integration/cli/test_cli_e2e.py`等）が、Phase7統合によって一切壊れないことを構造的に保証するため。
- [architecture-contract.md 保証15](architecture/architecture-contract.md#15-依存生成責務はcomposition-rootcliに一本化される)（依存生成責務はComposition Rootに一本化される）を維持したまま、生成対象を追加するだけで統合を完結できるため（`cli/`以外のパッケージに具象生成の責務を分散させない）。

## 3. CLIとの接続方針

- 既存6コマンドの内部実装（`pipeline/`・`review/`・`export/`への直接呼び出し）は**置き換えない**。`services/`（`JobOrchestrator`）へ移行する配線変更は行わない。既存コマンドは、Task16-6時点の[`package-design.md`](api/package-design.md)の`cli/`節が記す「`cli/`はその配下の`pipeline/`・`review/`・`export/`直接呼び出しを`services/`経由に置き換える配線変更をまだ行っておらず」という状態を、意図的に維持する（`services/`が提供する横断オーケストレーションは、既存コマンドの再実装ではなく、既存コマンドでは提供できない**新しい機能**を追加するために導入する）。
- 新規サブコマンド群（実装タスクでの追加を想定、コマンド名は暫定）: `fetch`（`JobOrchestrator.fetch_and_stage()`を呼び出す）・`workflow`（`run_workflow()`を呼び出す）・`publish`（`export_and_publish()`を呼び出す）。これらはPhase7統合が実際に価値を提供する新機能であり、既存コマンドとは独立したサブコマンドとして追加する。
- `Application`（`cli/bootstrap.py`、Task11-6で追加済みのdataclass）に、新フィールド`job_orchestrator: JobOrchestrator`を追加する想定とする。既存フィールド（`job_runner` / `review_service` / `export_service` / `_pdfs` / `_jobs` / `_knowledge_service`）は変更しない。

## 4. JobOrchestrator生成位置

**`cli/bootstrap.py`の新設関数`build_job_orchestrator()`が、唯一の生成位置である。**

```python
def build_job_orchestrator(
    application: Application,
    repositories: SqliteRepositories,
    fetch_client: FetchClient,
    ftp_client: FTPClient,
) -> DefaultJobOrchestrator:
    return DefaultJobOrchestrator(
        OrchestratorDependencies(
            fetch_client=fetch_client,
            ftp_client=ftp_client,
            pdf_repository=repositories.pdfs,
            job_runner=application.job_runner,
            review_service=application.review_service,
            export_service=application.export_service,
        )
    )
```

- `services/`自身（`DefaultJobOrchestrator`のコンストラクタを含む）は、[architecture-contract.md 保証15](architecture/architecture-contract.md#15-依存生成責務はcomposition-rootcliに一本化される)により、自らの依存の具象実装を生成しない設計のまま維持する（`services/__init__.py`のdocstringが既に明記済み）。したがって`JobOrchestrator`の生成位置が`cli/bootstrap.py`以外になることはない。
- `OrchestratorDependencies`の6フィールドのうち、`pdf_repository` / `job_runner` / `review_service` / `export_service`の4つは、既存の生成順序1〜7（[9](#9-依存生成順序)参照）が既に構築済みのインスタンスをそのまま再利用する（新規生成しない）。新規生成が必要なのは`fetch_client`・`ftp_client`の2つのみである。

## 5. FetchClient生成位置

**`cli/bootstrap.py`の新設関数`build_fetch_client()`が、唯一の生成位置である。**

```python
def build_fetch_client() -> FetchClient:
    return HTTPFetchClient()
```

`HTTPFetchClient`（`fetch/client.py`）のコンストラクタは`expected_status_codes: frozenset[int] = frozenset({200})`のみを取り、`AppSettings`・その他の設定値への依存を持たない（[8](#8-appsettingsとの接続)参照）。したがって`build_fetch_client()`は他の`build_*`関数のいずれよりも先に、依存なしで呼び出せる。

## 6. FTPClient生成位置

**`cli/bootstrap.py`の新設関数`build_ftp_client(settings)`を、唯一の生成位置として予定するが、現時点では前提条件が未整備であり実装をブロックされている。**

```python
def build_ftp_client(settings: CompositionSettings) -> FTPClient:
    return StandardFTPClient(
        FTPConnectionConfig(
            host=settings.ftp.host,       # 未実装: settings.ftp は現存しない
            port=settings.ftp.port,
            username=settings.ftp.username,
            password=settings.ftp.password.get_secret_value(),
            timeout=settings.ftp.timeout,
            passive=settings.ftp.passive,
        )
    )
```

**未解決のブロッカー**: `FTPConnectionConfig`（`ftp/config.py`）はホスト・ポート・ユーザー名・パスワード等を要求するが、`AppSettings`（`config/settings.py`、Phase6 Task14-5実装）は現時点でこれらのフィールドを一切持たない。`docs/configuration.md`は`FtpSettings`（`SecretStr`によるパスワード秘匿を含むネスト設定、[`docs/configuration.md`](configuration.md)参照）を設計済みだが、`config/settings.py`のdocstringが自己申告するとおり「`docs/configuration.md`が設計する`DatabaseSettings`/`FtpSettings`等のネスト構造・`Environment`・`SecretStr`は本Taskの対象外（未実装のまま）」の状態が継続している。したがって`build_ftp_client()`の実装着手は、**`AppSettings`への`FtpSettings`追加（`config/`パッケージの変更、別タスク）が完了した後**を前提とする。この前提が満たされるまで、Phase7統合のうち`export_and_publish()`のFTPアップロード経路・`run_workflow()`のFTP公開を伴う完全な経路は実現できない（`fetch_and_stage()` / `run_job()` / `run_pending_pipeline()` / `list_pending_reviews()`はFTPClientを必要としないため、この制約を受けない）。

## 7. FeatureStore生成位置

**`cli/bootstrap.py`に`build_feature_store(learning_service)`を追加することは技術的には可能だが、生成しても現時点では消費先が存在しないため、Phase7統合の対象外として据え置く。**

```python
def build_feature_store(learning_service: LearningService) -> FeatureStore:
    return DefaultFeatureStore(learning_service)
```

`DefaultFeatureStore`（`features/store.py`）のコンストラクタは`learning_service: LearningService | None = None`のみを要求し、既存の生成順序3（`build_learning_service()`）の成果物をそのまま渡せる（技術的な生成自体に障害はない）。

しかし、[`package-design.md`](api/package-design.md)の`features/`節・[`interfaces.md`](api/interfaces.md#featurestore)が確認するとおり、`FeatureStore`の呼び出し元として設計されている`JobRunner`（`pipeline/job_runner.py`）は、`FeatureVector`を`Normalizer`/`Validator`のコンストラクタへ注入する引数を**現時点で持たない**（`__init__`のシグネチャに`features`相当の引数がない）。`cli/bootstrap.py`が`FeatureStore`を生成しても、それを渡す先が存在しなければ「生成されるが使われない値」を合成ルートに追加するだけであり、これは`services/`統合（[4](#4-joborchestrator生成位置)、生成後ただちに`OrchestratorDependencies`へ渡り使用される）とは性質が異なる。

したがって、`FeatureStore`のComposition Root統合は、以下の前提が満たされてから着手する2段階の計画とする。

1. **前提**: `JobRunner` / `Normalizer` / `Validator`のコンストラクタへ`FeatureStore`（または計算済み`FeatureVector`）を注入する契約を、`docs/phase7-implementation-roadmap.md`のPhase7.1′が既に想定するとおり、ADR-0040/ADR-0041（`KnowledgeSnapshot`/`ValidationRuleSet`のコンストラクタ注入パターン）に準じる新規ADRとして正式決定する（`pipeline/`・`normalizers/`・`validators/`の変更を伴うため、本Task17-0のScope外）。
2. **その後**: 上記ADRに従い`JobRunner`の生成順序（[9](#9-依存生成順序)の順序7）に`build_feature_store()`の呼び出しを追加し、`JobRunner`のコンストラクタへ注入する。

## 8. AppSettingsとの接続

| 生成対象 | `AppSettings`への依存 | 状態 |
|---|---|---|
| `FetchClient`（`build_fetch_client()`） | なし | 依存なしで生成可能（[5](#5-fetchclient生成位置)） |
| `FTPClient`（`build_ftp_client()`） | `settings.ftp`（`FtpSettings`、**未実装**） | `config/`への`FtpSettings`追加を待つ（[6](#6-ftpclient生成位置)） |
| `FeatureStore`（`build_feature_store()`） | なし | 生成自体は依存なしで可能だが、消費先未整備のため統合対象外（[7](#7-featurestore生成位置)） |
| `JobOrchestrator`（`build_job_orchestrator()`） | なし（構築済みインスタンスの束のみを受け取る） | 上記3つと既存`Application`が揃えば生成可能 |

`AppSettings`本体（`db_path` / `knowledge_root` / `layouts_root` / `parser_code_version`の4フィールド、`config/settings.py`）自体の変更は、`FtpSettings`追加（[6](#6-ftpclient生成位置)のブロッカー解消）を除き、Phase7統合には不要である。

## 9. 依存生成順序

既存の生成順序1〜7（[`package-design.md`](api/package-design.md)の`cli/`節、ADR-0046）は変更しない。Phase7統合はこの後段に順序8〜10を追加する。

| 順序 | 内容 | 新設/既存 | 備考 |
|---|---|---|---|
| 1 | SQLite Repository具象生成 | 既存 | `build_sqlite_repositories()` |
| 2 | `KnowledgeService`生成 | 既存 | `build_knowledge_service()` |
| 3 | `LearningService`生成 | 既存 | `build_learning_service()` |
| 4 | `ReviewService`生成 | 既存 | `build_review_service()` |
| 5 | `ExportService`生成 | 既存 | `build_export_service()` |
| 6 | `JobRunnerRepositories`生成 | 既存 | `build_application()`内 |
| 7 | `JobRunner`生成 | 既存 | `build_application()`内。順序1〜7の全体が`Application`を返す |
| 8 | `FetchClient`生成 | **新設** | `build_fetch_client()`。依存なし（[5](#5-fetchclient生成位置)） |
| 9 | `FTPClient`生成 | **新設・ブロック中** | `build_ftp_client(settings)`。`FtpSettings`実装待ち（[6](#6-ftpclient生成位置)） |
| 10 | `JobOrchestrator`生成 | **新設** | `build_job_orchestrator()`。順序1〜9の成果物を束ねる（[4](#4-joborchestrator生成位置)） |

`FeatureStore`生成（[7](#7-featurestore生成位置)）は、この番号付き順序には含めない。消費先（`JobRunner`拡張）が未確定である現時点で順序に含めると、「生成されるが使われない値」の生成タイミングを規定することになり、実装の推測を招くため（Task16-6が確立した「実装内容を推測で記載しない」規律に従う）。

## 10. JobRunnerとの接続

`JobOrchestrator`は`JobRunner`のコンストラクタ・生成順序（順序1〜7）を一切変更しない。`DefaultJobOrchestrator.run_job()` / `run_pending_pipeline()`は、順序7で既に構築済みの`Application.job_runner`をそのまま`OrchestratorDependencies.job_runner`として受け取り、`self._job_runner.run_for_pdf(pdf)` / `self._job_runner.run_pending()`へ委譲するのみである（`services/orchestrator.py`の既存実装、Task16-4）。Phase7統合によって`JobRunner`自身に加わる変更は存在しない。

[7](#7-featurestore生成位置)が扱う`FeatureStore`→`JobRunner`統合のみが`JobRunner`のコンストラクタ変更を伴うが、これはPhase7統合（本Task17-0のScope）とは別の、新規ADRを前提とする将来タスクである。

## 11. 既存build_*関数との整合

以下の既存公開関数（`cli/bootstrap.py`の`__all__`、Task11-5〜Task12-2で確立）は、Phase7統合によって**シグネチャ・戻り値型・呼び出し順序のいずれも変更しない**。

- `build_settings()`
- `build_sqlite_repositories()`
- `build_knowledge_service()`
- `build_learning_service()`
- `build_review_service()`
- `build_export_service()`
- `build_application()`
- `build_job_runner()`

Phase7統合が追加する新規関数（`build_fetch_client()` / `build_ftp_client()` / `build_job_orchestrator()`、[9](#9-依存生成順序)の順序8〜10）は、いずれも上記の**後段**でのみ呼び出され、既存関数の内部実装・呼び出し元（`build_application()`自身を含む）を変更しない。この整合性により、既存の結合テスト（`tests/integration/cli/`・`tests/integration/config/`）・単体テスト（`tests/unit/cli/`）は、Phase7統合の実装着手後も無変更で成立し続ける設計とする。

## 12. Scheduler導入予定位置

`Scheduler`（[`interfaces.md#scheduler`](api/interfaces.md#scheduler)）は未実装であり、[ADR-0025](adr/0025-deployment-strategy.md)が定める**バッチ実行モデル**（永続プロセスではなく、外部トリガーがCLIを都度起動する方式、[`docs/operations/release.md`](operations/release.md#release-flow)参照）と整合させる必要がある。

既存の`nightly.yml`（[`.github/workflows/README.md`](../.github/workflows/README.md)）が、GitHub Actionsの`schedule`トリガーによって定期的にCI相当のジョブを起動する前例を踏まえ、Scheduler導入は以下の2案を比較検討する前提を記録する。最終決定は本Task17-0の対象外とし、着手時に新規ADRで確定する。

- **案A（軽量・ADR-0025と親和）**: `Scheduler` Protocolの具象実装を持たず、外部のcron/GitHub Actionsから、Phase7統合で追加する新規CLIサブコマンド（[3](#3-cliとの接続方針)の`workflow`等）を定期的に起動する。この場合`Scheduler`は「CI/CD運用手順」として`docs/operations/release.md`に記述され、`src/`に対応する実装を持たない。
- **案B（常駐プロセス）**: `Scheduler`の具象実装（例: `SimpleScheduler`）を`services/`または新設パッケージに追加し、長時間稼働プロセスとして`JobOrchestrator.run_workflow()`を内部から定期呼び出しする。この場合、生成位置は案Aと同様`cli/`（またはそれに準ずる新しいエントリポイント）だが、既存のバッチ実行モデル（ADR-0025）からの逸脱となるため、デプロイ戦略自体の見直しを伴う新規ADRが必須となる。

**責務境界**: いずれの案でも、`Scheduler`は「いつ`JobOrchestrator.run_workflow()`を呼び出すか」の決定にのみ責務を持ち、`JobOrchestrator`自身（[4](#4-joborchestrator生成位置)）が担う「`fetch/`・`ftp/`・`pipeline/`・`review/`・`export/`をどう調整するか」には関与しない。この境界は[`interfaces.md`](api/interfaces.md#scheduler)が既に明記する「`JobOrchestrator`をSchedulerへ統合するような設計にはしない」という制約と一致する。

## 13. 循環依存が発生しないことの確認

Phase7統合により`cli/`が新たに依存するのは`fetch/`・`ftp/`・`services/`の3パッケージである（`features/`は[7](#7-featurestore生成位置)のとおり本統合の対象外）。[`package-design.md`](api/package-design.md)のパッケージ横断の依存先サマリ表が確認するとおり、`fetch/`・`ftp/`・`services/`のいずれも`cli/`への依存禁止が既に明記されており（`services/`の依存禁止に`cli/`を含む）、逆方向の依存は存在しない。したがって`cli --> fetch` / `cli --> ftp` / `cli --> services`のいずれの新規エッジも、既存の依存グラフに循環を生じさせない。統合後の依存グラフは[`dependency-rule.md`](api/dependency-rule.md#統合後の依存グラフphase7-integration-design計画中)に図示する。

## 関連ドキュメント

- [`docs/phase7-implementation-roadmap.md`](phase7-implementation-roadmap.md) — Phase7 Task16-0が確定した4パッケージの設計方針・実装順序
- [`docs/api/package-design.md`](api/package-design.md) — 各パッケージの責務・依存先（Package Design）
- [`docs/api/dependency-rule.md`](api/dependency-rule.md) — 全体依存グラフ・統合後の依存グラフ（Dependency Rule）
- [`docs/api/interfaces.md`](api/interfaces.md) — `JobOrchestrator` / `Scheduler`等のProtocol定義
- [`docs/configuration.md`](configuration.md) — `FtpSettings`等、`AppSettings`拡張の設計
- [`docs/operations/release.md`](operations/release.md) — Release Flow・バッチ実行モデル（ADR-0025）
- [`docs/adr/0046-composition-root-dependency-injection-contract.md`](adr/0046-composition-root-dependency-injection-contract.md) — Composition Root DI契約
- [`RELEASE_STATUS.md`](../RELEASE_STATUS.md) — v1.0.0 Release Candidateのリリース判定・Remaining Work
