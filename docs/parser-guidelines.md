# Parser Development Guidelines

> 本ドキュメントは、中核パイプラインの`document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`各パッケージ（以下まとめて「Parser」と呼ぶ）を実装・変更する際に従う専用規約である。[`docs/implementation.md`](implementation.md)の「Parser Rule」が参照する正の文書。[ADR-0011](adr/0011-fixed-core-pipeline.md)（中核パイプライン固定化）・[ADR-0012](adr/0012-error-handling-priority-order.md)（未知パターンへの対応優先順位）・[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)（10の分離保証）と矛盾しない。実装コードは含まない。

## ParserはKnowledgeより優先されない

Parserのコードロジック（正規表現・分岐処理等）は、`knowledge/`が表現できるドメイン知識より優先度が低い。「コードで解決できるからコードで解決する」という判断を既定にしない。あるパターンへの対応を実装する前に、それが`knowledge/`（表記ゆれ・別名・改称履歴等）で表現可能かを必ず検討する（[ADR-0005](adr/0005-knowledge-base-normalization.md), [ADR-0012](adr/0012-error-handling-priority-order.md)）。

## Regex追加よりKnowledge追加を優先

未知のパターンに遭遇した場合、コード中に正規表現を追加する前に、`knowledge/`へのデータ追加で解決できないかを検討する（[ADR-0012](adr/0012-error-handling-priority-order.md)の優先順位1）。既存の正規表現を拡張・修正することで一時的にパターンを吸収する対応は、恒久的な解決ではなく応急処置として扱い、対応するIssueまたはLearning Datasetエントリに「Knowledgeへの移行が望ましい」ことを明記する。

## Knowledge追加よりLayout追加を優先してはいけない

[ADR-0012](adr/0012-error-handling-priority-order.md)が定める優先順位は「Knowledge Base追加 > Layout追加 > 例外処理」である。Knowledgeで表現できる差異（表記ゆれ・別名・改称等）を、Layout定義（様式・構造の差異を表現する層）に押し込んではならない。両者は扱う対象が異なる: Layoutは「PDFの版面構成」、Knowledgeは「値の表記」である。ある差異がどちらに属するか迷った場合は、「PDFの見た目・構造が変わったか」（Layout）か「同じ構造の中で値の書き方が変わったか」（Knowledge）で判断する。

## Unknown検出を優先する

Layout Detectorは、既存の`layouts/`のどの`era_id`にも該当しない入力を検出した場合、無理に最も近い既存様式へ分類しようとせず、明示的に「未知の様式」として扱いエラーを送出する（[`docs/architecture.md`](architecture.md)）。既存様式の判定ロジックを条件分岐で無理に拡張して未知パターンを飲み込むことを禁止する。未知の検出は、[`docs/review/policy.md`](review/policy.md)のレビューキュー優先度スコアにおいて`layout_unknown`として最優先で扱われる設計（[`docs/review/queue.md`](review/queue.md)）と対応しており、Parser側で誤って「既知」と誤判定すると、この優先度付けの仕組みが機能しなくなる。

## Confidence算出方法

