# Phase8 Task18-7 — Production Release Validation Report

> 実施日: 2026-07-25。対象: v1.0.0 Release CandidateのProduction Release可否判定。実施内容は（a）読み取り専用のコード・ドキュメント監査、（b）スクラッチ用SQLiteデータベースに対する実CLI実行（`init-db`/`list-schedule`/`schedule-now`/`run-workflow`、いずれも一時ディレクトリ上でのみ実行しリポジトリへの影響なし）、（c）GitHub Actions API（`mcp__github__actions_list`/`actions_get`）による実行履歴の直接確認、の3種類。**コード変更・テスト変更・`.github/`配下の変更は一切行っていない。** 推測による記載は行わず、確認できなかった事項は各節で「未確認」と明記する。
>
> 前提: [`docs/reports/phase7-final-audit.md`](phase7-final-audit.md)（Task17-5、Phase7完了時点の監査）・[RELEASE_STATUS.md](../../RELEASE_STATUS.md)（Task18-6時点）を引き継ぎ、Task18-1（`FtpSettings`）〜Task18-6（Production FTP運用整備）で追加された内容を対象に追加検証する。
>
> **2026-07-25 追記**: 本レポート初版の公開後、運用担当者が実際のProduction FTPサーバに対して「接続確認方法」節の手順を手動実行し、その結果を「5. FTP Upload確認」「6. Secrets確認」「8. Known Limitations確認」「11. Production Ready判定」の各節、および新設した「12. 追記」節に反映した。ホスト名・ユーザー名・パスワード等の実認証情報は本レポートに一切記載しない（運用担当者の手元でのみ扱われ、本セッションには開示されていない）。

## 1. Scheduler実行確認

- **登録状況**: GitHub Actions APIで`.github/workflows/scheduler.yml`が`Scheduler`という名前のワークフロー（workflow_id `320119724`、`state: active`）としてリポジトリのデフォルトブランチ上に登録済みであることを確認した（`created_at: 2026-07-25T15:39:47+09:00`）。
- **YAML構文**: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/scheduler.yml')); print('OK')"` → `OK`（Task18-6で確認済みの内容を本Taskでも変更していないため再確認のみ）。
- **実行履歴**: GitHub Actions API（`list_workflow_runs`、`resource_id=scheduler.yml`）で確認した結果、**`total_count: 0`**。cron（毎日17:45 JST）・`workflow_dispatch`いずれによる実行も、本レポート作成時点で一度も発生していない。
- **CLI経路の妥当性**: スクラッチDBに対し`schedule-now run_pending_pipeline`を実行し、未処理PDFが0件の状態で`no pending job: no pending pdf to process`（終了コード0）が返ることを実測で確認した（Task18-4で確定した仕様どおり）。`list-schedule`は`0 upcoming schedule(s)`（終了コード0）を返し、`_build_scheduler()`が常に空タプルを渡す既存契約（RELEASE_STATUS.mdのPhase8開始前の残課題一覧 項目2）と一致することを確認した。
- **判定**: ワークフロー自体・CLI呼び出し経路は構造的に妥当であることを実測で確認したが、**GitHub Actions runner上での実際のcron起動実績は未確認（実行履歴ゼロ）**。次回のcron到来（毎日17:45 JST）を待たない限り、実運用環境での動作は検証できない。

## 2. GitHub Actions確認

GitHub Actions APIで4ワークフローすべての登録状況・実行履歴を確認した。

