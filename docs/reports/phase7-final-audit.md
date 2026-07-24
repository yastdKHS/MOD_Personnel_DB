# Phase7 Task17-5 — 最終監査レポート

> 実施日: 2026-07-24。対象: Phase7全体（`ftp/`・`fetch/`・`features/`・`services/`・`Scheduler`・CLI統合・Composition Root・Dependency Rule・Package Design・Architecture Contract・`interfaces.md`・Release Readiness）。本レポートはコード変更・テスト変更を一切伴わない、読み取り専用の監査である。改善提案は含まない。前回のPhase7監査（Task16-5、`ftp/`・`features/`・`fetch/`・`services/`の実装直後・CLI未配線時点）を引き継ぎ、Task17-0〜17-4で実施したComposition Root統合（`fetch/`・`ftp/`・`JobOrchestrator`のTask17-1、CLIコマンド化のTask17-2、`Scheduler`実装のTask17-3、`Scheduler`のCLIコマンド化のTask17-4）が完了した状態を対象とする。

## 監査対象と方法

`src/mod_personnel_db/`全体の実際のimport文をgrep・ASTで走査し、`docs/api/package-design.md`・`docs/api/dependency-rule.md`・`docs/api/interfaces.md`・`docs/architecture/architecture-contract.md`の記述と突き合わせた。加えて、`mypy --strict`・`ruff check`・`ruff format --check`・`pytest --cov`を実行し、静的検証・テストが全件成功することを確認した。

## 1. 循環依存が存在しないこと

`fetch/`・`ftp/`・`features/`・`services/`・`cli/`それぞれの実際のimport（`grep -rhoE "^from mod_personnel_db\..*import|^import mod_personnel_db\..*"`）を確認した結果は以下のとおり。

| パッケージ | 実際の依存先 |
|---|---|
| `fetch/` | `utils/`のみ（`fetch/exceptions.py`が`MODPersonnelDBError`を参照） |
| `ftp/` | `utils/`のみ（`ftp/exceptions.py`が`MODPersonnelDBError`を参照） |
| `features/` | `models/`, `learning/`, `utils/` |
| `services/` | `export/`, `fetch/`, `ftp/`, `models/`, `pipeline/`（`pipeline.job_runner.JobRunner`含む）, `repositories/`（抽象）, `review/` |
| `cli/` | `config/`, `export/`, `fetch/`, `features/`, `ftp/`, `knowledge/`, `layout/`, `learning/`, `models/`, `pipeline/`, `repositories/sqlite/`（合成ルートの例外）, `review/`, `services/`, `utils/` |

`pipeline/`・`repositories/`・`review/`・`export/`・`knowledge/`・`learning/`・`models/`・`utils/`・`config/`・中核パイプライン6段階（`document/`〜`validators/`）のいずれのソースにも、`services`・`cli`・`fetch`・`ftp`という文字列を含む`import`文は検出されなかった（`grep -rhoE`で空集合を確認）。したがって`services/`→`fetch/`→`cli/`のような逆流エッジは存在せず、依存方向はすべて「`cli/`が末端（`fetch/`・`ftp/`・`services/`・その他）を指す」一方向のみである。**循環依存は検出されなかった。**

## 2. Composition Rootが唯一であること

`src/mod_personnel_db/`全体を対象に、Phase7で追加された4つの具象クラス（`HTTPFetchClient`・`StandardFTPClient`・`DefaultJobOrchestrator`・`DefaultScheduler`）の直接インスタンス化箇所をgrep（`grep -rn "HTTPFetchClient(\|StandardFTPClient(\|DefaultJobOrchestrator(\|DefaultScheduler("`）で検索した結果、**4件すべてが`src/mod_personnel_db/cli/bootstrap.py`内**（`build_fetch_client()`・`build_ftp_client()`・`build_job_orchestrator()`・`build_scheduler()`）に限定されていることを確認した。他のいかなるパッケージ（`services/`自身を含む）にもこれらの具象生成は存在しない。

`tests/unit/cli/test_bootstrap.py`の`test_only_composition_root_constructs_phase7_concrete_implementations`（AST走査、Task17-4で`DefaultScheduler`を対象へ追加）が、この性質を機械的に継続検証している。Phase3〜Phase6で確立した`Sqlite*Repository`（8種）・`FileKnowledgeService`・`RepositoryLearningService`・`RepositoryReviewService`・`RepositoryExportService`の生成が`cli/bootstrap.py`一箇所に集約されているという既存の性質（Phase5最終監査で確認済み）も、Phase7で変更されていない。**Composition Rootは`cli/bootstrap.py`のみである。**

## 3. SchedulerがJobOrchestratorのみへ依存していること

