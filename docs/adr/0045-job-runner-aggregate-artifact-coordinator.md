# 0045. JobRunnerによる集約Artifact展開モデル（Coordinatorパターン）

## ステータス
Accepted

## コンテキスト（Context）

Phase3 Task10-1で実装した`JobRunner`（[ADR-0044](0044-pipelinerunner-jobrunner-boundary.md)）は、中核パイプライン6段階（[ADR-0011](0011-fixed-core-pipeline.md)）を単一の`PipelineRunner`へ登録し、`run()`を1回だけ呼び出す構成を取っていた。Phase3 Task10-2（Architecture Review）は、この構成が以下3箇所で入出力型を満たさないことを、実際のコード（型シグネチャおよび内部の属性アクセス）を根拠に指摘した（[M-1]）。

| 境界 | 出力側の型（集約Artifact） | 入力側が要求する型（単一Artifact） | 実際にアクセスする属性 |
|---|---|---|---|
| Section Parser → Field Extractor | `SectionParseResult`（`sections: tuple[PersonnelSection, ...]`） | `PersonnelSection`単体 | `FieldExtractor.run()`は`section.section_text`・`section.layout_id`を直接参照 |
| Field Extractor → Normalizer | `FieldExtractionResult`（`records: tuple[RawRecord, ...]`） | `RawRecord`単体 | `Normalizer._evaluate_record()`は`record.layout_id`・`record.raw_fields`を直接参照 |
| Normalizer → Validator | `NormalizationResult`（`records: tuple[NormalizedRecord, ...]`） | `NormalizedRecord`単体 | `Validator._evaluate_record()`は`record.raw_record_ref`を直接参照 |

`PipelineRunner`はStage間の値を`object`として不透明に受け渡すのみで、集約結果から単一値への変換（アンラップ・展開）を一切行わない設計（[ADR-0044](0044-pipelinerunner-jobrunner-boundary.md)、`pipeline/runner.py`）であるため、1つのsection・1つのrecordしか含まない自明なケースを除き、実データでは上記いずれかの境界で`AttributeError`（`PipelineException`ではない未分類の例外）が発生し、`JobRunner.run_for_pdf()`から未処理のまま伝播する。

この欠陥は、ADR-0044が定める「Repository永続化責務: `PipelineRunner`が返す`PipelineResult`（および中間で得られる各Stage出力）を`repositories/`（抽象）経由で永続化する」の実現も妨げていた（[M-2]）。`PipelineResult`（`context`/`job`/`events`/`metrics`/`error`のみ保持）には最終Artifactを保持するフィールドがなく、`JobRunner`が中間Stage出力（`PersonnelSection`/`RawRecord`/`NormalizedRecord`/`ValidationResult`）へアクセスする手段自体が構造的に存在しなかった。

Phase3 Task10-3.0（Architecture Design Review）で、この欠陥を解消する複数案を比較検討し、本ADRが確定する案（B案）を採用した。

## 問題（Problem）

1. 中核パイプライン6段階のうち、Section Parser・Field Extractor・Normalizerの3段階は「1入力→N件の集約結果」を生成する段階であり、後続段階（Field Extractor・Normalizer・Validator）は「単一Artifact」を入力として要求する。この段数構成自体はADR-0011・ADR-0037・ADR-0038・ADR-0040・ADR-0043がそれぞれ個別に決定したものであり、いずれも変更しない前提のもとで、両者を橋渡しする責務がどこにも定義されていなかった。
2. `PipelineRunner`にこの橋渡し責務を持たせると、`PipelineRunner`が特定の集約Artifact型（`SectionParseResult`等）の内部構造を知る必要が生じ、ADR-0044が確立した「`PipelineRunner`は`PipelineStage[object, object]`として型消去された不透明な実行機である」という設計原則、およびarchitecture-contract.md保証13（`PipelineRunner`はRepository等を知らない）が暗黙に前提とする「`PipelineRunner`はドメイン知識を一切持たない」という性質を損なう。

## 決定（Decision）

### 1. PipelineRunnerは変更しない

`PipelineRunner`（`pipeline/runner.py`）は、ADR-0044で確定した「純粋なStage実行機」のままとする。集約Artifactの検出・展開（アンラップ・反復）はいかなる形でも`PipelineRunner`へ実装しない。`PipelineStage[object, object]`として型消去されたStage列を、渡された順序のまま1回実行するという既存の責務・実装（`pipeline/runner.py`, `pipeline/builder.py`）は無変更である。

### 2. JobRunnerが集約Artifactを反復処理するCoordinatorとなる

`JobRunner`（ADR-0044の「呼び出し元」責務の自然な拡張として）は、以下の実行モデルに従い、`PipelineRunner`を必要な回数だけ呼び出す。

