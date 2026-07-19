# 0039. Normalizer Field Mapping via Extended Layout Knowledge

## ステータス
Accepted

## コンテキスト（Context）

[ADR-0038](0038-field-extractor-produces-field-extraction-result.md)は、Field Extractorが列位置ベースの汎用フィールド名（`column_1`, `column_2`, ...）で`RawRecord`を生成するとVersion 2.0の暫定解として確定した一方、そのConsequences節で以下を明記し、Normalizer実装（Task8想定）着手前に新規ADRで確定するとしていた。

> 列位置ベースの汎用フィールド名（`column_1`等）は、そのままでは意味的な解釈ができない。Normalizer（段階5）が実際に「氏名」「階級」等の意味的な正規化を行うには、`column_N`から意味的フィールド名への対応付けが別途必要になる。この対応付けの方法（`LayoutDefinition`の拡張、`knowledge/`側での対応、Normalizer入力契約の拡張等）は本ADRの範囲外とし、Normalizer実装（Task8想定）着手前に新規ADRで確定する。

Phase2 Task8-0（Architecture Verification）は、この未確定事項を実装可能な形で解決することを要求する。検証の過程で、以下2件の欠落が複合していることが判明した。

1. **`RawRecord`にera_idを保持する手段がない**: `RawRecord.section_ref`は、パイプライン実行中（未永続化）は`None`であり（[`docs/api/models.md`](../api/models.md)）、Normalizerが受け取る時点では`RawRecord`単体からどの様式（`era_id`）で抽出されたかを判定できない。
2. **`column_N`→意味的フィールド名マッピングの正データを置く場所がない**: トップレベル`layouts/`は Layout Detector が唯一アクセスできる領域であり（[ADR-0035](0035-layout-detector-owns-pdf-content-access.md)）、`normalizers/`は`layouts/`への依存を禁止されている（[`docs/api/package-design.md`](../api/package-design.md)、[`docs/api/dependency-rule.md`](../api/dependency-rule.md)）。一方`knowledge/layout`カテゴリは、[`docs/knowledge/schema.md`](../knowledge/schema.md)により「参照する主な段階: Section Parser / Field Extractor」「特定レイアウト（era_id）固有の**既知の例外・補足知識**」に明示的に限定されており、Normalizerを参照段階に含まず、列位置マッピングのような**構造情報そのもの**も対象外である。

このうち(1)は既に実装済みの`RawRecord`（Phase1/Task2設計）のスキーマ変更、(2)は既に人手レビュー済みの8カテゴリKnowledge分類（`docs/knowledge/schema.md`）のスコープ変更にあたり、いずれも`CLAUDE.md`が確認を要求する「データモデルの破壊的変更」に該当するため、ユーザーに解決方針を確認した。ユーザーは以下を選択した。

> 既存の`knowledge/layout`カテゴリのスコープを「era_id固有の補足構造情報（例外だけでなく列位置マッピングも含む）」に広げて再利用する。`RawRecord`に`layout_id: str`（era_id）を新規フィールドとして追加し、Field Extractor実装と`repositories/sqlite/candidate.py`を小規模修正（Task6で`PersonnelSection.layout_id`を修正した前例と同型）。マッピングデータ自体の具体的内容（YAML構造等）は別途Taskで確定する。

本ADRは、この決定を正式な設計記録として確定する。Task8-0自体は「実装は一切行わず、設計確認と必要最小限のADR追加のみ実施する」ことを要求しているため、本ADRは方針の確定のみを行い、コード変更は実施しない。

## 問題（Problem）

1. `RawRecord`は、Normalizerが列位置→意味的フィールド名マッピングを引くために必要な`era_id`を、パイプライン実行中に保持していない。
2. `column_N`→意味的フィールド名マッピングの正データを置く既存の領域（`layouts/`・`knowledge/layout`のいずれも）が存在しない。

## 決定（Decision）

### 1. `RawRecord`に`layout_id: str`（era_id）を追加する

[ADR-0037](0037-layout-detector-produces-layout-artifact.md)が`PersonnelSection.layout_id: str`（era_id）を確定したのと同じ意味論の値を、`RawRecord`にも追加する。

```python
@dataclass(frozen=True, slots=True)
class RawRecord:
    section_ref: PersonnelSectionId | None
    layout_id: str  # era_id（新設）
    record_index: int
    raw_fields: Mapping[str, str]
    extracted_at: datetime
```