| ワークフロー | 登録状況 | 実行履歴 |
|---|---|---|
| `ci.yml` | 登録済み（`pull_request`・`main`へのpush） | 実行多数（過去のTask17-x/18-xのPRマージ履歴から間接的に推定されるが、本Taskでは出力サイズの制約により全件の合否詳細は取得していない。**個々の実行結果は未確認**） |
| `nightly.yml` | 登録済み（`schedule`・`workflow_dispatch`） | 3回実行。run1（2026-07-22）成功、run2（2026-07-23、`ruff format check`ステップで失敗、mypy/pytestはskip）、run3（2026-07-24、最新）成功。run2の失敗はTask18系の変更に先行する時点のものであり、本Taskの対象範囲外のため原因の追加調査は行っていない（既に後続のci/nightly成功で解消していることのみ確認） |
| `release.yml` | 登録済み（`workflow_dispatch`・`v*`タグpush） | **`total_count: 0`**。タグpush・手動実行いずれも一度も発生していない |
| `scheduler.yml` | 登録済み（上記1.参照） | **`total_count: 0`**（上記1.参照） |

- **判定**: 4ワークフローとも構文・登録状態は正常。ただし`release.yml`・`scheduler.yml`は実行実績が皆無であり、**Production環境での実動作は未確認**。`nightly.yml`は直近の実行が成功しているが、`ci.yml`の全件詳細は本Taskの調査範囲では取得しきれておらず**未確認**とする。

## 3. CLI確認

スクラッチディレクトリ（リポジトリ外）に一時SQLiteデータベースを作成し、以下のコマンドを実際に実行した（結果はいずれも実測、推測ではない）。

| コマンド | 実行結果 | 終了コード |
|---|---|---|
| `init-db` | `database initialized` | 0 |
| `list-schedule` | `0 upcoming schedule(s)` | 0 |
| `schedule-now run_pending_pipeline` | `no pending job: no pending pdf to process` | 0 |
| `run-workflow json <dest>`（`--remote-path`なし） | `fetched 0 pdf(s)` / `processed 0 pipeline job(s)` / `pending_reviews: 0` / `export: format=json record_count=0 sha256=...` | 0 |

いずれも`tests/integration/cli/test_phase7_scheduler_cli.py`・`tests/integration/cli/test_phase7_cli_workflow.py`等が検証する契約と一致する実測結果であり、CLI層の構造的な健全性を実運用に近い形（実際のプロセス起動・実際のSQLite I/O）で再確認した。

- **判定**: CLIの主要コマンド（`init-db`/`list-schedule`/`schedule-now`/`run-workflow`）は実測で正常動作を確認した。

## 4. Export確認

上記3.の`run-workflow json`実行により、`ExportService`経由のJSON Export（レコード0件のフィクスチャDBに対する空Export）が実際に成功し、SHA-256チェックサム付きの`export: format=json record_count=0 sha256=...`が出力されることを実測確認した（[ADR-0022](../adr/0022-export-policy.md)のExport Policy・[ADR-0029](../adr/0029-export-integrity-and-audit-log-policy.md)のチェックサム整合性）。CSV/Parquet Export・実データを含むExportについては、`tests/integration/export/`配下の既存結合テスト（`test_export_personnel_records.py`・`test_export_csv_parquet.py`・`test_export_with_metadata.py`）が引き続き全件成功していることを`pytest`実行で確認した（下記「検証結果」参照）。Export機能自体はCLIコマンドとして未公開のまま（RELEASE_STATUS.mdのKnown Limitations 6、本Taskでは変更していない）。

- **判定**: Export（JSON）は実測で正常動作を確認した。CSV/Parquet・完全性メタデータはテストスイート経由での確認に留まる（実データでの実行は本Taskでは行っていない）。

## 5. FTP Upload確認

- **実装確認**: `services/orchestrator.py`の`export_and_publish()`が`FTPClient.connect()`/`upload()`/`disconnect()`を呼び出す実装であることをコード確認済み（Task18-2で既に完成していたことをTask18-2完了報告時に確認済み、本Taskでは変更なし）。
- **プレースホルダ接続の実測**: FTP関連環境変数（`MOD_PERSONNEL_DB_FTP__*`）を一切設定しない状態で`run-workflow json <dest> --remote-path /incoming/test.json`を実行したところ、以下のとおり`FTPConnectionError`が送出され、終了コード1で異常終了することを実測確認した。

  ```
  mod_personnel_db.ftp.exceptions.FTPConnectionError: FTPサーバへの接続に失敗しました: :21
  ```

  これは`docs/operations/release.md`の「Production FTP運用」節が記す「`MOD_PERSONNEL_DB_FTP__HOST`が未登録の場合、`build_ftp_client()`はプレースホルダ（`FTPConnectionConfig(host="")`）を返すため、接続自体が空ホストへの接続として失敗する」という説明と一致する実測結果である。
