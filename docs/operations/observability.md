# Observability設計

> **本ドキュメントに実装（コード）はない。** ログ・メトリクス・トレース・ヘルスチェック・アラート・ダッシュボード・SLO/SLI/Error Budget・OpenTelemetry対応方針の設計のみを扱う。実装時は本ドキュメントに従い、`docs/api/python-contract.md`（ログ設計の詳細規約）・`docs/api/pipeline.md`（`PipelineEvent`/`PipelineMetrics`/`PipelineContext`）・`docs/database/schema.md`（`jobs`テーブル）と整合させること。
>
> 本ドキュメントは[`docs/constitution.md`](../constitution.md)の Core Principles「Observability」を、運用レベルで具体化したものである。Constitutionと矛盾する場合はConstitutionが優先される。

## 前提: このシステムの実行モデル

Observabilityの設計は、対象システムの実行モデルに強く依存する。本プロジェクトは以下を前提とする（[ADR-0019](../adr/0019-workflow-orchestration.md), [ADR-0025](../adr/0025-deployment-strategy.md)）。

- **常時稼働サーバーを持たないバッチ実行モデル**である。GitHub Actionsのスケジュール実行により、PDF取得（Fetch）→中核パイプライン→Review→Export→公開（FTP等）の各処理が都度起動・終了する。
- したがって、Webサービスで一般的な「常時稼働のCollector」「HTTPヘルスチェックエンドポイントへのポーリング」「リクエストレイテンシのSLO」はそのままでは適用できない。本ドキュメントは、これらの概念をバッチ・データパイプラインの文脈に翻訳して設計する。
- 処理量は防衛省の発令PDF（不定期・小規模）であり、大規模トラフィックを前提としたサンプリング戦略等は不要である。

## Logging