Field Extractorは、入力`PersonnelSection.layout_id`をそのまま`RawRecord.layout_id`にコピーする（Field Extractor自身が`layouts/`・`knowledge/`のいずれにも新たに依存する必要はなく、[ADR-0038](0038-field-extractor-produces-field-extraction-result.md)が確立した「`PersonnelSection`のみを入力とする」制約は維持される）。

### 2. `knowledge/layout`カテゴリのスコープを拡張する

[`docs/knowledge/schema.md`](../knowledge/schema.md)の`layout`カテゴリの定義を、以下のとおり拡張する。

- **参照する主な段階**: 「Section Parser / Field Extractor」に**Normalizerを追加**する。
- **性質**: 「特定レイアウト（era_id）固有の既知の例外・補足知識」を、「特定レイアウト（era_id）固有の補足構造情報（既知の例外に加え、列位置→意味的フィールド名マッピングを含む）」に拡張する。
- 既存の`LayoutEntry`スキーマ（`issue_type`/`affected_field`/`handling`による例外記述）はそのまま維持する。列位置マッピングを表現する新しいエントリ種別（例: `issue_type: "field_mapping"`、または`LayoutEntry`とは別の新フィールドの追加）の**具体的なJSON Schema拡張は本ADRの範囲外**とし、Normalizer実装タスク（Task8想定）で確定する。
- 物理ディレクトリ（`knowledge/layout_notes/`）・`era_id`が`layouts/<era_id>/`を参照するという参照整合性ルールは変更しない。

### 3. Normalizerは`KnowledgeSnapshot`経由でマッピングを取得する