**Confidenceの算出はParserの責務ではない。** `confidence`はDBの列ではなく、Publish段階で`candidate_records.validation_status`・`learning_dataset`の存在・Review状態から導出される計算値である（[`docs/database/json_schema.md`](database/json_schema.md#confidenceの算出ルール)）。

Parser（`extractors/`, `normalizers/`, `validators/`）が行うのは、この計算の**入力**を正しく生成することである。

- `validators/`は`ValidationResult`（`status`, `severity`）を正確に出力する。
- `normalizers/`は、曖昧さを伴う`knowledge_items`（表記ゆれの複数候補等）を適用した場合、その事実が`NormalizedRecord`（`normalization_applied`、[`docs/api/models.md`](api/models.md)）から追跡できる状態を維持する。

ConfidenceバンドのしきいDBへの直接的な書き込み・算出ロジックの実装をParserパッケージ内に置かない。

## Section単位で処理する

Field Extractor・Normalizer・Validatorは、`PersonnelSection`（Section Parserが切り出した単位、[`docs/api/models.md`](api/models.md)）ごとに処理する。1つのセクションの処理失敗が、同一PDF内の他のセクションの処理に波及しないようにする。これは[ADR-0019](adr/0019-workflow-orchestration.md)が定める「PDF単位で独立して成否を扱う」という原則を、PDF単位よりさらに細かいセクション単位まで一貫させたものである。

## ページ全体を一括解析しない

Document AnalyzerはPDFのメタデータ取得・健全性確認・基本統計・警告生成のみを行い、文字抽出・様式判定は行わない（[`docs/architecture.md`](architecture.md)、Version 2.0・[ADR-0032](adr/0032-redefine-document-analyzer-responsibility.md)）。ページ全体を一度にまとめて解析し、様式判定・セクション切り出し・フィールド抽出を単一の処理で済ませる実装をしない。中核パイプラインの6段階（[ADR-0011](adr/0011-fixed-core-pipeline.md)）は、この分割によって初めて「ある段階の変更が他の段階に影響しない」という設計上の利点を得る。段階をまたいだ最適化のための処理統合を行わない。

## 正規化はNormalizerでのみ行う

`extractors/`（Field Extractor）の出力（`RawRecord`）は正規化前の生の値である（[`docs/api/package-design.md`](api/package-design.md#extractorsfield-extractor)）。`extractors/`・`sections/`・`document/`・`layout/`のいずれにも、値を正規化するロジック（表記統一・単位変換等）を実装しない。正規化は`normalizers/`（Normalizer）に一元化する。

## Validationは修正しない

`validators/`（Validator）は、正規化後のデータを検証するのみで、**値そのものは変更しない**（[`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md)の保証6）。検証NGを検出した際に、Validatorが自動的に値を訂正・補完する実装をしない。訂正は常に人間のレビュー（[`docs/review/policy.md`](review/policy.md)）を経由する。

## ParserはRepositoryを知らない

`document/`, `layout/`, `sections/`, `extractors/`, `normalizers/`, `validators/`のいずれも、`repositories/`（抽象・具象いずれも）に依存しない。[`docs/api/package-design.md`](api/package-design.md)が定める依存禁止ルールであり、[`docs/api/dependency-rule.md`](api/dependency-rule.md)の依存グラフによって構造的に強制される。永続化は呼び出し元（`pipeline/`のJobRunner）の責務である。

## ParserはSQLiteを知らない

上記「ParserはRepositoryを知らない」の直接の帰結として、`sqlite3`モジュール・SQLite固有の型を、Parserパッケージのいずれもimportしない（[`docs/implementation.md`](implementation.md#no-sqlite-dependency-outside-infrastructure)の「No SQLite Dependency Outside Infrastructure」）。

## ParserはFTPを知らない

Parserパッケージは`ftp/`パッケージに依存しない。公開・配信（[ADR-0022](adr/0022-export-policy.md)）はParserの完了後の別ステージであり、Parser内から直接FTP送信を行う実装をしない。

## ParserはJSONを知らない

Parserパッケージは公開JSON形式（[`docs/database/json_schema.md`](database/json_schema.md)）を知らない。`export/`パッケージが`gold_records`から公開JSONへの変換を担う。Parserの出力（`RawRecord`, `NormalizedRecord`, `ValidationResult`）を公開JSON形式に直接シリアライズするロジックをParserパッケージ内に実装しない。

## ParserはReviewを知らない

Parserパッケージは`review/`パッケージに依存しない（[`docs/api/package-design.md`](api/package-design.md)）。Validatorの検証結果がレビューキューにどう反映されるか（[`docs/review/queue.md`](review/queue.md)の優先度スコア）は`pipeline/`・`review/`側の関心事であり、Parser自身がレビューの要否を判断・分岐するロジックを持たない。

## Parserはrun()以外の公開APIを持たない

中核パイプライン6段階は、公開メソッドを`run()`一つに限定する`PipelineStage` Protocol（[`docs/api/pipeline.md`](api/pipeline.md)）に従う。これにより各段階が副作用を持たない純粋な変換として扱われることが保証される。Parserパッケージに`run()`以外の公開メソッド（例: 部分的な処理だけを行うヘルパーメソッドの外部公開）を追加しない。内部実装として非公開のヘルパー関数（`_`接頭辞）を持つことは妨げない。

## Parser Version更新ルール

Parserのバージョニングは[ADR-0023](adr/0023-parser-versioning-policy.md)を正とする。要点:

- `parser_versions.code_version`にはGitのリリースタグ名（SemVer）を用いる。
- MAJOR: 既存レコードの再現性を壊す変更。MINOR: 出力形式への後方互換な追加。PATCH: 出力に影響しないバグ修正・内部リファクタリング。
- 新しい`parser_versions`行は、リリースタグ付与をトリガーにCIが自動作成する。手動INSERTはしない。
- 段階的展開の運用手順（`staging`→`production`）は[`docs/operations/release.md`](operations/release.md#parser-upgrade)を参照。

## Parser廃止手順

Parser Versionは**削除しない**。「廃止」とは、そのバージョンが新規のPDF処理に使われなくなることを指し、過去に生成されたレコードとの紐付けを保つため、`parser_versions`テーブルの当該行は永久に保持する（[ADR-0006](adr/0006-pipeline-provenance.md)の来歴不変原則、[ADR-0023](adr/0023-parser-versioning-policy.md)の「リリースタグは削除・強制上書きを禁止」）。

1. 新しいリリースタグ（後継バージョン）を作成し、次回以降のスケジュール実行は自動的に新バージョンを使用する（[`docs/operations/release.md`](operations/release.md#release-flow)）。
2. 旧バージョンのコード自体は`main`ブランチの履歴から削除しない。Gitの通常のコミット履歴として残る。
3. 旧バージョンで生成された`gold_records`・`candidate_records`は、当時の`parser_version_id`を保持したまま不変であり、遡って書き換えない。
4. 旧バージョンに起因する広範な誤りが判明した場合の対応は、[`docs/operations/release.md`](operations/release.md#backfill)のBackfill手順に従う。

## Parser性能評価

処理時間・メモリ使用量の評価は、[`docs/testing/test-policy.md`](testing/test-policy.md#performance-test)のPerformance Testを正とする。特にDocument Analyzer段階は、異常なPDF（圧縮爆弾等）に対するリソース上限を持つ（[ADR-0026](adr/0026-security-policy.md)）。新しいParser Versionのリリース前に、既存のベースラインと比較して著しい性能劣化がないことを確認する。

## Parser品質指標

Parserの量的な品質は、[`docs/testing/test-policy.md`](testing/test-policy.md#benchmark-test)のBenchmark Test（[ADR-0020](adr/0020-benchmark-dataset.md)）により、リリースごとに以下を計測する。

- 様式（`era_id`）別・期間別のValidator通過率
- Confidenceバンド（[`docs/database/json_schema.md`](database/json_schema.md#confidenceの算出ルール)）の分布
- Learning Dataset（[ADR-0017](adr/0017-learning-dataset-field-expansion.md)）の新規発生率（`error_category`別）

これらの指標がリリースごとに悪化していないかを、[`docs/operations/observability.md`](operations/observability.md#dashboard)のダッシュボードで追跡する。

## 関連ドキュメント

- [`docs/implementation.md`](implementation.md) — Implementation Guide（Parser Ruleが本ドキュメントを参照する）
- [ADR-0003](adr/0003-layout-definition-strategy.md) — PDFレイアウトの外部データ定義化
- [ADR-0005](adr/0005-knowledge-base-normalization.md) — ドメイン知識ベースによる名寄せ・正規化戦略
- [ADR-0011](adr/0011-fixed-core-pipeline.md) — 中核処理パイプラインの固定化
- [ADR-0012](adr/0012-error-handling-priority-order.md) — 未知パターンへの対応優先順位
- [ADR-0023](adr/0023-parser-versioning-policy.md) — Parserバージョニング方針
- [`docs/architecture/architecture-contract.md`](architecture/architecture-contract.md) — Architecture Contract（10の分離保証）
- [`docs/api/package-design.md`](api/package-design.md) — パッケージ構成・依存禁止ルール
- [`docs/api/pipeline.md`](api/pipeline.md) — `PipelineStage`（`run()`のみの公開）
- [`docs/testing/test-policy.md`](testing/test-policy.md) — Performance Test / Benchmark Test
- [`docs/operations/release.md`](operations/release.md) — Parser Upgrade / Backfill運用手順