ログの出力形式・ログレベルの指針・個人情報の扱いは[`docs/api/python-contract.md`](../api/python-contract.md#logging設計)のログ設計を正とする（本ドキュメントでは重複させない）。本ドキュメントでは運用上の側面を補足する。

- **保存先**: 各実行（GitHub Actions runner）はローカルの`logs/`に構造化ログ（JSON Lines）を出力し、実行終了時にワークフロー成果物（Artifact）として、または[ADR-0018](../adr/0018-pdf-registry-and-retention.md)と同様の外部永続ストレージにアップロードする。runnerはジョブ終了後に破棄されるため、runner内に残すだけでは保存にならない。
- **相関**: すべてのパイプライン関連ログは`PipelineContext.correlation_id`（[`pipeline.md`](../api/pipeline.md#pipelinecontext)）を含める。Review・Export等、パイプライン実行後に非同期で発生するイベントは、`job_id` / `pdf_id` / `gold_record_id`等のドメインIDでログを相関させる（`correlation_id`は1回のパイプライン実行に閉じるため、実行をまたぐ相関には使えない）。
- **保持期間**: 既定は1年。それ以前のログは集計サマリ（本ドキュメントの「Metrics」節のスナップショット）のみ残し、生ログは削除してよい。個人情報を含むログの長期保持は、[ADR-0008](../adr/0008-data-ethics-policy.md)の方針（公表範囲を超える保持をしない）に従う。
- **何を残すか**: `PipelineEvent`に対応するINFOログ（各Stageの開始・完了）、`ValidationResult`のWARNING/ERRORログ、Review Domainの状態遷移イベント（[`docs/review/domain.md`](../review/domain.md)）、Export/公開イベント、Job開始・終了。

## Metrics

メトリクスは、常時稼働のメトリクスDB（Prometheus等）を持たない前提のため、各実行の末尾で集計し、構造化ログおよびスナップショットファイルとして出力する。この運用モデルは[`docs/review/metrics.md`](../review/metrics.md#スナップショットの運用)で既に採用されているものと同一とし、Review以外の指標にも適用範囲を広げる。

指標は以下の5カテゴリに分類する。

| カテゴリ | 主な指標 | 主なデータ源 |
|---|---|---|
| パイプライン実行系 | Stage別処理時間（`PipelineMetrics.stage_durations_ms`）、処理件数・失敗件数・スキップ件数 | `PipelineMetrics`（[`pipeline.md`](../api/pipeline.md#pipelinemetrics)） |
| データ鮮度系 | PDF公表日時から取り込み完了までの経過時間分布 | `pdfs.published_date`, `jobs.finished_at` |
| 品質系 | 検証NG率、Confidence分布（band別件数） | `gold_records` / `candidate_records`のconfidence、Validatorの結果 |
| Review系 | Review Time・Correction Rate・Approval Rate等 | [`docs/review/metrics.md`](../review/metrics.md)（既存定義を参照。本ドキュメントでは再定義しない） |
| 運用基盤系 | Job成功率、ジョブ実行時間、GitHub Actions実行コスト（実行時間） | `jobs`テーブル |

Review系メトリクスの定義（Review Time、Correction Rate等の算出式）は[`docs/review/metrics.md`](../review/metrics.md)を正とする。本ドキュメントはそれを「運用基盤系」の他指標と並べて可視化する側であり、指標定義そのものは重複させない。

## Tracing

分散マイクロサービスではないため、複数プロセス間のネットワーク越しトレースではなく、「1件のPDFがFetchからExport/公開に至るまでの処理の流れ」を1つの論理的なトレースとして扱う。

- **トレース境界**: 1トレース = 1回のパイプライン実行（`PipelineContext`）。`correlation_id`をトレースIDとして扱う。
- **スパン構造**: `JobRunner`による実行全体をルートスパンとし、`DocumentAnalyzer`から`Validator`までの各`PipelineStage.run()`呼び出しを子スパンとする。`PipelineEvent`（開始・完了・失敗・スキップ）はスパン内のイベント（span event）に相当する。
- **Reviewの扱い**: Human Reviewは人間の作業ペースに依存し、数時間〜数日かかりうる。パイプライン実行のトレースにブロッキングな子スパンとして含めるのではなく、`gold_record_id` / `review_session_id`で関連付けられた**別トレース**として扱う（Review Domainのライフサイクルは[`docs/review/domain.md`](../review/domain.md)に既に定義されている）。パイプライン実行のトレースとReviewのトレースは、ドメインIDによるリンクで接続する。
- **サンプリング**: 処理量が小規模であるため、全件トレース（サンプリング率100%）を既定とする。将来、処理量が増えてトレース量がコストになった場合に、サンプリング戦略を別途ADRとして検討する。

## Health Check

常時稼働のプロセスがないため、HTTPエンドポイントへの生存確認は成立しない。代わりに「バッチ実行が正しく行われているか」をヘルスの定義とする。

| チェック項目 | 内容 | 判定基準（例。実運用で確定） |
|---|---|---|
| Scheduler Heartbeat | 想定した頻度でGitHub Actionsの定期実行が発生しているか | `jobs.started_at`の最新値が想定インターバルを超えて途絶えていないこと |
| Last Success Check | 各`job_type`の直近の実行が成功しているか | `jobs.status = 'succeeded'`（直近N件中の成功率） |
| Data Freshness Check | 公表済みPDFの取り込みに遅延がないか | `pdfs.published_date`と対応する取り込み完了時刻の差 |
| Dependency Health | Knowledge Base / Layout定義がスキーマとして妥当か | パイプライン実行前のロード時点でのスキーマ検証結果 |
| Storage Health | SQLiteファイル・外部永続ストレージにアクセス可能か | 実行開始時の読み込み・実行終了時の書き戻しの成否 |

これらは独立した常駐ヘルスチェックサービスではなく、ワークフロー実行自体の前段・後段のステップとして実施し、結果を`jobs`テーブルおよびログに記録する。ヘルスチェックの失敗は次節のAlertのトリガーになる。

## Alert

| トリガー条件 | 深刻度 | 通知先・対応 |
|---|---|---|
| `jobs.status = 'failed'`が既定回数連続 | Critical | GitHub Issueを自動起票し、担当者にアサイン（[ADR-0019](../adr/0019-workflow-orchestration.md)の人手対応方針に準拠） |
| Data Freshness Checkの遅延が閾値超過 | Warning | GitHub Issueを起票（自動クローズはしない。人間が原因調査） |
| 検証NG率（Validator失敗率）が急上昇 | Warning〜Critical（閾値により変動） | Knowledge/Layout追加要否の確認を促す通知（Review Domainのキュー優先度にも反映） |
| Error Budget消費率が50%/80%/100%に到達 | Warning（50%）/Critical（80%以上） | 「Error Budget」節の消費ポリシーに従う |
| Reviewキューの滞留（未処理件数・待機時間）が閾値超過 | Warning | [`docs/review/queue.md`](../review/queue.md)の優先度スコアに緊急補正を加え、レビュー担当者に通知 |
| Storage Health / Dependency Healthチェック失敗 | Critical | 実行を中断し、GitHub Issueを起票（データ破損の疑いがあるため自動継続しない） |

- **通知チャネル**: 現時点ではGitHub Issues（既存のCI/CD基盤）を一次チャネルとする。専用の通知サービス（Slack/メール等）の追加は、新たな外部依存の追加であり、[ADR-0025](../adr/0025-deployment-strategy.md)の「保守負荷を増やす追加ベンダー依存を避ける」方針に照らして、必要性が明確になった時点で新規ADRとして検討する。
- **アラート疲れの防止**: 同一条件の重複通知は一定期間（例: 24時間）抑制する。閾値は初期運用で厳しめに倒さず、実際の発生頻度を見ながら調整する。

## Dashboard

常時稼働のダッシュボードサービス（Grafana等）は導入せず、各実行または定期バッチで**静的な状況レポート**を生成する方式を既定とする（[ADR-0025](../adr/0025-deployment-strategy.md)の静的ファイル配信優先の方針と整合させる）。

含めるセクション:

1. パイプライン実行状況（直近の成功/失敗、Stage別処理時間の推移）
2. データ鮮度（公表〜取り込みまでのラグの推移）
3. 品質（検証NG率、Confidence band別件数の推移）
4. Review状況（[`docs/review/metrics.md`](../review/metrics.md)の各指標をそのまま埋め込む）
5. Knowledge/Layout成長（追加件数の推移。Learning Datasetの改善反映率を含む）
6. SLO達成状況・Error Budget消費状況（次節以降を参照）

生成頻度は実行ごとの差分更新に加え、週次で集計レポートを生成する。公開先（`docs/operations/`配下の静的ページとするか、Export成果物と同様の配信経路に載せるか）は実装時に確定する。

## SLO

SLO（Service Level Objective）は、Webサービスの可用性・レイテンシではなく、**データパイプラインとしての信頼性**を表す指標として定義する。数値目標（%や時間の具体的な閾値）は、実運用データが蓄積されるまでは暫定値であり、確定は運用開始後に行う（この点は[`docs/database/schema.md`](../database/schema.md#今後の検討事項スコープ外)等、他の設計文書でも同様に「設計フェーズでは枠組みを定め、数値は運用実績から確定する」方針を踏襲する）。

| SLOカテゴリ | 定義 |
|---|---|
| 可用性SLO | 定期実行（`job_type`別）が成功する月間の割合 |
| 鮮度SLO | 公表されたPDFが一定時間内に取り込まれ、Gold Databaseに反映される月間の割合 |
| 品質SLO | 検証NG（Validator失敗）率が一定以下に収まる月間の割合 |
| Reviewレスポンス SLO | Reviewキューに投入されたレコードが一定時間内にレビュー着手される月間の割合 |

各SLOの算出根拠となる指標（SLI）は次節で定義する。

## SLI

SLI（Service Level Indicator）は、SLOの達成度を実測するための指標であり、既存のテーブル・メトリクス定義から算出する。新しい算出ロジックを個別に作らず、既存のデータモデルに乗せることを優先する。

| SLOカテゴリ | 対応するSLI | 算出根拠 |
|---|---|---|
| 可用性SLO | 期間内の成功Job数 ÷ 総Job数（`job_type`別） | `jobs.status` |
| 鮮度SLO | `pdfs.published_date`から対応するGold反映完了時刻までの経過時間の分布（中央値・p95） | `pdfs`, `jobs.finished_at`, `gold_records` |
| 品質SLO | 検証NG件数 ÷ 検証対象件数（期間内） | Validatorの実行結果（`ValidationResult`の集計） |
| Reviewレスポンス SLO | Reviewキュー投入からレビュー着手までの待機時間分布 | [`docs/review/metrics.md`](../review/metrics.md#review-time)の「Review Time」指標をそのまま採用する（重複定義しない） |

## Error Budget

Error Budgetは「SLO目標を100%から引いた、許容できる失敗量」として、SLOカテゴリごとに定義する。例えば可用性SLOの目標が99%であれば、Error Budgetは残り1%分の失敗（Job失敗）である。

- **測定期間**: SLOと同じ月次ウィンドウでリセットする。
- **消費ポリシー**: Error Budgetの消費率が50%に達した時点でWarningアラートを発報し、原因調査を開始する。80%に達した時点でCriticalアラートとし、当該カテゴリに影響する変更（新様式対応・Knowledgeの大規模追加等、失敗リスクを伴う変更）の優先度を下げ、安定化作業を優先する。100%に達した場合は、そのSLOカテゴリに関わる非必須の変更（新機能・新様式ロールアウト）を、Error Budgetが回復するまで一時的に見合わせる。
- **例外**: 品質SLOに関するError Budgetの消費が、既知の新様式（未対応のLayout）によるものであると特定できている場合は、その様式へのLayout/Knowledge追加自体を最優先作業として進めてよい（安定化と原因解消が同じ作業になるため）。この判断はConstitutionの「Knowledge First」「Pipeline Never Breaks」原則、および[ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位ルールと整合する。
- 具体的な閾値・エスカレーション先の詳細運用は、実運用開始後に`docs/operations/`配下のRunbookとして具体化する。

## OpenTelemetry対応方針

将来的な監視基盤の拡張性を確保するため、**データモデル・命名規約としてのOpenTelemetryは今から採用し、常時稼働のCollector/バックエンドの導入は将来に持ち越す**という段階的な方針を取る。

### 今から採用するもの

OpenTelemetryのTrace / Span / Metric / Logという概念モデルと、Semantic Conventions（属性命名規則）を、本プロジェクトの既存の観測可能性関連の型設計の共通語彙として採用する。既存の型は、意図的にOpenTelemetryの概念と対応するように設計されている。

| 本プロジェクトの既存概念 | OpenTelemetryの対応概念 |
|---|---|
| `PipelineContext.correlation_id`（[`pipeline.md`](../api/pipeline.md#pipelinecontext)） | Trace ID |
| `JobRunner`による1回の実行全体 | Root Span |
| 各`PipelineStage.run()`呼び出し（[`pipeline.md`](../api/pipeline.md#pipelinestage)） | Child Span |
| `PipelineEvent`（[`pipeline.md`](../api/pipeline.md#pipelineevent)） | Span Event |
| `PipelineMetrics`（[`pipeline.md`](../api/pipeline.md#pipelinemetrics)） | Metric（Counter/Histogram相当） |
| 構造化ログ（[`python-contract.md`](../api/python-contract.md#logging設計)のログレベル） | Log Record（Trace ID/Span IDと相関） |

この対応関係により、実装時にOpenTelemetry SDKを導入しても、既存の型の意味を変えずにマッピングできる。

### 今は導入しないもの

常時稼働のOpenTelemetry Collector、および常時稼働の可視化・保管バックエンド（Jaeger、Tempo、Prometheus等の常時稼働サービス）は、現時点では導入しない。[ADR-0025](../adr/0025-deployment-strategy.md)が定める「常時稼働サーバーを持たないバッチ実行モデル」と正面から衝突するためである。

### エクスポート方式（当面の運用）

各実行の終了時に、ログ・メトリクス・トレース情報をOTLP互換の構造化データ（またはそれに変換可能なJSON Lines）としてファイルに出力し、「Logging」節と同じ経路（ワークフロー成果物・外部永続ストレージ）で保存する。常時稼働のCollectorへストリーミング送信するのではなく、実行完了後にまとめて出力する「ファイルベースのエクスポート」を当面の既定とする。

### 将来の移行条件

処理量・実行頻度が増加し、リアルタイムに近い監視・可視化が必要になった時点で、常時稼働のCollector/バックエンドの導入を新規ADRとして検討する。判断基準は[ADR-0019](../adr/0019-workflow-orchestration.md)がGitHub Actionsからの移行を検討する条件（実行時間・頻度の閾値到達）と同様の考え方を用いる。

なお、OpenTelemetry SDKそのものを実装の依存関係として追加する判断は、本ドキュメントの範囲を超える実装時の技術選定であり、`AGENTS.md`の変更ガードレール（依存ライブラリの追加は着手前にADR確認）に従い、実装着手時に改めてADRとして起票する。

## 関連ADR・ドキュメント

- [ADR-0006](../adr/0006-pipeline-provenance.md) — パイプライン段階分割と来歴（Provenance）管理。ログ・トレースの相関設計の前提。
- [ADR-0010](../adr/0010-ci-cd-and-publish-strategy.md) — CI/CDと公開戦略。GitHub Actionsを実行基盤として採用する根拠。
- [ADR-0019](../adr/0019-workflow-orchestration.md) — 実行オーケストレーション戦略。バッチ実行モデル・失敗時の人手対応方針の根拠。
- [ADR-0023](../adr/0023-parser-versioning-policy.md) — Parserバージョニング方針。メトリクス・ログのバージョン相関に関連。
- [ADR-0025](../adr/0025-deployment-strategy.md) — デプロイメント戦略。常時稼働サーバーを持たない前提の根拠。
- [ADR-0026](../adr/0026-security-policy.md) — セキュリティポリシー。ログ・トレースにおける個人情報の扱いに関連。
- [`docs/api/pipeline.md`](../api/pipeline.md) — `PipelineContext` / `PipelineEvent` / `PipelineMetrics` / `PipelineException`の型定義。
- [`docs/api/python-contract.md`](../api/python-contract.md) — ログ出力形式・ログレベルの規約（正）。
- [`docs/database/schema.md`](../database/schema.md) — `jobs`テーブル等、メトリクス・ヘルスチェックのデータ源。
- [`docs/review/metrics.md`](../review/metrics.md) — Review系メトリクスの定義（正）。
- [`docs/workflow/state-machine.md`](../workflow/state-machine.md) — Timeout / Retry Policy / Rollback。ヘルスチェック失敗時の状態遷移との関連。
- [`docs/constitution.md`](../constitution.md) — Core Principles「Observability」。本ドキュメント全体が従属する上位方針。