Normalizerの入力契約（`Normalizer.run(context, record: RawRecord, knowledge: KnowledgeSnapshot) -> NormalizedRecord`、[`docs/api/interfaces.md`](../api/interfaces.md)）は変更しない。Normalizerは`record.layout_id`（本ADRで新設）をキーに、`knowledge`（`KnowledgeSnapshot`）内の`layout`カテゴリのマッピングエントリを検索し、`record.raw_fields`の`column_N`キーを意味的フィールド名に変換したうえで、既存の適用順序（typography → alias → organization/position/rank、[`docs/knowledge/schema.md`](../knowledge/schema.md#normalizervalidatorでの適用順序)）に従って正規化する。Normalizerは`knowledge/`のファイルI/O・`KnowledgeRepository`等のサービスそのものを知らず、値オブジェクト`KnowledgeSnapshot`のみを受け取るという既存方針（[`docs/api/dependency-rule.md`](../api/dependency-rule.md)の`normalizers/` → `knowledge/`の行）は変更しない。

## 検討した代替案

- **`LayoutDefinition`（`layouts/`）にフィールド抽出定義を追加し、Normalizerがこれを読み込む**: [ADR-0038](0038-field-extractor-produces-field-extraction-result.md)がField Extractorについて却下したのと同じ理由により却下した。`normalizers/`が`layouts/`に依存することは、「様式の構造定義（`layouts/`）」と「ドメイン知識（`knowledge/`）」を分離する既存方針（[ADR-0003](0003-layout-definition-strategy.md)、[ADR-0005](0005-knowledge-base-normalization.md)）に反する。
- **`Normalizer.run()`の入力契約を拡張し、呼び出し元がマッピングを別引数で注入する**: `Normalizer.run(context, record, knowledge)`という確立済みの3引数契約（[`docs/api/interfaces.md`](../api/interfaces.md)）を破壊的に変更することになり、「Normalizerは`KnowledgeSnapshot`という単一の値オブジェクト経由でのみ知識を得る」という既存方針をわざわざ崩す割に、`knowledge/layout`カテゴリの拡張で同じ目的を達成できるため採用しなかった。
- **Knowledge Baseに新カテゴリ（例: `field_mapping`）を新設する**: [`docs/knowledge/schema.md`](../knowledge/schema.md)の8カテゴリ分離方針の基準（「どの中核パイプライン段階が、どんな性質の知識を必要とするか」）に照らすと、列位置マッピングは「era_id固有の構造補足知識」であり、既存の`layout`カテゴリと本質的に同じ性質の知識である。新カテゴリを増やすより、既存`layout`カテゴリの範囲を「例外知識」から「補足構造情報全般」に広げる方が、既存の分離基準に忠実であり、8カテゴリという設計済みの分類自体を変更せずに済む。ユーザーの選択に基づき採用しなかった。

## 結果（トレードオフ, Consequences）

- `RawRecord`への`layout_id: str`追加は、既に実装済み（[Phase2 Task7](0038-field-extractor-produces-field-extraction-result.md)）の`RawRecord`に対する破壊的変更である。影響を受けるコードは以下（Migration節参照、本ADRでは変更しない）。
  - `src/mod_personnel_db/models/candidate.py`（`RawRecord`定義）
  - `src/mod_personnel_db/extractors/extractor.py`（`RawRecord`構築箇所）
  - `src/mod_personnel_db/repositories/sqlite/candidate.py`（`add_raw`・読み取り、`candidate_records`テーブルとのマッピング）
  - `tests/unit/models/test_extraction.py`, `tests/unit/extractors/`配下のテスト
- `candidate_records`テーブル（[`docs/database/schema.md`](../database/schema.md#4-candidate_records)）は現状`personnel_section_id`経由で`personnel_sections.layout_id`（era_id）をJOINで導出可能であり、`layout_id`列を新設するか、読み取り時にJOINで導出するかは実装判断であり、本ADRでは確定しない。
- `knowledge/layout`カテゴリのスコープ拡張は、[`docs/knowledge/schema.md`](../knowledge/schema.md)という人手レビュー済みの設計文書の記述変更を伴う。既存の`LayoutEntry`スキーマ・既存の物理配置・既存の`layout_notes/`エントリ（サンプル含む）とは非互換ではなく、追加的な拡張である。
- マッピングエントリの具体的なYAML構造（JSON Schema拡張）は未確定のまま残る。これはNormalizer実装タスク（Task8想定）で確定するべき、意図的に本ADRの範囲外とした事項である。

## Migration

1. `docs/knowledge/schema.md`の`layout`カテゴリの説明（8カテゴリの分離方針表・`layout`節本文・[Normalizer/Validatorでの適用順序](../knowledge/schema.md#normalizervalidatorでの適用順序)）を本ADRの決定に同期する（同一PR）。
2. `docs/api/models.md`の`RawRecord`に`layout_id: str`を追記する（同一PR、コードは変更しない）。
3. 実装（Normalizer実装タスク、Task8想定）で以下を行う。
   - `src/mod_personnel_db/models/candidate.py`の`RawRecord`に`layout_id: str`フィールドを追加。
   - `src/mod_personnel_db/extractors/extractor.py`で`section.layout_id`を`RawRecord.layout_id`にコピーする処理を追加。
   - `src/mod_personnel_db/repositories/sqlite/candidate.py`の`add_raw`・読み取りロジックを追随修正。
   - `knowledge/layout_notes/`のエントリスキーマに列位置マッピングを表現する具体的なJSON Schema拡張を追加。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`docs/knowledge/schema.md`](../knowledge/schema.md) | `layout`カテゴリの参照段階にNormalizerを追加。性質の説明を「例外知識」から「補足構造情報全般（例外＋列位置マッピング）」に拡張 |
| [`docs/api/models.md`](../api/models.md) | `RawRecord`に`layout_id: str`を追記し、Normalizerがこれを用いて`knowledge/layout`のマッピングを参照する旨を記述 |

## 関連ADR
- [ADR-0003](0003-layout-definition-strategy.md) — Layout外部データ定義戦略。`layouts/`（構造定義）と`knowledge/layout`（補足知識）の役割分担の前提。
- [ADR-0005](0005-knowledge-base-normalization.md) — Knowledge Base全体の設計方針。Normalizerが`KnowledgeSnapshot`のみを受け取るという既存方針の前提。
- [ADR-0011](0011-fixed-core-pipeline.md) — 中核パイプラインの固定化。段階の数・順序・名称は本ADRでも変更しない。
- [ADR-0012](0012-error-handling-priority-order.md) — 未知パターンへの対応優先順位。Knowledge Base追加を優先するという方針を、Normalizerの列位置マッピング解決にも適用する。
- [ADR-0037](0037-layout-detector-produces-layout-artifact.md) — `PersonnelSection.layout_id: str`（era_id）の型決定の先例。本ADRの`RawRecord.layout_id`追加はこれと同型。
- [ADR-0038](0038-field-extractor-produces-field-extraction-result.md) — 本ADRが解決を委譲された「`column_N`から意味的フィールド名への対応付け」の起点。

（本ADRはADR-0003/0005/0011/0012/0037/0038のいずれの核心決定も変更しないため、Supersededにはしない。）
