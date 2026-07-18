# Architecture Contract

> 本ドキュメントは[`docs/constitution.md`](../constitution.md)（Project Constitution）に従属する。両者が矛盾する場合はConstitutionが優先される。
>
> 本ドキュメントは、Interface & Package設計（[`docs/api/`](../api/)）全体が満たすべき9つの分離保証を定義する。個々の保証は[`package-design.md`](../api/package-design.md)（依存関係）・[`dependency-rule.md`](../api/dependency-rule.md)（禁止/許可パターン）・[`pipeline.md`](../api/pipeline.md)（`run()`のみの公開）・[`docs/review/`](../review/)（Review Domain）の設計によって、**構造的に**（レビューや申し合わせだけでなく、依存グラフ上の事実として）実現される。曖昧な保証は解釈を明記し、将来の実装者が異なる解釈をしないようにする。
>
> **本ドキュメントに実装はない。**

## 保証一覧

| # | 保証 | 実現するパッケージ境界 |
|---|---|---|
| 1 | Document Analyzerはlayoutを知らない | `document/` ⊥ `layout/` |
| 2 | Layout Detectorはfieldを知らない | `layout/` ⊥ `extractors/` |
| 3 | Section Parserはknowledgeを知らない | `sections/` ⊥ `knowledge/` |
| 4 | Field ExtractorはDBを知らない | `extractors/` ⊥ `repositories/` |
| 5 | Normalizerは正規表現を持たない | `normalizers/`のコードにドメイン固有regexを書かない |
| 6 | Validatorは修正しない | `Validator.run()`の戻り値に修正後の値を含めない |
| 7 | RepositoryはSQLiteを隠蔽する | `repositories/`（抽象）⊥ `sqlite3` |
| 8 | Reviewはgold_recordsだけ更新できる | `GoldRepository`への書き込み経路を`review/`に一本化 |
| 9 | Reviewだけがgold_records（Gold Database）を書き換えられる | `review/`以外のいかなるパッケージも`GoldRepository`の書き込みメソッドを呼ばない |