- **追加の観察事項（Known Limitation）**: 上記実行時、`FTPConnectionError`は`cli/app.py::main()`の`except CliCommandError`にも`except NoPendingJobError`にも該当せず、捕捉されないまま Python の生トレースバックとして出力された（`CliCommandError`のサブクラスではないため）。ユーザー向けの整形されたエラーメッセージにはならない。本Taskの変更禁止スコープ（`src/**`）によりコード修正は行わず、事実として記録するに留める（「Known Limitations確認」節に追記）。
- **実サーバへの接続確認**: 本Task初版の時点では、本Taskの実行環境からProduction FTPサーバへの実接続は行っていなかった（実サーバのホスト名・認証情報を本セッションは保持していない）。
- **2026-07-25 追記（運用担当者による実地検証）**: 運用担当者が、README.mdの「接続確認方法」手順に従い、実際のProduction FTPサーバに対して`run-workflow --remote-path`を手動実行した。結果は以下のとおり。
  - **接続・認証（`connect()`→`login()`）は成功した。** 発生した例外が`FTPConnectionError`ではなく`FTPTransferError`（`upload()`内部）であったことから、`StandardFTPClient.connect()`（TCP接続＋`ftplib.FTP.login()`）は正常に完了していたと判断できる。これにより「実FTPサーバへの接続実績」は**確認済み**に更新する。
  - **アップロード（`STOR`）は失敗した。** サーバから`530 You cannot upload file here`が返された。この時点で`--remote-path`には絶対パス（例: `/incoming/_connectivity_check_<timestamp>.json`）を指定していた。
  - **原因をコード読解で特定した**: `ftp/config.py`の`FTPConnectionConfig`には`remote_directory`フィールドが存在せず、`cli/bootstrap.py`の`build_ftp_client()`も`FtpSettings.remote_directory`をマッピングしていない。さらに`ftp/client.py`の`StandardFTPClient.connect()`は`cwd()`を一切呼び出さない。したがって`MOD_PERSONNEL_DB_FTP__REMOTE_DIRECTORY`（Task18-6でSecrets一覧に追加した6項目の1つ）は**現在のコードでは静かに無視される**。ログイン直後のカレントディレクトリ（サーバ既定、多くの場合ホームディレクトリまたはchrootのルート）に対して、`--remote-path`に渡した絶対パスがそのまま`STOR`されるため、そのFTPアカウントの書き込み許可範囲外のパスを指してしまい`530`になったと推定される（推定である旨を明記。サーバ側の正確な権限設定は運用担当者・FTPサーバ管理者のみが確認可能であり、本セッションからは**未確認**）。
  - **切り分け・是正の推奨手順**: (1) `--remote-path`をファイル名のみの相対パスにして再試行し、ログイン直後のディレクトリへの書き込み可否を切り分ける、(2) FTPサーバ管理者に当該アカウントの書き込み許可ディレクトリを確認してもらう、(3) 許可ディレクトリが判明次第、そのフルパスを`--remote-path`に指定する。`remote_directory`をコード側で実際に`cwd()`する改修（`src/**`変更）は本Taskの範囲外であり、実施する場合は別Taskとする。
- **判定（更新後）**: 実FTPサーバへの**接続・認証は実測で確認済み**。**アップロード（実際のファイル到達）は現時点でも未確認**（`530`により失敗、原因はコード側の`remote_directory`未配線と権限設定の組み合わせであることをコード読解で特定したが、切り分け・是正はまだ完了していない）。