**実行モデル**:

1. **文書レベル（1回呼び出し）**: `DocumentAnalyzer` → `LayoutDetector` → `SectionParser`を1つの`PipelineRunner`に登録し、`run()`を1回呼び出す。この3段階の入出力（`PdfRecord`→`Document`→`LayoutArtifact`→`SectionParseResult`）はすべて1:1であり、単一`PipelineRunner`での連結が成立する。
2. **Section単位（`SectionParseResult.sections`の件数分、繰り返し呼び出し）**: `JobRunner`が`SectionParseResult.sections`の各`PersonnelSection`を取り出し、`FieldExtractor`単体を登録した`PipelineRunner`の`run()`を、取り出した`PersonnelSection`を入力として都度呼び出す。
3. **Record単位（各`FieldExtractionResult.records`の件数分、繰り返し呼び出し）**: `JobRunner`が`FieldExtractionResult.records`の各`RawRecord`を取り出し、`Normalizer`単体を登録した`PipelineRunner`の`run()`を都度呼び出す。戻り値`NormalizationResult.records`（[ADR-0040](0040-normalizer-produces-normalization-result.md)により常に単一要素のtuple）から`NormalizedRecord`を取り出し、`Validator`単体を登録した別の`PipelineRunner`の`run()`へ入力として渡す。

各呼び出しにおいて、`JobRunner`は集約Artifactの`tuple`フィールド（`.sections`, `.records`）を読み取り、その要素を次の`PipelineRunner.run()`呼び出しの`initial_input`としてそのまま渡すのみであり、新たな値を生成・加工しない（下記「Artifact Ownership維持」参照）。段階のグルーピング（例: Normalizer/Validatorを2回の呼び出しに分けるか、`JobRunner`がその間で最小限のアンラップのみ行うか）の実装詳細は、本ADRでは1:1関係にある段階同士のみを同一`PipelineRunner`に登録できるという原則のみを定め、具体的なコード構成は実装タスクに委ねる。

### 3. Artifact Ownershipを維持する

各段階が自段階の出力物の生成を独占するという既存の保証（architecture-contract.md保証10, Exclusive Generation Ownership）は変更しない。`JobRunner`は集約Artifact（`SectionParseResult`, `FieldExtractionResult`, `NormalizationResult`）の`tuple`フィールドから要素を取り出す（インデックスアクセス）のみを行い、`PersonnelSection`・`RawRecord`・`NormalizedRecord`・`ValidationResult`のいずれも自ら生成しない。これらの値を生成できるのは引き続き対応するStage（Section Parser・Field Extractor・Normalizer・Validator）のみである。

### 4. Repository永続化との関係

`JobRunner`は各`PipelineRunner.run()`呼び出しの戻り値（`PipelineResult`が保持する最終Artifact、または呼び出し前に`JobRunner`自身が保持する集約Artifactの要素）を`CandidateRepository`（抽象）へ永続化する。`CandidateRepository`（[`docs/api/repositories.md`](../api/repositories.md)）の既存メソッド——`add_section(section: PersonnelSection)`, `add_raw(section_id, record: RawRecord)`, `attach_normalized(candidate_id, normalized: NormalizedRecord)`, `update_validation(candidate_id, result: ValidationResult)`——はいずれも単一Artifactを引数に取る形状で、Phase2 Task1（[ADR-0003](0003-layout-definition-strategy.md)以前の初期設計）から一貫して定義されていた。この形状は、`JobRunner`が集約Artifactを個々の要素へ展開してから永続化するという本ADRの実行モデルと整合しており、`CandidateRepository`のインターフェース自体が、本ADR以前から暗黙に本モデルを前提としていたことを示す。これにより、ADR-0044の「Repository永続化責務」（中間で得られる各Stage出力の永続化）が実現可能になる（Task10-2 [M-2]の解消）。

### 5. Learningとの関係

`JobRunner`はSection単位・Record単位でそれぞれ独立した`PipelineRunner.run()`を呼び出すため、あるsection・recordの処理失敗（`PipelineException`）は、他のsection・recordの処理に波及しない（[ADR-0019](0019-workflow-orchestration.md)の「PDF単位で失敗を独立させる」方針を、本ADRによりsection・record単位まで拡張したものと位置づけられる）。各呼び出しが返す`PipelineResult.error`を`JobRunner`が個別に検査し、`LearningService.record_error()`への委譲（ADR-0044）を呼び出し単位で行う。これにより、失敗した段階・対象record（`candidate_id`等）をより precise に紐付けたLearning記録が可能になる。

### 6. CLI/servicesとの整合

