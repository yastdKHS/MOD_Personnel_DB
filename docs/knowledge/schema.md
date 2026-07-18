# Knowledge Base スキーマ設計

> **位置づけ**: 本ドキュメントは `knowledge/` 配下に置かれるYAMLファイルの構造契約を定義します。`knowledge/` のファイルが正（source of truth）であり、[`docs/database/schema.md`](../database/schema.md) の `knowledge_items` テーブルはそれをロード・インデックスしたものです（[ADR-0005](../adr/0005-knowledge-base-normalization.md)）。
>
> **「YAML Schema」の表記について**: YAML専用のスキーマ標準は存在しないため、YAMLファイルをパースした結果（Pythonの `dict` 等）に対し、[公開JSON仕様](../database/json_schema.md)と同じくJSON Schema Draft 2020-12を適用して検証する。本ドキュメント中のスキーマは、Pythonの `jsonschema`（Draft 2020-12実装）でメタスキーマ検証済み、各カテゴリのYAML例は実際にYAMLとしてパースした上でスキーマ検証済みである。
>
> **コードはまだ実装していません。** 本ドキュメントは設計仕様であり、実データ（実際の組織名・階級名等）はまだ `knowledge/` に投入していません。

## 目次

1. [8カテゴリの分離方針](#8カテゴリの分離方針)
2. [カテゴリと物理ディレクトリの対応](#カテゴリと物理ディレクトリの対応)
3. [共通定義](#共通定義)
4. [JSON Schema本体](#json-schema本体)
5. [カテゴリ詳細](#カテゴリ詳細)
   - [organization](#organization)
   - [position](#position)
   - [rank](#rank)
   - [alias](#alias)
   - [historical](#historical)
   - [typography](#typography)
   - [layout](#layout)
   - [validation](#validation)
6. [Normalizer/Validatorでの適用順序](#normalizervalidatorでの適用順序)
7. [Draft 2020-12に関する留意事項](#draft-2020-12に関する留意事項)
8. [実装時の配置（想定）](#実装時の配置想定)
9. [関連ADR](#関連adr)

---

## 8カテゴリの分離方針

ドメイン知識を単一の雑多な「knowledge」にせず、以下の8カテゴリに分離する。分離の基準は「**どの中核パイプライン段階（[ADR-0011](../adr/0011-fixed-core-pipeline.md)）が、どんな性質の知識を必要とするか**」である。

| カテゴリ | 参照する主な段階 | 性質 |
|---|---|---|
| `organization` | Normalizer | 組織・部隊名の名称エンティティ（時期ごとの正式名称） |
| `position` | Normalizer | 官職・補職名の名称エンティティ |
| `rank` | Normalizer / Validator | 階級呼称の名称エンティティ＋序列 |
| `alias` | Normalizer | 氏名の異体字・別名（個人に紐づく表記ゆれ） |
| `historical` | Normalizer（監査・遡及） | 組織改称・制度改正等の変更イベントそのもの |
| `typography` | Normalizer（前処理） | 文字種・表記法の機械的な正規化ルール |
| `layout` | Section Parser / Field Extractor | 特定レイアウト（era_id）固有の既知の例外・補足知識 |
| `validation` | Validator | 許容値・制約ルール（何が「あり得る値」か） |

**`organization` / `position` / `rank` と `historical` の役割分担**: `organization` / `position` / `rank` は「ある名称がいつからいつまで正式だったか」という**状態**を保持する（改称のたびに新しいエンティティを追加し、`predecessor_id` / `successor_id` で連結する）。一方 `historical` は「なぜ・どの資料に基づいて改称されたか」という**変更イベントそのもの**を保持する。同じ情報を二重管理しないよう、状態は名称エンティティ側に、変更の経緯・根拠は `historical` 側に置く。

**`typography` と `alias` の役割分担**: `typography` は全角/半角・旧字体/新字体・空白等、**値に依存しない機械的な文字レベルの変換規則**（例: 全角数字→半角数字）。`alias` は**特定の個人に紐づく**、機械的規則では導けない表記対応（例: 特定の人物の旧字体氏名と現行表記の対応）。Normalizerは常に `typography` を先に適用し、その後で `alias` / `organization` / `position` / `rank` の名称マッチングを行う（[適用順序](#normalizervalidatorでの適用順序)）。

**`layout` とトップレベル `layouts/` の役割分担**: トップレベルの `layouts/`（[ADR-0003](../adr/0003-layout-definition-strategy.md)）は、様式の**構造定義**（列位置・見出しパターン等）を保持する正データである。`knowledge/` の `layout` カテゴリは、その構造定義だけでは表現しきれない、**特定era_id内で発生する既知の例外・補足知識**（例: 特定月のみ発令日が和暦表記になっている等）を保持する。構造そのものを変えたい場合は `layouts/` を、構造は変えず例外的な扱いを追記したい場合は `knowledge/layout` を更新する、という使い分けを行う。物理ディレクトリ名は `layouts/` との混同を避けるため `knowledge/layout_notes/` とする（[カテゴリと物理ディレクトリの対応](#カテゴリと物理ディレクトリの対応)）。

**`validation` の新規性**: 従来、Validatorが「あり得る階級か」等を判定する基準は未定義だった。`validation` カテゴリにより、この基準自体をコードではなくデータとして表現する（[ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位方針をValidatorにも拡張適用する）。

---

## カテゴリと物理ディレクトリの対応

| カテゴリ（`category`値） | 物理ディレクトリ | 既存構成からの変更 |
|---|---|---|
| `organization` | `knowledge/organizations/` | 既存を継続 |
| `position` | `knowledge/positions/` | **新設** |
| `rank` | `knowledge/ranks/` | 既存を継続 |
| `alias` | `knowledge/aliases/` | 既存を継続 |
| `historical` | `knowledge/historical/` | **新設** |
| `typography` | `knowledge/typography/` | **新設** |
| `layout` | `knowledge/layout_notes/` | `knowledge/known_issues/` を改称（トップレベル `layouts/` との名称衝突を避けるため） |
| `validation` | `knowledge/validation/` | **新設** |

`knowledge/learning_dataset/`（[ADR-0013](../adr/0013-learning-dataset-not-correction-log.md)）は本ドキュメントが定める8カテゴリとは別の関心事（誤り修正の構造化データセット）であり、対象外として現状維持する。

---

## 共通定義

全カテゴリで共通して使う部品を `$defs` として先に定義する。

- **`Provenance`**: このエントリの根拠。`source`（必須、根拠資料名）、`source_url`（任意）、`note`（任意）。
- **`VersionInfo`**: このエントリ自体の改訂バージョン。`version`（必須、整数、内容変更のたびに増分）、`updated_at`（必須、更新日）、`updated_by`（任意）。
- **`AliasVariant`**: 表記バリエーション1件。`value`（必須）、`kind`（必須、`abbreviation` / `common_name` / `typographic_variant`）。
- **`RelatedEntryRef`**: `historical` エントリが指し示す、変更前後のエンティティへの参照。`category`（`organization` / `position` / `rank`）、`id`。

---

## JSON Schema本体

以下は `jsonschema`（Python、Draft 2020-12実装）でメタスキーマ検証済みである。トップレベルは `oneOf` により、`category` の値に応じて8つの定義のいずれか1つに一致することを要求する。

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.mod-personnel-db.example/knowledge-entry/v1/schema.json",
  "title": "Knowledge Base Entry",
  "description": "knowledge/配下の8カテゴリ(organization/position/rank/alias/historical/typography/layout/validation)のYAMLエントリが満たすべき契約。",
  "oneOf": [
    { "$ref": "#/$defs/OrganizationEntry" },
    { "$ref": "#/$defs/PositionEntry" },
    { "$ref": "#/$defs/RankEntry" },
    { "$ref": "#/$defs/AliasEntry" },
    { "$ref": "#/$defs/HistoricalEntry" },
    { "$ref": "#/$defs/TypographyEntry" },
    { "$ref": "#/$defs/LayoutEntry" },
    { "$ref": "#/$defs/ValidationEntry" }
  ],
  "$defs": {
    "Provenance": {
      "type": "object",
      "title": "Provenance",
      "description": "このエントリの根拠。",
      "required": ["source"],
      "additionalProperties": false,
      "properties": {
        "source": { "type": "string", "minLength": 1, "description": "根拠資料(例: 防衛省組織令、官報等)" },
        "source_url": { "type": "string", "format": "uri" },
        "note": { "type": "string" }
      }
    },
    "VersionInfo": {
      "type": "object",
      "title": "VersionInfo",
      "description": "このエントリ自体の改訂バージョン。",
      "required": ["version", "updated_at"],
      "additionalProperties": false,
      "properties": {
        "version": { "type": "integer", "minimum": 1 },
        "updated_at": { "type": "string", "format": "date" },
        "updated_by": { "type": "string" }
      }
    },
    "AliasVariant": {
      "type": "object",
      "title": "AliasVariant",
      "required": ["value", "kind"],
      "additionalProperties": false,
      "properties": {
        "value": { "type": "string", "minLength": 1 },
        "kind": {
          "type": "string",
          "enum": ["abbreviation", "common_name", "typographic_variant"]
        }
      }
    },
    "RelatedEntryRef": {
      "type": "object",
      "title": "RelatedEntryRef",
      "required": ["category", "id"],
      "additionalProperties": false,
      "properties": {
        "category": { "type": "string", "enum": ["organization", "position", "rank"] },
        "id": { "type": "string" }
      }
    },
    "OrganizationEntry": {
      "type": "object",
      "title": "OrganizationEntry",
      "description": "組織・部隊名の名称期間エンティティ。knowledge/organizations/配下。",
      "required": ["id", "category", "canonical_name", "effective_from", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^org-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "organization" },
        "canonical_name": { "type": "string", "minLength": 1 },
        "aliases": { "type": "array", "items": { "$ref": "#/$defs/AliasVariant" } },
        "effective_from": { "type": "string", "format": "date" },
        "effective_to": { "type": ["string", "null"], "format": "date" },
        "predecessor_id": { "type": ["string", "null"] },
        "successor_id": { "type": ["string", "null"] },
        "historical_event_ref": { "type": ["string", "null"] },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "PositionEntry": {
      "type": "object",
      "title": "PositionEntry",
      "description": "官職・補職名の名称期間エンティティ。knowledge/positions/配下。",
      "required": ["id", "category", "canonical_title", "effective_from", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^pos-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "position" },
        "canonical_title": { "type": "string", "minLength": 1 },
        "aliases": { "type": "array", "items": { "$ref": "#/$defs/AliasVariant" } },
        "organization_scope": { "type": ["string", "null"], "description": "この官職が属する組織区分への参照(任意、organizations/のidを想定)" },
        "effective_from": { "type": "string", "format": "date" },
        "effective_to": { "type": ["string", "null"], "format": "date" },
        "predecessor_id": { "type": ["string", "null"] },
        "successor_id": { "type": ["string", "null"] },
        "historical_event_ref": { "type": ["string", "null"] },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "RankEntry": {
      "type": "object",
      "title": "RankEntry",
      "description": "階級呼称の名称期間エンティティ。knowledge/ranks/配下。",
      "required": ["id", "category", "canonical_name", "service_branch", "rank_order", "effective_from", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^rank-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "rank" },
        "canonical_name": { "type": "string", "minLength": 1 },
        "service_branch": { "type": "string", "enum": ["ground", "maritime", "air", "joint"] },
        "rank_order": { "type": "integer", "minimum": 1, "description": "同一service_branch内での階級序列(数値が大きいほど上位)。Validatorの妥当性検証に使う。" },
        "aliases": { "type": "array", "items": { "$ref": "#/$defs/AliasVariant" } },
        "effective_from": { "type": "string", "format": "date" },
        "effective_to": { "type": ["string", "null"], "format": "date" },
        "predecessor_id": { "type": ["string", "null"] },
        "successor_id": { "type": ["string", "null"] },
        "historical_event_ref": { "type": ["string", "null"] },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "AliasEntry": {
      "type": "object",
      "title": "AliasEntry",
      "description": "氏名等の異体字・別名。knowledge/aliases/配下。",
      "required": ["id", "category", "target_type", "canonical_value", "variants", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^alias-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "alias" },
        "target_type": { "type": "string", "enum": ["person_name"] },
        "canonical_value": { "type": "string", "minLength": 1 },
        "variants": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["value", "kind"],
            "additionalProperties": false,
            "properties": {
              "value": { "type": "string", "minLength": 1 },
              "kind": { "type": "string", "enum": ["old_glyph", "itaiji", "misprint", "honorific_variant"] }
            }
          }
        },
        "effective_from": { "type": ["string", "null"], "format": "date" },
        "effective_to": { "type": ["string", "null"], "format": "date" },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "HistoricalEntry": {
      "type": "object",
      "title": "HistoricalEntry",
      "description": "組織改称・階級制度改正等の変更イベント。knowledge/historical/配下。",
      "required": ["id", "category", "event_type", "occurred_on", "description", "related_entries", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^hist-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "historical" },
        "event_type": {
          "type": "string",
          "enum": ["organization_rename", "organization_merge", "organization_split", "rank_system_reform", "position_rename", "other"]
        },
        "occurred_on": { "type": "string", "format": "date" },
        "description": { "type": "string", "minLength": 1 },
        "related_entries": {
          "type": "object",
          "required": ["from", "to"],
          "additionalProperties": false,
          "properties": {
            "from": { "type": "array", "items": { "$ref": "#/$defs/RelatedEntryRef" } },
            "to": { "type": "array", "items": { "$ref": "#/$defs/RelatedEntryRef" } }
          }
        },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "TypographyEntry": {
      "type": "object",
      "title": "TypographyEntry",
      "description": "表記・文字種の機械的な正規化ルール。knowledge/typography/配下。",
      "required": ["id", "category", "rule_type", "pattern", "replacement", "applies_to", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^typo-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "typography" },
        "rule_type": {
          "type": "string",
          "enum": ["fullwidth_halfwidth", "old_new_glyph", "whitespace_normalization", "symbol_normalization", "other"]
        },
        "pattern": { "type": "string", "minLength": 1, "description": "対象パターン(リテラル文字列、または正規表現)" },
        "replacement": { "type": "string" },
        "applies_to": {
          "type": "string",
          "enum": ["all", "person_name", "organization_name", "position_title", "rank_name"]
        },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "LayoutEntry": {
      "type": "object",
      "title": "LayoutEntry",
      "description": "特定レイアウト(era_id)に固有の既知の例外・補足知識。knowledge/layout_notes/配下。トップレベルのlayouts/(構造定義)を補足する。",
      "required": ["id", "category", "era_id", "issue_type", "description", "affected_field", "handling", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^layoutnote-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "layout" },
        "era_id": { "type": "string", "description": "layouts/<era_id>/への参照" },
        "issue_type": {
          "type": "string",
          "enum": ["ocr_artifact", "alternate_date_format", "extra_whitespace_column", "section_boundary_exception", "other"]
        },
        "description": { "type": "string", "minLength": 1 },
        "affected_field": {
          "type": "string",
          "enum": ["section_boundary", "name", "rank", "organization", "position", "effective_date", "other"]
        },
        "handling": { "type": "string", "minLength": 1, "description": "Section Parser/Field Extractorが参照する対応方法の説明" },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    },
    "ValidationEntry": {
      "type": "object",
      "title": "ValidationEntry",
      "description": "Validatorが参照する制約・許容値ルール。knowledge/validation/配下。",
      "required": ["id", "category", "rule_type", "target_field", "constraint", "severity", "description", "provenance", "version"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^val-[a-z0-9]+(-[a-z0-9]+)*$" },
        "category": { "const": "validation" },
        "rule_type": {
          "type": "string",
          "enum": ["allowed_value_set", "cross_field_constraint", "date_range_constraint", "other"]
        },
        "target_field": { "type": "string", "minLength": 1, "description": "検証対象のフィールド名(例: 'rank', 'appointment_type')" },
        "constraint": {
          "type": "object",
          "minProperties": 1,
          "description": "rule_typeごとの制約定義。形状はrule_typeに依存する(本文の表を参照)。"
        },
        "severity": { "type": "string", "enum": ["error", "warning"] },
        "description": { "type": "string", "minLength": 1 },
        "provenance": { "$ref": "#/$defs/Provenance" },
        "version": { "$ref": "#/$defs/VersionInfo" }
      }
    }
  }
}
```

---

## カテゴリ詳細

各カテゴリについて、YAML例（`#/$defs/<Name>Entry` に対し検証済み）、Version（このカテゴリにおけるバージョン管理の意味）、Validation Rule（スキーマで表現しきれない意味的な制約）、更新ルールを記す。

### organization

**YAML例**（`knowledge/organizations/jgsdf-1st-division-1962.yaml`）:

```yaml
id: org-jgsdf-1st-division-1962
category: organization
canonical_name: "陸上自衛隊第1師団"
aliases:
  - value: "陸自第1師団"
    kind: abbreviation
  - value: "第１師団"
    kind: typographic_variant
effective_from: "1962-01-01"
effective_to: null
predecessor_id: null
successor_id: null
historical_event_ref: null
provenance:
  source: "防衛省組織令"
  source_url: "https://www.mod.go.jp/example/order.html"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: エントリ自体は `version.version` で改訂管理する（例: `aliases` に新しい表記ゆれを追加したら `version` を+1し `updated_at` を更新）。組織が改称された場合は既存エントリの `version` を上げるのではなく、`effective_to` を設定した上で**新しいエンティティ（新しい `id`）を追加**し、`successor_id` / `predecessor_id` で連結する（名称期間ごとに別エンティティとする設計、[8カテゴリの分離方針](#8カテゴリの分離方針)参照）。
- **Validation Rule**: (1) `effective_to` が設定されている場合、`successor_id` も設定されていること（改称後のエンティティが必ず存在する）。(2) `predecessor_id` / `successor_id` は同ディレクトリ内の別エントリの `id` を指すこと（参照整合性）。(3) 同一 `canonical_name` を持つ有効期間が重複する2エントリが存在しないこと（Publish段階での名寄せの一意性確保）。これらはJSON Schema単体では表現できないため、Normalizerロード時のアプリケーション層チェックとする。
- **更新ルール**: 新規追加・`aliases` の追加は通常のPRレビューで足りる。改称（新エンティティ追加＋`predecessor_id`/`successor_id`連結）を行う場合は、対応する `historical` エントリを同一PR内で追加すること。出典（`provenance.source`）を伴わない追加は認めない。

---

### position

**YAML例**（`knowledge/positions/division-commander.yaml`）:

```yaml
id: pos-division-commander
category: position
canonical_title: "師団長"
aliases:
  - value: "師団長職"
    kind: common_name
organization_scope: org-jgsdf-1st-division-1962
effective_from: "1962-01-01"
effective_to: null
predecessor_id: null
successor_id: null
historical_event_ref: null
provenance:
  source: "自衛隊法施行令"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: `organization` と同様、名称変更は新エンティティ追加＋連結で表現する。`organization_scope` の変更（所属組織区分の見直し）のみの場合は既存エントリの `version` を+1する。
- **Validation Rule**: `organization_scope` を設定する場合、`knowledge/organizations/` に存在する `id` を指すこと（参照整合性）。`organization_scope` は任意項目であり、複数組織に共通する官職（例: 特定の部隊種別に依存しない職名）の場合は `null` のままでよい。
- **更新ルール**: `organization` と同様の方針。官職名は制度上の根拠（自衛隊法施行令等）を `provenance` に明記する。

---

### rank

**YAML例**（`knowledge/ranks/1st-lieutenant-ground.yaml`）:

```yaml
id: rank-1st-lieutenant-ground
category: rank
canonical_name: "1等陸尉"
service_branch: ground
rank_order: 9
aliases:
  - value: "1尉"
    kind: abbreviation
effective_from: "1954-07-01"
effective_to: null
predecessor_id: null
successor_id: null
historical_event_ref: null
provenance:
  source: "自衛隊法"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: 階級呼称・序列は制度変更でしか変わらないため、`aliases` の追加以外での改訂は稀。制度改正（例: 階級区分の新設・統合）の場合は `historical`（`event_type: rank_system_reform`）を伴う新エンティティ追加とする。
- **Validation Rule**: (1) 同一 `service_branch` 内で `rank_order` が一意であること（同順位の階級が2つ存在してはならない）。(2) `rank_order` は数値が大きいほど上位となるよう、`service_branch` 内で連続または単調増加であること。これらは `knowledge/validation/` のルールとしてではなく、`rank` カテゴリ自体のロード時整合性チェックとしてアプリケーション層で担保する（Validatorが実行時に参照する制約は別途 `validation` カテゴリで定義する、[validation](#validation)参照）。
- **更新ルール**: `rank_order` の変更は、既存の階級順序比較（Validatorの「あり得る階級か」判定）に影響するため、変更PRには影響範囲（どの `validation` エントリ・どの期間のデータに影響するか）を明記する。

---

### alias

**YAML例**（`knowledge/aliases/example-person-001.yaml`、氏名は架空例）:

```yaml
id: alias-example-person-001
category: alias
target_type: person_name
canonical_value: "髙橋一郎"
variants:
  - value: "高橋一郎"
    kind: old_glyph
  - value: "高橘一郎"
    kind: misprint
effective_from: null
effective_to: null
provenance:
  source: "本人確認済み表記(架空例)"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: `variants` への追加のたびに `version` を+1する。氏名変更（改姓等）を扱う場合は `effective_from` / `effective_to` を設定し、新しい `canonical_value` を持つ新エンティティを追加する（`organization`等と同じ「名称期間ごとに別エンティティ」パターン）。
- **Validation Rule**: `variants` は最低1件必須（表記ゆれの対応がないエントリは無意味なため）。`canonical_value` と同一の `value` を `variants` に重複して含めないこと。
- **更新ルール**: 個人の氏名表記に関わるため、[ADR-0008](../adr/0008-data-ethics-policy.md)の個人情報方針に従い、根拠のない推測による表記統合は行わない。`provenance.source` に本人確認・公的文書等の具体的根拠を明記できない場合はエントリを追加しない。

---

### historical

**YAML例**（`knowledge/historical/2024-001.yaml`、内容は架空例）:

```yaml
id: hist-2024-001
category: historical
event_type: organization_rename
occurred_on: "2024-03-01"
description: "架空例: 第1師団の隷下部隊再編に伴う組織改称。"
related_entries:
  from:
    - category: organization
      id: org-jgsdf-1st-division-1962
  to:
    - category: organization
      id: org-jgsdf-1st-division-2024
provenance:
  source: "防衛省組織令改正(架空例)"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: 変更イベントの記述は原則として追記後に内容を変えない（イベントログ的性質）。誤記の修正のみ `version` を+1して行う。
- **Validation Rule**: `related_entries.from` / `related_entries.to` が指す `id` は、それぞれ対応するカテゴリ（`organization` / `position` / `rank`）のディレクトリに実在すること。`organization_merge` / `organization_split` の場合、`from` または `to` のいずれかが複数件になり得る（多対1・1対多の変更を表現するため配列とした設計理由）。
- **更新ルール**: `organization` / `position` / `rank` 側で改称・改編を反映するPRには、対応する `historical` エントリの追加を必須とする（[8カテゴリの分離方針](#8カテゴリの分離方針)の役割分担を維持するため）。

---

### typography

**YAML例**（`knowledge/typography/fullwidth-digit.yaml`）:

```yaml
id: typo-fullwidth-digit
category: typography
rule_type: fullwidth_halfwidth
pattern: "０-９"
replacement: "0-9"
applies_to: all
provenance:
  source: "正規化方針(内部決定)"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: ルールの `pattern` / `replacement` を変更すると、過去に正規化済みのデータの再現性に影響するため、変更時は `version` を+1し、影響範囲（再正規化が必要なデータ範囲）をPR説明に明記する。
- **Validation Rule**: `pattern` は空文字列不可。`applies_to` を `all` にする場合、他の3カテゴリ（`organization` / `alias` 等）の正規化結果を意図せず変えないか、影響範囲を確認すること（意味的チェックのため、ロード時の自動検証ではなくレビューで担保する）。
- **更新ルール**: 単純な文字対応の追加は通常のPRレビューで足りる。既存ルールの `pattern` / `replacement` の変更（過去データへの遡及的影響があり得る変更）は、[ADR-0014](../adr/0014-development-discipline.md)の「1PR1責務」に従い、他のカテゴリ変更と混ぜない単独PRとする。

---

### layout

**YAML例**（`knowledge/layout_notes/2022-format-b-date-typo.yaml`、内容は架空例）:

```yaml
id: layoutnote-2022-format-b-date-typo
category: layout
era_id: 2022_format_b
issue_type: alternate_date_format
description: "架空例: 2022年10月分のみ発令日が和暦表記になっている。"
affected_field: effective_date
handling: "和暦検出時はknowledge/typographyの和暦変換ルールを適用してから正規化する。"
provenance:
  source: "2022年10月分PDF(架空例、content_hashは実装時に記録)"
version:
  version: 1
  updated_at: "2026-07-18"
```

- **Version**: 同一 `era_id` 内で新しい例外が見つかるたびに新規エントリを追加する（既存エントリの上書きではなく追記）。`handling` の記述を改善した場合のみ `version` を+1する。
- **Validation Rule**: `era_id` は `layouts/<era_id>/` に実在する様式を指すこと（トップレベル `layouts/` との参照整合性）。同一 `era_id` + `issue_type` + `affected_field` の組み合わせで重複エントリを作らない（既存エントリの `handling` を拡充すること）。
- **更新ルール**: [ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位ルールにより、Section Parser/Field Extractorの例外処理をコードに追加する前に、まず本カテゴリへの追加で対応できないか検討すること。`layout` エントリで対応しきれない構造的な差異（列位置そのものが違う等）は、`knowledge/layout_notes/` ではなくトップレベル `layouts/` への新規様式追加で対応する。

---

### validation

**YAML例**（`knowledge/validation/rank-allowed-values-ground.yaml`、値は例示）:

```yaml
id: val-rank-allowed-values-ground
category: validation
rule_type: allowed_value_set
target_field: rank
constraint:
  values:
    - "2等陸士"
    - "1等陸士"
    - "3等陸曹"
    - "2等陸曹"
    - "1等陸曹"
    - "曹長"
    - "准陸尉"
    - "3等陸尉"
    - "2等陸尉"
    - "1等陸尉"
    - "3等陸佐"
    - "2等陸佐"
    - "1等陸佐"
    - "陸将補"
    - "陸将"
severity: error
description: "陸上自衛官の階級として許容される値の一覧。"
provenance:
  source: "自衛隊法"
version:
  version: 1
  updated_at: "2026-07-18"
```

`constraint` の内部形状は `rule_type` ごとに以下の慣例とする（JSON Schemaでは `rule_type` ごとの厳密な条件分岐までは強制せず、レビューで担保する。理由は[Validation Ruleの項](#validation-1)を参照）。

| `rule_type` | `constraint` の慣例的な形状 |
|---|---|
| `allowed_value_set` | `{ "values": [string, ...] }` |
| `cross_field_constraint` | `{ "if_field": string, "if_value": string, "then_field": string, "then_allowed": [string, ...] }` |
| `date_range_constraint` | `{ "min_date": string\|null, "max_date": string\|null }` |

- **Version**: 許容値集合（`allowed_value_set`）は `rank` カテゴリの改訂と連動することが多い。`rank` に新しい階級エンティティを追加した場合、対応する `validation` エントリの `constraint.values` も同一PRで更新すること。
- **Validation Rule**: `constraint` は空オブジェクト不可（`minProperties: 1`）。`severity: error` のルール違反はValidatorが `candidate_records.validation_status = 'failed'` とする根拠になり、`severity: warning` は `learning_dataset` への記録対象とはなるが `failed` にはしない（[`schema.md`](../database/schema.md)の `candidate_records` / `learning_dataset` 設計と対応）。
- **更新ルール**: 新しいValidatorの制約を追加する際、まず本カテゴリへのデータ追加で表現できないか検討し、表現できない複雑な制約のみ `src/` の例外処理とする（[ADR-0012](../adr/0012-error-handling-priority-order.md)の優先順位をValidatorにも適用）。`severity: error` への変更（`warning` → `error`）は、既存データへの影響（新たに `failed` になるレコードが発生し得る）があるため、影響件数の見積もりをPR説明に含めること。

---

## Normalizer/Validatorでの適用順序

Normalizerは、以下の順序で `knowledge/` の各カテゴリを適用する（[`architecture.md`](../architecture.md)のNormalizer責務を具体化したもの）。

```
1. typography  (文字種の機械的正規化。全角/半角、旧字体/新字体等)
2. alias       (人名の個別表記ゆれの解決)
3. organization / position / rank (名称エンティティへのマッチング。有効期間(effective_from/to)は発令日で絞り込む)
```

Validatorは、Normalizer出力に対して `validation` カテゴリの各エントリ（`severity` 別）を適用する。`historical` と `layout` はNormalizer/Validatorの実行時判定には直接使わず、監査・保守（なぜこの値になっているかの説明、新様式対応時の参照）のための知識として位置づける。

---

## Draft 2020-12に関する留意事項

[`json_schema.md`](../database/json_schema.md#draft-2020-12に関する留意事項)で述べた留意事項（`$defs`の使用、`format`のアノテーション既定動作、`additionalProperties: false`による生成時品質ゲートとしての位置づけ）は本スキーマにも同様に適用される。本スキーマ固有の点として:

- **`oneOf` によるカテゴリ判別**: 8つの `$defs` 定義はいずれも `category` に `const` 制約を持つため、ある `category` 値に対して `oneOf` の候補が2つ以上マッチすることはない（`oneOf` は「ちょうど1つ」を要求するため、複数マッチ・ゼロマッチはいずれもバリデーションエラーになる）。これにより、`category` の書き間違い（例: 存在しない値）は即座に検出される。

---

## 実装時の配置（想定）

- **正のスキーマファイル**: `src/mod_personnel_db/normalizer/schemas/knowledge_entry.v1.schema.json`（実装着手時に作成。内容は本ドキュメントの[JSON Schema本体](#json-schema本体)と同一に保つ）。
- **検証の実施箇所**: Normalizer / Validatorの起動時、`knowledge/` 配下の全YAMLファイルを読み込む際に本スキーマで検証し、不合格のファイルがあればロード自体を失敗させる（不正な知識データでパイプラインを動かさないための品質ゲート）。
- 本ドキュメントとスキーマファイルの内容が乖離した場合、スキーマファイルを正とし、本ドキュメントを追随して更新する。

---

## 関連ADR

- [ADR-0003](../adr/0003-layout-definition-strategy.md): `layout` カテゴリとトップレベル `layouts/` の役割分担の前提
- [ADR-0005](../adr/0005-knowledge-base-normalization.md): Knowledge Base全体の設計方針
- [ADR-0008](../adr/0008-data-ethics-policy.md): `alias` カテゴリの個人情報取り扱い方針
- [ADR-0011](../adr/0011-fixed-core-pipeline.md): 各カテゴリと中核パイプライン段階の対応関係
- [ADR-0012](../adr/0012-error-handling-priority-order.md): `layout` / `validation` カテゴリの優先順位方針
- [ADR-0014](../adr/0014-development-discipline.md): 更新ルールにおける1PR1責務の適用