## 6. Secrets確認

- **登録状況の直接確認**: 本セッションが利用可能なGitHub MCPツールにはActions Secretsの一覧・登録状況を取得する手段が含まれていない（Secret値はGitHub側の設計上、API経由でも再表示されない）。したがって、`MOD_PERSONNEL_DB_FTP__HOST`等6件のSecretsが対象のGitHub Environmentに実際に登録されているかどうかは**未確認**。
- **間接的な確認（代替）**: 上記5.のとおり、Secrets未設定を模したローカル実行では、ドキュメント記載どおりのプレースホルダ接続失敗を再現できた。これは「Secretsが未登録の場合の挙動」がドキュメントとコードで一致していることの確認であり、「Secretsが登録されているかどうか」自体の確認ではない。
- **Secret名とコードの対応**: `MOD_PERSONNEL_DB_FTP__HOST`/`_PORT`/`_USERNAME`/`_PASSWORD`/`_REMOTE_DIRECTORY`/`_TIMEOUT`の6件が、`.github/workflows/scheduler.yml`（Task18-6で追加）の`env:`ブロックと`config/ftp.py`の`FtpSettings`フィールド名に矛盾なく対応していることをファイル読み合わせで確認した（本Taskで`.github/**`は変更していない）。
- **判定**: Secret名・コード側の対応関係は構造的に確認できたが、**実際のGitHub Environmentへの登録状況・値の正しさは未確認**（運用側の責任範囲であり、本セッションからは検証不能）。
- **2026-07-25 追記**: 運用担当者による手動検証（上記5.参照）では、シェル環境変数として手動で入力した認証情報（`MOD_PERSONNEL_DB_FTP__HOST`/`_USERNAME`/`_PASSWORD`等）でFTPログインが成功した。これは**認証情報の値そのものが有効であること**を示すが、**GitHub Actions（`scheduler.yml`）のProduction Environmentに同じ値がSecretsとして正しく登録されているかどうかを直接証明するものではない**（手動検証はローカルのシェル変数経由であり、GitHub Secrets経由の実行ではないため）。GitHub Environmentへの実登録状況は引き続き**未確認**のまま残る。

## 7. Rollback手順確認

[`docs/operations/release.md`](../operations/release.md)に既存の手順が包括的に定義されていることを確認した（本Taskでの新規追加はなし、内容の整合性のみ確認）。