（`⊥`は「依存しない」を表す。保証8と9は同じ設計判断を異なる向きから述べたものであり、[9節](#9-reviewだけがgold_recordsgold-databaseを書き換えられる)で統合的に扱う）

---

## 1. Document Analyzerはlayoutを知らない

**保証の内容**: `document/`パッケージのコードは、`layout/`パッケージ・`layouts/`ディレクトリ・`era_id`という概念のいずれも参照しない。

**理由**: PDFの構造抽出（ページ・テキスト・座標）は、どの様式かに関わらず共通の処理であるべきであり（[ADR-0011](../adr/0011-fixed-core-pipeline.md)）、様式判定ロジックが混入すると、新様式追加のたびに`document/`の変更が必要になり、[ADR-0003](../adr/0003-layout-definition-strategy.md)が意図する「レイアウト変更を`layouts/`の追加だけで完結させる」という目標を損なう。

**実現方法**: [`package-design.md`](../api/package-design.md)の`document/`節が定めるとおり、`document/`の依存先は`models/`, `utils/`のみ。`DocumentAnalyzer.run()`（[`interfaces.md`](../api/interfaces.md)）の戻り値`Document`は、様式に関する情報を一切含まない（ページ・テキスト・座標のみ）。

## 2. Layout Detectorはfieldを知らない

**保証の内容**: `layout/`パッケージのコードは、氏名・階級・組織等の個別フィールド名、および`extractors/`パッケージを参照しない。

**理由**: Layout Detectorの責務は「どの様式か」の判定のみであり、フィールドの中身への言及は責務の逸脱である（単一責務、[ADR-0011](../adr/0011-fixed-core-pipeline.md)）。

**実現方法**: `layout/`の依存先は`models/`, `utils/`のみ。`LayoutDetector.run()`の戻り値`LayoutDetectionResult`（[`models.md`](../api/models.md#補助的な値オブジェクト)）は`Layout`＋`Confidence`のみを持ち、フィールド定義を含まない。

## 3. Section Parserはknowledgeを知らない

**保証の内容**: `sections/`パッケージのコードは、`knowledge/`パッケージ・`knowledge/`ディレクトリの内容を参照しない。

**理由**: セクションの切り出しは、レイアウト定義（構造）のみに基づいて機械的に行われるべきであり、組織名・階級名等のドメイン知識（意味）は後続のNormalizer段階の関心事である（[ADR-0005](../adr/0005-knowledge-base-normalization.md)と[ADR-0011](../adr/0011-fixed-core-pipeline.md)の段階分離）。

**実現方法**: `sections/`の依存先は`models/`, `utils/`のみ。

## 4. Field ExtractorはDBを知らない

**保証の内容**: `extractors/`パッケージのコードは、`repositories/`（抽象・具象いずれも）を一切参照しない。

**解釈上の注記**: [`dependency-rule.md`](../api/dependency-rule.md)が示す一般原則では「`repository`という抽象を経由すれば許可」だが、本プロジェクトは中核パイプライン6段階についてこれよりも**厳格な制約**（repositoryへの依存自体を禁止）を採用する。理由は[`dependency-rule.md`](../api/dependency-rule.md#本プロジェクト固有の追加制約)を参照。したがって「DBを知らない」は、単に「具体的なDB技術を知らない」ではなく、「永続化という概念そのものを知らない」という、より強い意味で成立する。

**実現方法**: `FieldExtractor.run()`（[`pipeline.md`](../api/pipeline.md)）は`PersonnelSection`を受け取り`RawRecord`を返す純粋な変換のみを行う。永続化は呼び出し元の`pipeline/`（`JobRunner`）が`CandidateRepository.add_raw()`（[`repositories.md`](../api/repositories.md)）を呼んで行う。

## 5. Normalizerは正規表現を持たない

**保証の内容**: `normalizers/`パッケージのソースコードに、ドメイン固有の正規表現パターン（組織名・階級名・氏名の表記ゆれに対応する具体的なパターン文字列）をハードコードしない。

**解釈上の注記（重要）**: これは「`re`モジュールを一切使ってはならない」という意味ではない。`knowledge/typography/`（[`docs/knowledge/schema.md`](../knowledge/schema.md#typography)）のルールは`pattern`/`replacement`のペアとしてデータ側に定義されており、Normalizerがそれを**汎用的な適用エンジン**として実行すること（例: `re.sub(pattern, replacement, text)`をデータ駆動で呼び出すこと）は許容される。禁止されるのは、**コード中に個別のドメイン知識を表すパターン文字列を直接書くこと**である（[ADR-0012](../adr/0012-error-handling-priority-order.md)の「Knowledge Base追加を正規表現の追加より優先する」を、コードレベルの制約として言い換えたもの）。

**実現方法**: `Normalizer.run()`（[`interfaces.md`](../api/interfaces.md)）は`RawRecord`と、呼び出し元が注入する`KnowledgeSnapshot`（[`models.md`](../api/models.md)、`knowledge/typography/`・`knowledge/organizations/`等のルールを含む）を受け取り、`KnowledgeSnapshot`内のデータのみを使って変換する。`normalizers/`のコードレビューでは、リテラルな正規表現パターン（変数化されていない、`knowledge/`由来でないパターン文字列）の混入を明示的にチェック項目とする（[`python-contract.md`](../api/python-contract.md)のコードレビュー観点として今後明記）。

## 6. Validatorは修正しない

**保証の内容**: `Validator.run()`の戻り値`ValidationResult`（[`models.md`](../api/models.md)）は、検証対象の値そのもの（修正後の値）を一切含まない。合否（`status`）・違反内容（`violations`）・信頼度（`confidence`）のみを返す。

**理由**: 検証と修正を同じコンポーネントに持たせると、「なぜその値になったか」の追跡が困難になり、[ADR-0006](../adr/0006-pipeline-provenance.md)の来歴管理の原則に反する。修正が必要な場合は、人手レビュー（`review/`、[ADR-0021](../adr/0021-review-ui-strategy.md)）を経由するか、Knowledge Base/Layoutの改善（[ADR-0012](../adr/0012-error-handling-priority-order.md)）による再処理を経由する。

**実現方法**: [`models.md`](../api/models.md#validationresult)の`ValidationResult`型定義に`NormalizedRecord`（修正後の値）を含むフィールドは存在しない。`subject_ref`は検証**対象への参照**であり、値のコピーや改変版ではない。

## 7. RepositoryはSQLiteを隠蔽する

**保証の内容**: `repositories/`（抽象Protocol）の公開シグネチャに、`sqlite3`モジュールの型・SQL文字列・SQLite固有の構文（`STRFTIME`関数呼び出し等）が一切現れない。

**実現方法**: [`repositories.md`](../api/repositories.md#sqlite非依存を実現する設計原則)の6原則（モデル型のみで表現、不透明ID型、`date`/`datetime`型での受け渡し、パース済みモデルでのJSON受け渡し、`UnitOfWork`によるトランザクション抽象化、`limit`/`offset`によるページネーション抽象化）がこれを実現する。`repositories/sqlite/`のみが`sqlite3`をimportしてよい（[`dependency-rule.md`](../api/dependency-rule.md)）。将来PostgreSQLへ移行する際、`repositories/`の公開契約は変更しない（[`repositories.md`](../api/repositories.md#postgresql移行時に変更が必要な範囲参考)）。

## 8. Reviewはgold_recordsだけ更新できる

**保証の内容と解釈**: 文字どおり「ReviewServiceが書き込めるRepositoryはGoldRepositoryのみ」と読むと、[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)・[ADR-0017](../adr/0017-learning-dataset-field-expansion.md)が定めるReviewService自身の記録（`ReviewRepository`への`review_changes`記録、`LearningRepository`への状態遷移記録）と矛盾する。したがって本保証は以下のように解釈を確定する。

> **`GoldRepository`への書き込み（`add_version` / `supersede`）を行えるのは`review/`パッケージ（`ReviewService`）のみであり、他のいかなるパッケージ（`pipeline/`, `validators/`等）も`GoldRepository`に書き込まない。** `ReviewService`は自身の責務に付随する`ReviewRepository`・`LearningRepository`への書き込みも行うが、それらは「Gold Databaseの更新」ではなく「レビュー自身の記録」であり、本保証の対象外とする。

**理由**: [ADR-0010](../adr/0010-ci-cd-and-publish-strategy.md)が定める「人手ゲート」の原則——検証を通過しただけでは公開データにならず、必ず人手の確認を経る——を、Repositoryレベルの書き込み権限として構造化したものである。Validatorが「検証を通過した」と判定しても、それだけでは`gold_records`は更新されない。

**実現方法**: [`package-design.md`](../api/package-design.md)の`review/`節・依存先サマリ表で、`GoldRepository`への書き込みメソッド（`add_version`, `supersede`、[`repositories.md`](../api/repositories.md#goldrepository)）を実際に呼び出すのは`review/`パッケージの`ReviewService.promote_to_gold()`（[`interfaces.md`](../api/interfaces.md#reviewservice)）のみとする設計上の取り決めとする。`pipeline/`は`GoldRepository`に依存しない（[`package-design.md`](../api/package-design.md)の`pipeline/`節の依存先一覧に`GoldRepository`は含まれない）。

## 9. Reviewだけがgold_records（Gold Database）を書き換えられる

**保証の内容**: 保証8が「`review/`はGoldRepository以外を書き換えない」という**`review/`側の制約**を述べたのに対し、本保証は「`GoldRepository`は`review/`以外から書き換えられない」という**`GoldRepository`側の排他性**を述べる。両者は同一の設計（`GoldRepository`への書き込み経路を`review/`に一本化する）の裏表であり、Human Reviewを「システムの中核」（[`docs/review/`](../review/)）として設計する上で、最も基本的な不変条件として独立に明記する。

> **`gold_records`（Gold Database）への書き込みは、`review/`パッケージの`ReviewService.promote_to_gold()`を経由した場合に限り発生する。これ以外の経路——`pipeline/`・`validators/`・`knowledge/`・`export/`はもちろん、`review/`パッケージ内であっても`promote_to_gold()`以外のメソッド——からの直接書き込みは存在しない。**

**理由**: [`docs/review/policy.md`](../review/policy.md#gold更新条件)が定めるGold更新条件（承認済みの`ReviewDecision`が存在すること、Confidence基準を満たすこと等）は、書き込み経路が`promote_to_gold()`一つに絞られていて初めて、機械的に「必ず適用される」と保証できる。書き込み経路が複数存在すると、どこかの経路がポリシーチェックをバイパスするリスクを排除できない。

**実現方法**:
1. **パッケージ境界**（構造的な保証）: [`dependency-rule.md`](../api/dependency-rule.md)の全体依存グラフ・[`import-graph.md`](../api/import-graph.md)の検証済みグラフにおいて、`GoldRepository`（`repositories/`が定義する抽象、[`repositories.md`](../api/repositories.md#goldrepository)）への依存を持つのは`review/`のみである。`pipeline/`・`validators/`・`knowledge/`・`export/`はいずれも`GoldRepository`に依存しない（[`package-design.md`](../api/package-design.md)の依存先サマリ表）。
2. **メソッド粒度の保証**（`review/`パッケージ内部）: `review/`パッケージ内でも、`GoldRepository.add_version()` / `supersede()`（[`repositories.md`](../api/repositories.md#goldrepository)）を呼び出すのは`ReviewService.promote_to_gold()`（[`docs/api/review.md`](../api/review.md#reviewservice)）のみとする。`ReviewService`の他のメソッド（`submit_field_change()`, `decide()`, `add_comment()`等）はいずれも`GoldRepository`を呼び出さない。
3. **ライフサイクル上の保証**: [`docs/review/domain.md`](../review/domain.md#review-lifecycle状態遷移図)の状態遷移図において、`GoldDatabase`状態に到達する経路は`Approved --> GoldDatabase`の1本のみであり、`Approved`は`ReviewDecision.decision == "approve"`が確定した場合にのみ到達する。

**この保証が破られていないことの確認**: 実装着手後、`grep -r "GoldRepository" src/`のような単純な静的検索で、`repositories/sqlite/`の実装クラス自体を除けば`review/`パッケージ内にしか出現しないことを確認できる。将来的には[`dependency-rule.md`](../api/dependency-rule.md#機械的な検証将来の推奨事項)が推奨する`import-linter`の契約に、「`GoldRepository`への依存は`review/`のみ許可」というルールを追加することで、この確認を自動化する。

---

## この契約の検証方法

本ドキュメントの9保証はいずれも「特定パッケージが特定パッケージに依存しない」という形に還元できる（[`dependency-rule.md`](../api/dependency-rule.md)の全体依存グラフ）。したがって、実装着手後にこの契約が破られていないかは、以下の方法で検証可能である。

1. **静的解析**: `import-linter`等によるパッケージ間import制約の機械的検証（[`dependency-rule.md`](../api/dependency-rule.md#機械的な検証将来の推奨事項)）。
2. **型検査**: `Validator.run()`の戻り値型に修正後の値が含まれないこと等は、`mypy --strict`（[`python-contract.md`](../api/python-contract.md)）による型シグネチャの検証で担保される。
3. **コードレビュー**: 保証5（正規表現）のような、型シグネチャだけでは検出できない規約は、PRレビュー時の明示的なチェック項目とする（[CONTRIBUTING.md](../../CONTRIBUTING.md)のコーディング規約に、実装着手時に追記する）。

---

## 関連ドキュメント

- [`docs/api/package-design.md`](../api/package-design.md) — パッケージ構成
- [`docs/api/interfaces.md`](../api/interfaces.md) — 公開API定義
- [`docs/api/repositories.md`](../api/repositories.md) — Repository Pattern
- [`docs/api/models.md`](../api/models.md) — ドメインモデル
- [`docs/api/pipeline.md`](../api/pipeline.md) — Pipeline Interface
- [`docs/api/dependency-rule.md`](../api/dependency-rule.md) — 依存関係ルール
- [`docs/api/import-graph.md`](../api/import-graph.md) — Importグラフ・循環参照の検証
- [`docs/api/python-contract.md`](../api/python-contract.md) — Pythonコーディング規約
- [`docs/api/review.md`](../api/review.md) — Review API（保証8・9の実装契約）
- [`docs/review/domain.md`](../review/domain.md) — Review Domainモデル・ライフサイクル
- [`docs/review/policy.md`](../review/policy.md) — Review Policy（Gold更新条件等）
- [`docs/review/queue.md`](../review/queue.md) — Review Queueの優先順位
- [`docs/review/metrics.md`](../review/metrics.md) — Review Metrics
- [ADR-0011](../adr/0011-fixed-core-pipeline.md) — 中核処理パイプラインの固定化
- [ADR-0012](../adr/0012-error-handling-priority-order.md) — 未知パターンへの対応優先順位
- [ADR-0021](../adr/0021-review-ui-strategy.md) — レビュー用インターフェース戦略
