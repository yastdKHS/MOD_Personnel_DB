# Test Policy

> 本ドキュメントは[`docs/implementation.md`](../implementation.md)の「Testing Rule」が参照する正の文書であり、8種類のテストそれぞれについて、目的・責務・実行タイミング・GitHub Actionsでの位置づけ・成功条件・失敗時の対応・Coverage対象・Coverage目標を定義する。実装（テストコード）は含まない。既存のGolden Test戦略（[ADR-0007](../adr/0007-golden-file-testing.md)）・Benchmark Dataset戦略（[ADR-0020](../adr/0020-benchmark-dataset.md)）を上書きせず、それらを本ドキュメントの枠組みの中に位置づける。

## テスト種別の全体像

本プロジェクトのテストは、目的の異なる8種類に分類する。数値目標（Coverage目標・具体的な閾値）は、実装が存在しない現時点では暫定であり、実装着手後の実績に基づき調整する（[`docs/operations/observability.md`](../operations/observability.md)のSLO同様、暫定値であることを明示する誠実さを優先する）。

| # | 種別 | 一言でいうと |
|---|---|---|
| 1 | Unit Test | 個々の関数・クラスは正しいか |
| 2 | Integration Test | 複数コンポーネントは正しく協調するか |
| 3 | Golden Test | 実際のPDF様式を最後まで正しく処理できるか |
| 4 | Regression Test | 過去の誤りは再発していないか |
| 5 | Performance Test | 処理時間・リソース消費は許容範囲か |
| 6 | Acceptance Test | 利用者・レビュー担当者から見て期待通りか |
| 7 | Benchmark Test | 全体としてどの程度正確に抽出できているか |
| 8 | Mutation Test（将来） | テストスイート自体は有効か |

## Unit Test