`services/scheduler.py`の実際のimportは`from mod_personnel_db.models import JobId`と、`TYPE_CHECKING`ガード下の`from mod_personnel_db.services import JobOrchestrator`（型注釈のみ、循環import回避）の2件のみである。`DefaultScheduler.__init__`は`orchestrator: JobOrchestrator`・`schedules: tuple[JobSchedule, ...]`・`clock: Callable[[], datetime]`の3引数を属性代入するのみであり（`tests/unit/services/test_scheduler.py`のAST検証が保証）、`JobRunner`・`ReviewService`・`ExportService`・`FetchClient`・`FTPClient`・Repositoryのいずれも直接参照しない。`trigger_now()`は`self._orchestrator.run_pending_pipeline()`を呼ぶのみであり、`fetch/`・`ftp/`・`pipeline/`等を直接呼び出すコードパスは存在しない。**`Scheduler`は`JobOrchestrator`のみに依存する設計・実装になっている。**

## 4. CLIがProtocol経由のみ利用していること

`cli/commands.py`の`_build_job_orchestrator()`・`_build_scheduler()`はいずれも戻り値の型注釈が`JobOrchestrator`・`Scheduler`（`services/__init__.py`が定めるProtocol）であり、`fetch_stage_command`/`run_workflow_command`/`schedule_now_command`/`list_schedule_command`は変数の型注釈を経由してこれらのProtocol型としてのみ呼び出す。`cli/app.py`は`DefaultJobOrchestrator`・`DefaultScheduler`・`HTTPFetchClient`・`StandardFTPClient`のいずれの名前もimportしない（`from mod_personnel_db.services import RUN_PENDING_JOB_TYPE, WorkflowResult`という、定数・値オブジェクトの参照のみ）。**CLIコマンド層（`commands.py`・`app.py`）はPhase7の4具象クラスをいずれも直接参照せず、Protocol型経由でのみ利用している。**

## 5. JobOrchestratorの直接利用箇所が存在しないこと

`schedule_now_command`/`list_schedule_command`（`cli/commands.py`）は`_build_scheduler()`が返す`Scheduler`のメソッド（`trigger_now()`/`list_upcoming()`）のみを呼び出し、`JobOrchestrator`型の変数を一切保持しない（`_build_scheduler()`の内部で`_build_job_orchestrator()`を呼ぶが、その戻り値は`bootstrap.build_scheduler()`への引数としてのみ使われ、`schedule_now_command`/`list_schedule_command`のスコープには渡らない）。`fetch_stage_command`/`run_workflow_command`は`JobOrchestrator`を直接呼び出すが、これは意図された設計（Task17-2の対象）であり、`Scheduler`経由を要求されていない。**`schedule-now`/`list-schedule`から`JobOrchestrator`への直接アクセス経路は存在しない。**

## 6. fetch/ftp/features/servicesがArchitecture Contractへ適合していること

[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)のGuarantee 15（依存生成責務はComposition Root（`cli/`）に一本化される）は、本文が列挙する対象を`repositories/sqlite/`・`KnowledgeService`・`LearningService`の3種に限定しており、Phase7で追加された`HTTPFetchClient`・`StandardFTPClient`・`DefaultJobOrchestrator`・`DefaultScheduler`を文言上は含まない。実装は上記2節で確認したとおりこの保証の**趣旨**（具象生成箇所の一本化）をPhase7の4クラスにも一貫して適用しており、矛盾するものではない。ただしGuarantee 15の**文面自体**は本Taskの変更禁止対象（`docs/architecture/**`）であるため未修正のまま残る（`RELEASE_STATUS.md`のArchitecture Contract節に記録済み）。Guarantee 1〜14はいずれも中核パイプライン・Repository・Review/Exportに関するものであり、Phase7の4パッケージによる変更を受けない。

`fetch/`・`ftp/`・`features/`・`services/`それぞれの依存禁止制約（`docs/api/package-design.md`）の遵守状況:

- `fetch/`: `document/`〜`validators/`, `models/`, `repositories/`, `ftp/`, `features/`, `services/`, `cli/`への依存禁止 → 実際の依存は`utils/`のみであり違反なし。`pypdf`等のPDF解析ライブラリのimportも0件（PDF本文非アクセス制約を遵守）。
- `ftp/`: `repositories/`, `models/`, `config/`への依存禁止 → 実際の依存は`utils/`のみであり違反なし。
- `features/`: `document/`〜`validators/`, `repositories/`, `pipeline/`, `ftp/`, `fetch/`, `services/`, `cli/`への依存禁止 → 実際の依存は`models/`・`learning/`・`utils/`のみであり違反なし。`pipeline/job_runner.py`から`features`という文字列を含むimportは検出されず、統合は依然未実装のまま（既知の制限として記録済み）。
- `services/`: `repositories/sqlite/`（具象）, `document/`〜`validators/`, `cli/`への依存禁止 → 実際の依存は`export/`, `fetch/`, `ftp/`, `models/`, `pipeline/`, `repositories/`（抽象）, `review/`のみであり違反なし。

