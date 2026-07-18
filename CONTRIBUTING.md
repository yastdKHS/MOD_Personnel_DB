# CONTRIBUTING.md

本プロジェクトへの貢献方法について説明します。長期運用プロジェクトであるため、短期的な速度より「後から読める・直せる」ことを重視します。**実装速度より設計品質を優先し、既存の設計を壊す変更は行いません**（[ADR-0014](docs/adr/0014-development-discipline.md)）。

## 開発環境セットアップ（実装開始後に有効化）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

- Python バージョン、依存関係の唯一の情報源は `pyproject.toml` です。
- `pre-commit install` を必ず実行してください。CIと同じチェックがローカルのコミット時に走ります。

## ブランチ戦略

- デフォルトブランチ（`main`）は常にデプロイ可能な状態を保つ。
- 作業は `feature/<短い説明>`、修正は `fix/<短い説明>`、レイアウト追加は `layout/<年度・様式名>` のブランチ名を使う。
- `main` への直接pushは行わず、Pull Requestを経由する。

## コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) に準拠します。

```
<type>(<scope>): <概要>

<必要であれば詳細説明>
```

- `type`: `feat` / `fix` / `docs` / `refactor` / `test` / `chore` / `layout`（新規PDFレイアウト対応）/ `knowledge`（ドメイン知識データの更新）
- 例: `layout(2021-format-b): 2021年10月以降の新様式レイアウト定義を追加`

## Pull Request プロセス

1. `.github/PULL_REQUEST_TEMPLATE.md` に従って記述する。
2. 関連するADR（あれば）へのリンクを含める。
3. `CODEOWNERS` に基づくレビュー担当者の承認を得る。
4. CI（lint / 型チェック / テスト）がグリーンであることを確認する。
5. データモデル・レイアウトフォーマット・ドメイン知識のスキーマに影響する変更は、最低1名の追加レビューを必須とする。
6. **1つのPRは1つの責務のみを変更する**（[ADR-0014](docs/adr/0014-development-discipline.md)）。例: 「新しいLayoutの追加」と「無関係なリファクタリング」を同じPRに含めない。レビュー中に無関係な変更が見つかった場合は別PRに切り出す。

## コーディング規約

- Lint / フォーマット: `ruff`（設定は `pyproject.toml`）
- 型チェック: `mypy`。新規コードには型ヒントを付与する。
- テスト: `pytest`。新機能には対応するテストを追加する。パーサー関連の変更には可能な限りゴールデンファイルテスト（`tests/golden`）を追加する。
- **大きな関数を作らない**。目安は1関数あたり最大30文・最大分岐数8・最大循環的複雑度8・最大引数5。`pyproject.toml` のruff設定（`C90`, `PLR09xx`）で機械的に検出する。閾値内でも複数責務を持つ関数は分割する（[ADR-0014](docs/adr/0014-development-discipline.md)）。
- 詳細な設計原則は [`docs/architecture.md`](docs/architecture.md) を参照。

## 未知パターンへの対応優先順位

パース・正規化で「既存ロジックでは扱えないパターン」に遭遇した場合、対応の優先順位は以下の通りとする（[ADR-0012](docs/adr/0012-error-handling-priority-order.md)）。

1. `knowledge/` へのデータ追加（表記ゆれ・別名・改称履歴等）— 正規表現の追加より常に優先する
2. `layouts/` へのレイアウト定義追加（様式・構造の差異）— `src/` の例外処理より常に優先する
3. `src/` 内の例外処理・正規表現による特殊対応 — 最後の手段。追加する場合は、なぜ上記2つで表現できなかったかをコードコメントとPR説明に明記する

中核処理パイプライン（Document Analyzer → Layout Detector → Section Parser → Field Extractor → Normalizer → Validator）は[固定](docs/adr/0011-fixed-core-pipeline.md)されており、この段階構成自体を変更する提案は、ADR追加だけでなくプロジェクトオーナーの明示的な承認を要する。

## 誤りの修正記録（Learning Dataset）

Validatorでの検証NGや、公開後に判明した誤りは、単なる修正ログ（いつ・誰が・何を直したか）ではなく、`knowledge/learning_dataset/` にLearning Datasetとして記録する。誤りの分類・発生した中核パイプライン段階・`knowledge/`/`layouts/`への反映有無を含める（[ADR-0013](docs/adr/0013-learning-dataset-not-correction-log.md)）。

## 新しいPDFレイアウトへの対応手順（概要）

防衛省の発令PDFは様式が変わることがあります。新様式を見つけた場合の大まかな流れです（詳細は `docs/operations/` に整備予定）。

1. `.github/ISSUE_TEMPLATE/pdf_format_change.md` でIssueを起票する。
2. 代表的なサンプルを `sample_pdfs/` に、命名規則に従って追加する。
3. `layouts/` に新しいレイアウト定義を追加する（既存コードの改変は最小限に留める）。
4. 期待される抽出結果を `sample_outputs/` に追加し、ゴールデンファイルテストを通す。
5. 影響するドメイン知識があれば `knowledge/` を更新する。

## ドメイン知識（`knowledge/`）の更新

`knowledge/` は人手でレビューされるべき正データベースです。自動生成・一括置換ではなく、差分が説明可能な単位でPRを作成してください。変更理由（出典・根拠）をPR説明に明記してください。

## Architecture Decision Record（ADR）

データモデル・技術選定・パイプライン構成など、後から「なぜそうしたか」が問われる決定は `docs/adr/` にADRとして記録してください。テンプレートは `docs/adr/README.md` にあります。

## 質問・相談

設計判断に迷う場合は、実装を進める前にIssueまたはPRのドラフトで相談してください。
