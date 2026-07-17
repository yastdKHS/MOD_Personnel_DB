# CONTRIBUTING.md

本プロジェクトへの貢献方法について説明します。長期運用プロジェクトであるため、短期的な速度より「後から読める・直せる」ことを重視します。

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

## コーディング規約

- Lint / フォーマット: `ruff`（設定は `pyproject.toml`）
- 型チェック: `mypy`。新規コードには型ヒントを付与する。
- テスト: `pytest`。新機能には対応するテストを追加する。パーサー関連の変更には可能な限りゴールデンファイルテスト（`tests/golden`）を追加する。
- 詳細な設計原則は [`docs/architecture.md`](docs/architecture.md) を参照。

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