**4パッケージともArchitecture Contract・依存禁止制約に適合している。**

## 7. Public API後方互換性

`cli/commands.py`・`cli/app.py`・`cli/bootstrap.py`の既存公開関数（`init_db_command`/`run_pending_command`/`run_job_command`/`review_*_command`/`export_*_command`/`version_command`、`build_settings`/`build_application`/`build_job_runner`等）は、Task17-1〜17-4を通じてシグネチャ・戻り値型のいずれも変更されていない（加算的統合）。既存CLIコマンド9種（`init-db`/`run-pending`/`run-job`/`version`/`review`/`export`/`help`、Task17-2で追加済みの`fetch-stage`/`run-workflow`）は、Task17-4完了後も`app.COMMANDS`に残存し、`tests/unit/cli/test_phase7_scheduler_commands.py`の`test_commands_tuple_includes_scheduler_subcommands`・既存回帰テスト（`test_existing_*`）群で動作確認済みである。新設された2コマンド（`schedule-now`/`list-schedule`）・2関数（`schedule_now_command`/`list_schedule_command`）・1 Builder（`build_scheduler`）はいずれも追加のみであり、既存の`__all__`エントリの削除・改名は発生していない。**Public APIの後方互換性は維持されている。**

## 8. Release Readinessとしての状態

- **Architecture Contract**: Guarantee 1〜15、構造的に維持（Guarantee 15の文面未更新は上記6節のとおり）。
- **ADR**: 全46本`Status: Accepted`のまま、Superseded・本文変更は本Task（変更禁止）でも発生していない。
- **静的検証**: `mypy --strict src/ tests/` → `Success: no issues found in 259 source files`。`ruff check .` → `All checks passed!`。`ruff format --check .` → `382 files already formatted`。
- **テスト**: `pytest --cov` → **816 passed**（0 failed）、TOTAL coverage **98.98%**（`fail_under = 80`を大きく上回る）。Phase6完了時点（634 passed・98.99%）からTask17-1〜17-4で182件のテストが追加された。
- **CLI統合の到達範囲**: `fetch-stage`・`run-workflow`・`schedule-now`・`list-schedule`の4コマンドが利用可能。ただし（a）`ftp/`の実接続情報（`config/`の`FtpSettings`）が未実装のため、`build_ftp_client()`は`FTPConnectionConfig(host="")`というプレースホルダを生成し実FTPサーバへ接続できない、（b）CLIから`JobSchedule`（周期実行対象）を登録する経路が存在しないため`list-schedule`は常に0件を返し、`schedule-now`も人手による都度実行のみが可能で、cron等による自動的な定期実行の経路は存在しない、という2点が残る。
- **未接続のまま残るパッケージ**: `features/`（`JobRunner`への統合が未実装）。

**総合判定**: Phase7が目指した「実装済みだが未配線」の解消（Task17-0の課題設定）は、`fetch/`・`ftp/`・`services/`（`JobOrchestrator`・`Scheduler`）の3パッケージについて完了した。循環依存なし・Composition Root唯一・`Scheduler`は`JobOrchestrator`のみに依存・CLIはProtocol経由のみ利用・`JobOrchestrator`の直接利用箇所なし、という設計上の5要件はいずれも満たされている。一方、実運用への到達（実FTP接続・自動定期実行・`features/`統合・データ整備・セキュリティ強化）にはなお複数の未実装領域が残るため、v1.0.0としての完全な本番リリースには未達のままである（詳細な判定根拠は[`RELEASE_STATUS.md`](../../RELEASE_STATUS.md)を参照）。

## 関連ドキュメント

- [`RELEASE_STATUS.md`](../../RELEASE_STATUS.md) — v1.0.0 Release Candidateのリリース判定（本監査結果を反映）
- [`docs/reports/phase5-final-audit.md`](phase5-final-audit.md) — Phase5時点の詳細監査レポート
- [`docs/phase7-integration-design.md`](../phase7-integration-design.md) — Phase7 Composition Root統合設計（Task17-0）
- [`docs/api/package-design.md`](../api/package-design.md) — パッケージ構成・依存関係（Task17-5で`services/`・`ftp/`・`fetch/`・`cli/`節を更新）
- [`docs/api/dependency-rule.md`](../api/dependency-rule.md) — 依存方向ルール（Task17-5で全体依存グラフを更新）
- [`docs/api/interfaces.md`](../api/interfaces.md) — 公開API定義（Task17-5で`Scheduler`・`JobOrchestrator`節を更新）
- [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) — Architecture Contract（15 Guarantee、本Taskでは変更禁止）