`JobRunner`のコンストラクタが受け取る依存の型（`KnowledgeService`, `LearningService`, `JobRunnerRepositories`等のProtocol型）は本ADRによって変更しない。`cli/`（合成ルート）・`services/`から見た`JobRunner`の外部契約（`docs/api/interfaces.md#jobrunner`のProtocol、`run_for_pdf`/`run_pending`/`get_job`）にも変更はなく、本ADRは`JobRunner`内部の`PipelineRunner`呼び出し方法にのみ関わる。

## 検討した代替案

- **A案: `PipelineRunner`自身が集約Artifactを検知して内部展開する**: `PipelineRunner`が特定の出力型（`SectionParseResult`等）を認識し、内部でループ処理する案。却下した。`PipelineRunner`が特定のドメイン型を知る必要が生じ、ADR-0044が確立した「`PipelineRunner`は`PipelineStage[object, object]`として型消去された、ドメイン知識を持たない実行機である」という設計原則と正面から矛盾するため。
- **C案: 集約→単一への変換を専用のAdapter Stageとして中核パイプラインへ追加する**: ADR-0011が固定する6段階の構成・順序・名称を変更することになるため却下した（本ADRの前提「ADR-0011の6段階構成は変更しない」に反する）。
- **D案: `PipelineResult`に最終Artifactを保持するフィールドを追加するのみで、展開責務の所在は明確化しない**: `JobRunner`が中間Artifactへアクセスする手段は得られるが、「誰が・どの単位で`PipelineRunner`を呼び出すか」という反復処理の責務自体が未定義のままであり、[M-1]（実行時の型不整合によるクラッシュ）を解消しないため不採用とした。

## 結果（トレードオフ, Consequences）

- `JobRunner`は、単一の`PipelineRunner`呼び出しではなく、文書レベル・Section単位・Record単位で複数回`PipelineRunner`を構築・呼び出す構成になる。これにより`JobRunner`側のコード量・複雑度は増すが、`PipelineRunner`・中核6段階のいずれのコードも変更を要しない。
- `PipelineRunner`を複数回構築するオーバーヘッド（`PipelineBuilder`の都度生成等）が生じるが、現時点の処理量（防衛省の発令PDF、不定期・小規模、[ADR-0019](0019-workflow-orchestration.md)）に対しては無視できる範囲と判断する。将来的に問題になった場合は、`PipelineBuilder`のキャッシュ等、非破壊的な最適化を別途検討する。
- `CandidateRepository`への永続化ロジックが`JobRunner`に集中する。これは`JobRunner`がADR-0044で既に「Repository永続化責務」を担うと決定されていることと整合する。

## Migration

1. 実装（Task10-3.2以降を想定）は本ADRの対象外。本ADRはアーキテクチャ決定のみを確定する。
2. `docs/api/pipeline.md`・`docs/api/package-design.md`・`docs/api/dependency-rule.md`・`docs/architecture/architecture-contract.md`・ADR index/README/dependency-map.mdを本ADRの内容に同期する（詳細はTask10-3.1完了報告を参照）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/api/pipeline.md`](../api/pipeline.md) | 「`JobRunner`との関係」節にCoordinatorとしての反復処理を追記 |
| [`docs/api/package-design.md`](../api/package-design.md) | `pipeline/`節の`JobRunner`責務にCoordinator/反復呼び出しを追記 |
| [`docs/api/dependency-rule.md`](../api/dependency-rule.md) | 変更不要（理由はTask10-3.1完了報告を参照） |
| [`docs/architecture/architecture-contract.md`](../architecture/architecture-contract.md) | 新規保証の要否を検討（詳細はTask10-3.1完了報告を参照） |

## 関連ADR
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0019](0019-workflow-orchestration.md) — PDF単位での失敗独立方針。本ADRはこれをsection・record単位へ拡張する。
- [ADR-0037](0037-layout-detector-produces-layout-artifact.md) — Section Parserの単一入力`run()`パターン。
- [ADR-0038](0038-field-extractor-produces-field-extraction-result.md) — `FieldExtractionResult`集約結果パターンの先例。
- [ADR-0040](0040-normalizer-produces-normalization-result.md) — `NormalizationResult`集約結果パターン。`records`が常に単一要素のtupleであることの根拠。
- [ADR-0043](0043-validator-produces-validation-result-with-rule-engine.md) — `ValidationResult`集約結果パターン。
- [ADR-0044](0044-pipelinerunner-jobrunner-boundary.md) — `PipelineRunner`/`JobRunner`の責務境界。本ADRはこの境界（`PipelineRunner`はRepository・Knowledge・Learning・Review・Exportを知らない）を変更せず、その範囲内で`JobRunner`の反復処理責務を確定する。

（本ADRはADR-0011/0019/0037/0038/0040/0043/0044のいずれの核心決定も変更しないため、Supersededにはしない。）
