# knowledge/

## 責務

パースロジック（コード）ではなく、**人手でレビューされるべきドメイン知識**を構造化データとして保持する場所。設計判断の背景は [ADR-0005](../docs/adr/0005-knowledge-base-normalization.md) を参照。

「これはコードか、データか」の判断基準: **時間とともに項目が増える／出典に基づいて正誤が判断できる**ものは `knowledge/`、**入力に対して常に同じ処理をする手続き**は `src/`。

## 構成

ドメイン知識は8カテゴリに分離する。各カテゴリのYAML構造・バージョン管理・検証ルール・更新ルールの詳細な定義は [`docs/knowledge/schema.md`](../docs/knowledge/schema.md) を参照（[ADR-0005](../docs/adr/0005-knowledge-base-normalization.md)）。

> **現在の実データ形式について**: `docs/knowledge/schema.md`が定めるカテゴリ別のリッチなJSON Schema（`OrganizationEntry`等、`provenance`/`version`オブジェクトを持つ構造）は設計目標であり、まだ実装に橋渡しされていない。実装済みの読み込みコード（`src/mod_personnel_db/knowledge/loader.py`）は、各カテゴリディレクトリ配下のYAMLファイルを、トップレベルが`items:`（リスト）で、各要素が`item_key`・`canonical_value`・`provenance_source`（必須）と`effective_from`/`effective_to`/`version`（任意）を持つ、より単純なフラット形式として読み込む。Phase6 Task14-0で各カテゴリに追加した最小構成の実データは、この実装済みのフラット形式に従っている（詳細は各サブディレクトリの`README.md`を参照）。

| ディレクトリ | `category` | 内容 |
|---|---|---|
| `organizations/` | `organization` | 部隊・機関名の名称期間エンティティ |
| `positions/` | `position` | 官職・補職名の名称期間エンティティ |
| `ranks/` | `rank` | 階級呼称の名称期間エンティティ＋序列 |
| `aliases/` | `alias` | 氏名の異体字・旧字体等、個人に紐づく表記対応 |
| `historical/` | `historical` | 組織改称・制度改正等の変更イベント（`organization`/`position`/`rank`の経緯・根拠） |
| `typography/` | `typography` | 全角/半角・旧字体/新字体等、値に依存しない機械的な文字正規化ルール |
| `layout_notes/` | `layout` | 特定レイアウト（`era_id`）固有の既知の例外・補足知識（トップレベル`layouts/`を補足） |
| `validation/` | `validation` | Validatorが参照する許容値・制約ルール |

上記8カテゴリとは別の関心事として、以下も `knowledge/` 配下に置く。

| ディレクトリ | 内容 |
|---|---|
| `learning_dataset/` | 検証NG・誤り修正の構造化データセット（Correction Logではなく学習資産として設計、[ADR-0013](../docs/adr/0013-learning-dataset-not-correction-log.md)） |

各サブディレクトリの詳細は、それぞれの `README.md` を参照。

## 変更ルール

- `knowledge/` の変更は通常のコード変更と同じくPRレビューを経る。ただしレビュー観点は「ロジックの正しさ」ではなく「データの正しさ・出典の妥当性」である。
- 変更PRには、追加・修正の根拠（どのPDF・どの公表資料に基づくか）を明記する。
- 自動生成・一括置換による書き換えは行わない。差分が説明可能な単位でコミットする（`CLAUDE.md` / `AGENTS.md` 参照）。
- 既存データの削除は行わず、時点情報（いつまで有効だったか）を付与して履歴として残すことを基本方針とする。

## 未知パターンに遭遇したときの優先順位

新しい表記ゆれ・組織名・階級・PDFの例外に遭遇した場合、`src/` に正規表現や例外処理を追加するより先に、まず本ディレクトリへのデータ追加で解決できないかを検討する。`layouts/` への追加や `src/` の例外処理より優先する（[ADR-0012](../docs/adr/0012-error-handling-priority-order.md)）。