| 項目 | 内容 |
|---|---|
| 目的 | 個々の関数・クラス単位でロジックの正しさを検証する |
| 責務 | `models/`, `extractors/`, `normalizers/`, `validators/`等ロジックを持つ全パッケージの、単一の関数・メソッド・小さな単位の振る舞いを検証する。外部依存（Repository・I/O）は`Protocol`を利用してモック化する（[`docs/api/python-contract.md`](../api/python-contract.md#protocol利用方針)の「テスト用モックが書きやすい」という設計上の利点をそのまま活用する） |
| 実行タイミング | PRごと（CI）。ローカルでは`pre-commit`と独立して開発者が随時実行する |
| GitHub Actionsでの位置づけ | `.github/workflows/ci.yml`の`test`ジョブ（既存の`pytest --cov`ステップ）。`tests/unit/`配下を対象とする |
| 成功条件 | 全テストがパスする。新規・変更されたロジックに対応するテストが存在する（機械的強制は困難なため、コードレビューで確認する） |
| 失敗時の対応 | PRをブロックし、マージ不可とする |
| Coverage対象 | `src/mod_personnel_db/`全体のうち、ロジックを持つパッケージ（`models/`, `extractors/`, `normalizers/`, `validators/`, `services/`, `review/`等）。`config/`, `utils/`は薄いため目標を緩める |
| Coverage目標 | 80%（暫定値）。`pyproject.toml`の`[tool.coverage.run]`に`fail_under`として実装時に設定する |

## Integration Test

| 項目 | 内容 |
|---|---|
| 目的 | 複数コンポーネントを跨いだ結合動作を検証する |
| 責務 | 中核パイプラインの複数段階の連携（例: Section Parser→Field Extractor→Normalizer）、`UnitOfWork`を介した複数Repositoryにまたがる操作の原子性を検証する（[`tests/README.md`](../../tests/README.md)の既定構成`tests/integration/`） |
| 実行タイミング | PRごと（CI） |
| GitHub Actionsでの位置づけ | `ci.yml`の`test`ジョブ内、`tests/integration/`配下として実行。実行時間が伸びた場合はUnit Testと別ジョブへの分離を検討する |
| 成功条件 | 全テストがパスする |
| 失敗時の対応 | PRをブロックし、マージ不可とする |
| Coverage対象 | パイプライン段階間の連携部分、`repositories/sqlite/`の実装（実SQLiteに対する統合検証） |
| Coverage目標 | 数値目標は設けない。主要な結合経路（中核パイプライン全段階の直列実行、`UnitOfWork`のcommit/rollback）を最低1シナリオずつ持つことを質的基準とする |

## Golden Test

既存の[ADR-0007](../adr/0007-golden-file-testing.md)が定める戦略をそのまま適用する。

| 項目 | 内容 |
|---|---|
| 目的 | PDFパースのような「入力の微妙な違いが出力に大きく影響しうる」処理の回帰を検知する（[ADR-0007](../adr/0007-golden-file-testing.md)） |
| 責務 | `sample_pdfs/`の各ファイルをパイプラインに通した結果が`sample_outputs/`と一致することを検証する |
| 実行タイミング | PRごと（CI）。新しい`layouts/`定義を追加する変更では必須 |
| GitHub Actionsでの位置づけ | `ci.yml`の`test`ジョブ（`tests/golden/`配下、既存の`pytest`実行に含まれる）。将来的には`layout-validation.yml`（[`.github/workflows/README.md`](../../.github/workflows/README.md)の「今後追加予定」）として専用化することを検討する |
| 成功条件 | すべての`sample_pdfs/`が対応する`sample_outputs/`と一致する |
| 失敗時の対応 | 不一致が「バグ」か「意図的な正解変更」かを人手で判定する。後者の場合はゴールデンファイルを更新し、PR説明に変更理由を明記する（無言で更新しない、[`CLAUDE.md`](../../CLAUDE.md)） |
| Coverage対象 | `layouts/`の全`era_id`（様式）に対する代表サンプル |
| Coverage目標 | 全`era_id`に対し最低1サンプル（[`sample_pdfs/README.md`](../../sample_pdfs/README.md)の選定基準に従う） |

## Regression Test

| 項目 | 内容 |
|---|---|
| 目的 | Learning Dataset（[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md)）に記録された過去の誤りが再発していないことを検知する |
| 責務 | `learning_dataset.status='verified'`（`regression_status='passed'`が確定条件、[`docs/api/models.md`](../api/models.md)の`LearningRecord`）となった各エントリに対応する再発防止テストケースを蓄積・実行する |
| 実行タイミング | PRごと（CI） |
| GitHub Actionsでの位置づけ | `ci.yml`の`test`ジョブ内、`tests/regression/`（またはGolden Testに統合、実装時に判断）。Golden Testとの違いは、対象が「様式の網羅」ではなく「個別に発覚した誤り」である点 |
| 成功条件 | 全テストがパスする |
| 失敗時の対応 | PRをブロックする。再発が確認された場合、対応する`learning_dataset`エントリの`regression_status`を`failed`に戻す運用とする（[`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md)のライフサイクル） |
| Coverage対象 | `learning_dataset.status='verified'`の全エントリ |
| Coverage目標 | 100%（`verified`と判定するための必要条件が`regression_status='passed'`であるため、定義上ほぼ全件が対象になる） |

## Performance Test

| 項目 | 内容 |
|---|---|
| 目的 | 処理時間・メモリ使用量が許容範囲内であることを検証する。特にDocument Analyzer段階のリソース上限（[ADR-0026](../adr/0026-security-policy.md)が要求する「異常なPDFがパイプライン全体を停止させない」ための上限）を確認する |
| 責務 | 大きいPDF・異常なPDF（圧縮爆弾等を想定した合成データ）に対するリソース消費の上限を確認する |
| 実行タイミング | PRごとには実行しない（コスト高）。定期実行（週次を既定候補とする）およびリリース前（[`docs/operations/release.md`](../operations/release.md#release-flow)の`staging`検証時） |
| GitHub Actionsでの位置づけ | 専用ワークフロー（実装時に新設、`ci.yml`とは分離） |
| 成功条件 | 処理時間・メモリ使用量が閾値内。具体的な閾値は実装後のベースライン計測を経て確定する（暫定値なし） |
| 失敗時の対応 | 初期運用ではブロッキングとせず、警告として人手確認を促す。閾値が安定した段階でブロッキング化を検討する |
| Coverage対象 | Document Analyzer段階（最もリスクが高い、[ADR-0026](../adr/0026-security-policy.md)）、大規模Backfill相当の一括処理（[`docs/operations/release.md`](../operations/release.md#backfill)） |
| Coverage目標 | 定量目標は初期運用データの蓄積後に確定する（暫定） |

## Acceptance Test

| 項目 | 内容 |
|---|---|
| 目的 | 利用者（公開JSON利用者、レビュー担当者）から見て期待通りに機能することを検証する |
| 責務 | 公開JSON/CSV/Parquetが公開契約（[`docs/database/json_schema.md`](../database/json_schema.md)のJSON Schema Draft 2020-12）に適合することの検証、Review Lifecycle（[`docs/review/domain.md`](../review/domain.md)）を通した承認フロー全体のE2E確認 |
| 実行タイミング | リリース前（`staging`環境、[`docs/operations/release.md`](../operations/release.md#release-flow)のRelease Flow手順5） |
| GitHub Actionsでの位置づけ | リリース関連ワークフロー（`release.yml`、[`.github/workflows/README.md`](../../.github/workflows/README.md)の「今後追加予定」）の一部 |
| 成功条件 | 公開JSON SchemaのValidationに合格する。Review E2Eシナリオ（承認・差し戻し・再レビュー）に合格する |
| 失敗時の対応 | `staging`から`production`への昇格をブロックする（[`docs/operations/release.md`](../operations/release.md#release-flow)） |
| Coverage対象 | 公開契約（JSON Schema全体）、Review Lifecycleの主要な状態遷移経路（[`docs/review/domain.md`](../review/domain.md)） |
| Coverage目標 | JSON Schemaは全必須フィールドを100%カバー。Review E2Eは主要遷移（承認・差し戻し・再レビュー）を最低1シナリオずつ |

## Benchmark Test

既存の[ADR-0020](../adr/0020-benchmark-dataset.md)が定める戦略をそのまま適用する。

| 項目 | 内容 |
|---|---|
| 目的 | 「全体としてどの程度正確に抽出できているか」という量的な品質指標を継続的に計測する（[ADR-0020](../adr/0020-benchmark-dataset.md)。Golden Testの「壊れていないか」という回帰検知とは目的が異なる） |
| 責務 | 新しい`parser_version`のリリースごとに、ベンチマークデータセット全体に対して評価を実行し、様式・期間別のValidator通過率、Confidence分布、Learning Datasetの新規発生率を算出する |
| 実行タイミング | リリースタグ付与時（[`docs/operations/release.md`](../operations/release.md#release-flow)の手順4〜5の間） |
| GitHub Actionsでの位置づけ | `release.yml`の一部、または専用の`benchmark.yml`。ベンチマークデータセットは個人情報を含み得る実データであり、リポジトリ外の外部データストア（[ADR-0020](../adr/0020-benchmark-dataset.md)）にあるため、限定された認可済み実行環境でのみ動作する（通常のフォークからのPRでは実行しない、[`docs/security.md`](../security.md#github-actions)の最小権限方針と整合） |
| 成功条件 | 「合否判定」ではなく「計測・記録」が主目的。ただし品質指標が前回リリースから著しく劣化した場合は要確認とする |
| 失敗時の対応 | 劣化検知はリリースを自動ブロックせず、Issueを起票し原因調査を行う（[`docs/operations/release.md`](../operations/release.md#parser-upgrade)のMAJORバージョンBackfill判断とも接続する） |
| Coverage対象 | 様式（`era_id`）別・期間別の分布（実運用データの実態を代表するよう構成、[ADR-0020](../adr/0020-benchmark-dataset.md)） |
| Coverage目標 | 具体的なサンプルサイズは実装時に確定する（暫定） |

## Mutation Test（将来）

**現時点では導入しない。**

| 項目 | 内容 |
|---|---|
| 目的 | テストスイート自体の有効性を検証する（コードに意図的な変異を注入し、既存テストがそれを検知できるかを確認する） |
| 責務 | 将来導入時、複雑な分岐を持つ`normalizers/`・`validators/`のテスト網羅性を優先的に検証する |
| 実行タイミング | 将来決定。処理コストが高いため、低頻度（月次等）を候補とする |
| GitHub Actionsでの位置づけ | 将来の専用ワークフロー。現時点では未導入 |
| 成功条件 | 将来定義（Mutation Score、生存した変異体の割合が閾値以下であること等） |
| 失敗時の対応 | 将来定義 |
| Coverage対象 | 将来、複雑なロジックを持つ`normalizers/`, `validators/`を優先対象とする |
| Coverage目標 | 将来決定 |

**不採用の理由（現時点）**: Mutation Testツールの導入・実行コストは、[ADR-0001](../adr/0001-python-packaging.md)の依存最小化・保守負荷最小化方針に対して、現在の開発体制規模では見合わないと判断する。Unit Test・Golden Test・Regression Testの多層防御により、当面の品質担保は十分と判断する。処理規模・関与者数が拡大した場合、新規ADRとして再検討する（[ADR-0019](../adr/0019-workflow-orchestration.md)が同様の考え方でGitHub Actionsからの移行条件を先送りしているのと同じ姿勢）。

## GitHub Actionsワークフローとの対応まとめ

| テスト種別 | ワークフロー | 既存/将来 |
|---|---|---|
| Unit / Integration / Golden / Regression | `ci.yml`の`test`ジョブ | 既存（骨格のみ、[`.github/workflows/README.md`](../../.github/workflows/README.md)） |
| Golden（専用化する場合） | `layout-validation.yml` | 将来追加予定 |
| Performance | 専用ワークフロー | 将来新設 |
| Acceptance / Benchmark | `release.yml` | 将来追加予定 |
| Mutation | 専用ワークフロー | 将来（不採用、本ドキュメントの「Mutation Test」節参照） |

## 関連ドキュメント

- [`docs/implementation.md`](../implementation.md) — Implementation Guide（Testing Ruleが本ドキュメントを参照する）
- [ADR-0007](../adr/0007-golden-file-testing.md) — ゴールデンファイルテスト戦略
- [ADR-0020](../adr/0020-benchmark-dataset.md) — ベンチマークデータセット戦略
- [`docs/architecture/learning_dataset.md`](../architecture/learning_dataset.md) — Learning Dataset（Regression Testの対象）
- [`docs/operations/release.md`](../operations/release.md) — Release Flow（Performance/Acceptance/Benchmark Testの実行タイミング）
- [`tests/README.md`](../../tests/README.md) — テストディレクトリ構成
- [`pyproject.toml`](../../pyproject.toml) — pytest/coverage設定の唯一の情報源