| 節 | 内容 | 確認結果 |
|---|---|---|
| Rollback（コードリリース） | 直前の正常なリリースタグへのRevert、次回スケジュール実行での自動反映、`gold_records`は自動訂正されない旨 | 記述は[ADR-0023](../adr/0023-parser-versioning-policy.md)・[ADR-0025](../adr/0025-deployment-strategy.md)・[ADR-0006](../adr/0006-pipeline-provenance.md)と矛盾なし |
| Rollback（データ） | `Approved`後の真のロールバックは行わずCompensating Actionで訂正 | [`docs/workflow/state-machine.md`](../workflow/state-machine.md#rollback)と整合（本Taskでは同ファイルを変更していない） |
| Recovery | 実行途中異常終了・排他ロックのスタック・ストレージ障害への対応 | [ADR-0025](../adr/0025-deployment-strategy.md)のバッチ実行モデルと整合 |
| Disaster Recovery | DB/PDF Registry/リポジトリ/署名鍵/Secrets喪失シナリオごとの復旧方針 | 表形式で網羅されている |
| Maintenance Window | スケジュール実行の一時無効化としての定義 | `schedule: cron`無効化という具体手順まで明記 |

- **実地訓練の実績**: 上記手順が実際にリハーサル・DR訓練として実行された記録は本リポジトリ内に見当たらない（`docs/operations/release.md`自身も「DR訓練: ...頻度・具体的な訓練手順は実装後にRunbookとして確定する」と自己申告している）。**手順のドキュメント上の整合性は確認したが、実地での動作確認は未確認。**
- **判定**: 手順は文書化されており既存ADRと矛盾しない。実地検証は未実施（未確認）。

## 8. Known Limitations確認

[RELEASE_STATUS.md](../../RELEASE_STATUS.md)のKnown Limitations（13件、Task18-6時点）を再確認し、Task18-7時点での差分は以下のとおり。

- 項目1・2・4〜13は本Taskの調査範囲において状態に変化なし（コード変更を伴わない監査Taskのため）。
- 項目3（`ftp/`・自動実行経路）は、実測（上記1・5）により「Secrets未設定時のプレースホルダ接続失敗」という記述済みの挙動を再確認できた。加えて、本Taskで新たに次の事実を確認した。
  - **新規確認事項A**: `FTPConnectionError`が`cli/app.py::main()`で捕捉されず生トレースバックとして出力される（上記5.参照）。ユーザー向けCLIとしてはエラーメッセージの整形余地があるが、`src/**`変更禁止のため本Taskでは是正しない。
  - **新規確認事項B**: `scheduler.yml`・`release.yml`はいずれも実行履歴がゼロであり、GitHub Actions上での実動作は未検証のまま本番判定を迎えている（上記1・2参照）。
- **判定**: 既存Known Limitationsの記述は現時点でも正確である。新規確認事項A・Bを追加の限界事項として本レポートに記録した（RELEASE_STATUS.md本体への転記は次節「4. Architecture Contract整合性確認」後のRELEASE_STATUS.md更新で行う）。
- **2026-07-25 追記・新規確認事項C**: 運用担当者による実FTPサーバ検証（上記5.参照）で、`FtpSettings.remote_directory`（Task18-1で追加、Task18-6でGitHub Secretsにも追加した`MOD_PERSONNEL_DB_FTP__REMOTE_DIRECTORY`に対応するフィールド）が、`FTPConnectionConfig`（`ftp/config.py`）にそもそもフィールドとして存在せず、`build_ftp_client()`（`cli/bootstrap.py`）でもマッピングされず、`StandardFTPClient.connect()`（`ftp/client.py`）も`cwd()`を呼ばないため、**実行時に一切参照されない**ことをコード読解で確認した。運用者が`_REMOTE_DIRECTORY`を設定していても無視され、`--remote-path`に渡した絶対パスがサーバ側の権限範囲外であれば`530`エラーでアップロードが失敗する（実測で再現済み）。これは新規確認事項A・Bと並ぶ第3の確認事項であり、`src/**`変更を要する是正（`remote_directory`を用いた`cwd()`呼び出しの追加、または`--remote-path`との統合方針の設計）は本Taskの範囲外のため実施していない。

## 9. Remaining Work確認

[docs/operations/release.md](../operations/release.md#release-candidateからv100正式版までの残タスク)の残タスク表を再確認した。Task18-1〜18-6の完了により「Scheduler自動実行」行は「本体・CLI統合・自動起動経路・FTP Secrets整備まで完了」の状態にあるが、本Taskの実測（上記1・2・6）により、**「整備済み」と「実運用で動作確認済み」は区別する必要がある**ことが判明した。具体的には、`ftp/`実接続情報整備（Task18-1）・cron自動実行の仕組み自体（Task18-3〜18-5）は完了しているが、（a）実FTPサーバへの接続実績、（b）GitHub Actions runner上でのcron実行実績、（c）GitHub Secretsの実登録確認、の3点はいずれも本Taskでも依然として未確認のまま残る。他の残タスク（データ整備・`features/`統合・セキュリティ強化・リリース自動化・スキーマMigration基盤・残りのテスト層）は、Task18-1〜18-7のいずれでも対象になっておらず、変化なし。

## 10. Architecture Contract整合性確認

[`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md)が定めるGuarantee 1〜15（見出し行`## 1.`〜`## 15.`を`grep`で直接確認、全15件の存在を確認）について、Task18-1〜18-6で変更されたファイル（`config/ftp.py`, `config/settings.py`, `cli/bootstrap.py`, `cli/app.py`, `.github/workflows/scheduler.yml`, ドキュメント各種）が抵触しないことを確認した。

- **Guarantee 15（依存生成責務はComposition Rootに一本化される）**: `FtpSettings`・`AppSettings.ftp`はいずれも`pydantic.BaseModel`のデータ構造であり、`build_ftp_client()`（`cli/bootstrap.py`）内でのみ`FTPConnectionConfig`へマッピングされる。Task18-1〜18-6のいずれの変更も、`StandardFTPClient`等の具象クラスを`cli/bootstrap.py`以外の箇所からインスタンス化するものではない（Phase7時点でTask17-5が確認した性質から変化なし）。
- **Guarantee 7（RepositoryがSQLiteを隠蔽する）・Guarantee 8/9（Reviewのみがgold_recordsを書き換える）**: Task18-1〜18-6はいずれも`repositories/`・`review/`を変更していないため、影響なし。
- **本Taskの変更（`docs/reports/phase8-release-validation.md`新設、`RELEASE_STATUS.md`更新）**: いずれもコードではなくドキュメントであり、Architecture Contractが規定する実装上の保証そのものには影響しない。
- **`docs/architecture/**`は本Taskのスコープ外（変更禁止）であるため、Guarantee本文への変更は一切行っていない。**
- **判定**: Architecture Contract 15/15と、Task18-1〜18-7で行われた変更（実装済み分・本Taskのドキュメント変更分）との間に矛盾は確認されなかった。

## 11. Production Ready判定

**Release Candidate maintained**

以下の理由により、「Ready for v1.0.0 Release」と「Not Ready」のいずれの断定も避け、Phase6 Task15-4以来維持されている「Release Candidate」の状態を継続することが妥当と判断する。

- **v1.0.0 Release Recommendation（Ready）を選ばない理由**: 上記5・6・1・2で確認したとおり、（a）実FTPサーバへのアップロード成功、（b）GitHub SecretsのProduction Environmentへの実登録、（c）`scheduler.yml`のGitHub Actions runner上での実行実績、の3点がいずれも未確認のまま残っている。これらは「継続的にPDFを収集・公開する」というプロジェクトの中核機能が実運用で動作することの直接的な証拠であり、証拠が揃わない状態でのReady判定はしない。
- **Not Readyを選ばない理由**: 構造面（Architecture Contract 15/15維持、ADR間の矛盾ゼロ、依存方向の一方向性）・実装面（CLI主要コマンドの実測動作確認、Export実行成功、FTP未設定時の失敗挙動がドキュメントどおりであることの実測確認）はいずれも本Taskの実測により裏付けられており、「構造的な欠陥がある」という意味でのNot Readyではない。未確認事項は実装の欠陥ではなく、本番環境（実FTPサーバ・実Secrets・実cron起動）に依存する運用上の検証待ちである。
- **推奨される次のアクション**: 実運用担当者が、（1）Production GitHub EnvironmentへのSecrets登録を実施・確認し、（2）`workflow_dispatch`による`scheduler.yml`の手動初回実行、または次回cron到来（毎日17:45 JST）を待って実行結果を確認し、（3）`run-workflow --remote-path`を実FTPサーバに対して一度手動実行して接続・アップロードの成功を確認する。この3点が確認され次第、改めてRelease Validationを実施し「Ready for v1.0.0 Release」への昇格を判断することを推奨する（本Taskの範囲外の提案であるため、実施は別Taskとする）。
- **2026-07-25 追記**: 上記（3）を運用担当者が実際に試行した結果、**接続・認証（`connect()`/`login()`）は成功したが、アップロード（`STOR`）は`530`エラーで失敗した**（上記5.参照）。原因はコード側の`remote_directory`未配線（新規確認事項C、上記8.参照）と、FTPサーバ側の書き込み権限設定の組み合わせと推定される。この結果、判定は引き続き**Release Candidate maintained**を維持するが、根拠がより具体的になった。「未確認だから判定を保留する」状態から、「実接続は確認できたが、アップロード自体にコード上の欠陥（`remote_directory`未配線）が新たに判明したため、その是正または回避策の確立が完了するまでReadyにはできない」という、より明確な理由に更新する。是正（`src/**`変更）は本Taskの範囲外のため、別Taskでの対応を推奨する。

## 検証結果

- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/scheduler.yml')); print('OK')"` → `OK`（本Taskでは同ファイルを変更していないため再確認のみ）
- `poetry run mypy --strict src/ tests/` → `Success: no issues found in 261 source files`
- `poetry run ruff check .` → `All checks passed!`
- `poetry run ruff format --check .` → `387 files already formatted`（本レポート追加により386→387）
- `poetry run pytest --cov` → `833 passed`、TOTAL coverage `98.98%`（`fail_under = 80`を大きく上回る。Phase8 Task18-6完了時点から件数・カバレッジとも変化なし。本Taskはsrc/tests変更を伴わないため）
- CLI実測（`init-db`/`list-schedule`/`schedule-now`/`run-workflow`、`run-workflow --remote-path`によるFTP接続失敗の再現）→ 上記1〜5節に記載のとおり、いずれも実行しドキュメント記載と一致する結果を得た
- **2026-07-25 追記**: 運用担当者による実Production FTPサーバへの手動接続確認 → `connect()`/`login()`成功、`upload()`（`STOR`）は`530 You cannot upload file here`で失敗。原因は`ftp/config.py`の`FTPConnectionConfig`に`remote_directory`フィールドが存在しないこと、`cli/bootstrap.py`の`build_ftp_client()`が`FtpSettings.remote_directory`をマッピングしていないこと、`ftp/client.py`の`StandardFTPClient.connect()`が`cwd()`を呼ばないことをコード読解で特定した（詳細は上記5.参照）。この追記に伴うコード変更（`src/**`）は本セッションでは一切行っていない。

## 13. 追記サマリ（2026-07-25、運用担当者による実地検証を反映）

| 項目 | 初版（Task18-7時点） | 追記後（本日時点） |
|---|---|---|
| 実FTPサーバへの接続・認証 | 未確認 | **確認済み**（`connect()`/`login()`成功を実測） |
| 実FTPサーバへのアップロード成功 | 未確認 | **未確認のまま**（`530`で失敗、原因はコード側の`remote_directory`未配線＋サーバ側権限設定と推定） |
| GitHub SecretsのProduction Environment登録 | 未確認 | **未確認のまま**（手動検証はローカルのシェル変数経由であり、GitHub Secrets経由の実行ではないため） |
| `scheduler.yml`/`release.yml`のGitHub Actions実行実績 | 実行履歴0件（未確認） | 変化なし（本追記調査の対象外） |
| Production Ready判定 | Release Candidate maintained | **Release Candidate maintained（変更なし、ただし根拠がより具体的に）** |
| 新規判明事項 | — | `remote_directory`（`MOD_PERSONNEL_DB_FTP__REMOTE_DIRECTORY`）が実行時に一切参照されないコード上の欠落（新規確認事項C、上記8.参照） |

## 関連ドキュメント

- [RELEASE_STATUS.md](../../RELEASE_STATUS.md) — 本レポートの判定を反映した最新のRelease Readiness記録
- [`docs/reports/phase7-final-audit.md`](phase7-final-audit.md) — Phase7完了時点の監査（Task17-5）
- [`docs/operations/release.md`](../operations/release.md) — Release Flow・Scheduler運用フロー・Production FTP運用・Rollback/Recovery/Disaster Recovery
- [`docs/phase8-integration-design.md`](../../docs/phase8-integration-design.md) — Phase8統合設計（Task18-0）
- [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) — Architecture Contract（15 Guarantee、本Taskでは変更していない）
