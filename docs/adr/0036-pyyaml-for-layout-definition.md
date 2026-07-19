# 0036. LayoutDefinitionの実装にPyYAMLを採用する

## ステータス
Accepted

## コンテキスト

Phase2 Task5（Layout Detector Implementation）は、`LayoutDefinition`（Layout判定ルールの保持）を「YAMLからロード可能な構造」とすることを求めている。[`layouts/README.md`](../../layouts/README.md)は、`layouts/<era_id>/manifest.yaml`にレイアウト定義を持たせる想定を既に示していたが、そのスキーマ・パーサーの選定は「形式は仮」として未確定のままだった。

本プロジェクトは`pyproject.toml`の`dependencies`が空であり（[ADR-0001](0001-python-packaging.md)の依存最小化方針）、新規ライブラリの追加は`CLAUDE.md`・`AGENTS.md`が定める「依存ライブラリの新規追加は着手前にユーザー確認」の対象である。標準ライブラリにはYAMLパーサーが存在しない。

## 決定

**`LayoutDefinition`のYAMLロード実装に`PyYAML`（PyPI: `PyYAML`）を採用する。** `pyproject.toml`の`dependencies`に`pyyaml>=6.0.0`を、`dev`依存に型スタブ`types-pyyaml`（PyYAML自体は`py.typed`マーカーを持たないため、`mypy --strict`適合に必要）を追加する。

選定理由:
- **事実上の標準**: PythonエコシステムでYAMLパーサーが必要な場面のほぼすべてで採用される、最も枯れた選択肢である（[ADR-0001](0001-python-packaging.md)の「枯れた技術を選ぶ」方針と直接合致）。
- **`knowledge/`の将来実装との共通化**: [`docs/knowledge/schema.md`](../knowledge/schema.md)が定めるknowledge/配下のYAMLロード（`KnowledgeService.load_snapshot()`、未実装）も同じくYAMLパーサーを必要とする。同一ライブラリを採用することで、依存の重複を避ける（[ADR-0001](0001-python-packaging.md)の依存最小化）。
- **セキュリティ**: `yaml.safe_load()`により、任意のPythonオブジェクト構築を許さない安全なロードが標準で提供される（`layouts/`・`knowledge/`はいずれもリポジトリ管理下のデータであり信頼境界の外ではないが、[ADR-0026](0026-security-policy.md)の防御的姿勢と整合させ`safe_load`を用いる）。

## 検討した代替案

- **`tomllib`（標準ライブラリ、TOML）を使い、`layouts/`の定義形式自体をTOMLに変更する**: `layouts/README.md`・`docs/knowledge/schema.md`が既にYAMLを前提として設計されており（`knowledge/schema.md`はJSON Schema Draft 2020-12でYAML文書を検証する設計）、今から形式を変更すると設計文書全体への影響が大きい。新規依存を避けるためだけに既存設計を変更するのは本末転倒と判断し見送った。
- **`ruamel.yaml`**: コメント保持等の高度な機能を持つが、`LayoutDefinition`のロード（読み取り専用）にはオーバースペックであり、`PyYAML`より重い依存となるため見送った。

## 結果（トレードオフ）

- `layout/`パッケージが`pyyaml`に依存する。[`docs/api/package-design.md`](../api/package-design.md)の`layout/`節が定める「依存先: `models/`, `utils/`のみ」という**自プロジェクト内パッケージ間**の依存禁止ルールには抵触しない（`pyyaml`は外部ライブラリ）。
- `yaml.YAMLError`系の例外は`layout/`パッケージ内で捕捉し、`LayoutDetectorError`に変換する（Task5禁止事項「ライブラリ例外を外へ漏らさない」、[ADR-0032](0032-redefine-document-analyzer-responsibility.md)・[ADR-0034](0034-pypdf-for-document-analyzer.md)と同一の例外設計方針）。
- 将来`knowledge/`のYAMLロードを実装する際、本ADRが定めた`pyyaml`をそのまま再利用できる（新規ADR不要、[ADR-0001](0001-python-packaging.md)の依存最小化に資する）。

## 関連ADR
- [ADR-0001](0001-python-packaging.md) — Pythonパッケージング・依存最小化方針。
- [ADR-0005](0005-knowledge-base-normalization.md) — Knowledge Base正規化。将来のYAMLロードとの関係。
- [ADR-0026](0026-security-policy.md) — セキュリティポリシー。`safe_load`採用の根拠。
- [ADR-0034](0034-pypdf-for-document-analyzer.md) — Document Analyzerの実装にpypdfを採用する。同種の実装着手時ライブラリ選定の先例。
- [ADR-0035](0035-layout-detector-owns-pdf-content-access.md) — Layout Detector Owns PDF Content Access。`LayoutDefinition`の利用元。
