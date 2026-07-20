# 0042. Python Version Target Realignment

## ステータス
Accepted

## コンテキスト（Context）

GitHub Actions CI（`lint-and-typecheck`・`test`ジョブ）が以下のエラーで恒常的に失敗する状態が発見された。

```
ERROR: Package 'mod-personnel-db' requires a different Python:
3.12.13 not in '>=3.14'
```

調査の結果、以下3箇所のPythonバージョン指定が相互に不整合であることが判明した。

| 箇所 | 指定 |
|---|---|
| `pyproject.toml`（`requires-python`, `[tool.mypy] python_version`） | `>=3.14` / `3.14` |
| `.github/workflows/ci.yml`（`actions/setup-python`、2ジョブとも） | `3.12` |
| ローカル開発環境（`poetry`管理の`.venv`実体） | `3.13.12`（`python3.14`バイナリはOS上に存在しない） |

`git log -p -- pyproject.toml`で追跡したところ、`>=3.12`から`>=3.14`への変更はPhase2 Task1「Repository Skeleton実装」のコミット（`dc1fdf2`）で行われていた。同コミットメッセージ自身が次のように明記している。

> Python 3.14を対象とする（pyproject.toml更新）。本サンドボックス環境はネットワークポリシーにより3.14バイナリを取得できないため、実際のテスト実行はuv管理のPython 3.13で行った（コードは3.14固有構文に依存しない）。

すなわち、3.14への引き上げは実装作業中の一コミットで行われた変更であり、（1）新規ADRを起票せず、（2）実際に3.14インタプリタで検証されたことはなく、（3）`.github/workflows/ci.yml`側は追随修正されないまま今日に至っていた。これは[`CLAUDE.md`](../../CLAUDE.md)が定める「依存ライブラリ・技術選定の変更は憶測で進めず確認する」という原則、および大きな設計変更は事前にADRを起票するという運用（[ADR-0009](0009-ai-agent-operating-policy.md)）から外れた状態だった。

[ADR-0030](0030-strenum-adoption.md)は`enum.StrEnum`採用の理由説明の中で「本プロジェクトはPython 3.14を対象とする」という記述を既成事実として引用しているが、これは3.14固有の言語機能を必須とする決定ではない（`enum.StrEnum`はPython 3.11以降で利用可能であり、コードベース全体を確認しても3.14専用構文への依存は存在しない）。

## 問題（Problem）

1. `pyproject.toml`が要求するPythonバージョン（`>=3.14`）と、GitHub Actionsが実際にインストールするバージョン（`3.12`）が一致せず、`pip install -e ".[dev]"`が即座に失敗する。
2. ローカル開発環境（`.venv`実体は3.13.12）も`>=3.14`を満たしておらず、`poetry run`経由のコマンド実行が阻害される（本セッションでは`.venv/bin/mypy`等への直接呼び出しで回避してきたが、正規の`poetry run`ワークフローが機能しない状態が常態化していた）。
3. 3.14への引き上げ自体が、ADRを経ない一コミットでの変更であり、実地検証もされていない。

## 決定（Decision）

`requires-python`・mypy対象・GitHub Actionsの3箇所すべてを、**Python 3.13**に統一する。

```toml
# pyproject.toml
requires-python = ">=3.13"

[tool.mypy]
python_version = "3.13"
```

```yaml
# .github/workflows/ci.yml（2ジョブとも）
python-version: "3.13"
```

3.13を選定する理由:

- Task1以降、`mypy --strict`・`ruff`・`pytest`によるすべての実装検証が、実際には（`poetry`のPythonバージョンチェックを回避しつつ）Python 3.13の`.venv`で行われてきた。3.13は「名目上の目標」ではなく「実際に検証されてきたバージョン」である。
- コードベースに3.13以降でなければ動作しない構文・API依存は存在しない（`enum.StrEnum`は3.11+、`X | Y`合併型・`slots=True`データクラス等は3.10+で利用可能）。
- GitHub Actionsのホストランナーで確実に取得できる。
- 3.14へCI側を合わせる代替案（後述）は、3.14バイナリを配布しない開発・CIサンドボックス環境を今後も塞ぎ続けるリスクを残す。

## 検討した代替案

- **CIの`python-version`を`3.14`に引き上げ、`pyproject.toml`の`>=3.14`要求に合わせる**: GitHub Actionsのホストランナーでは取得できる可能性が高い一方、（1）3.14は一度も実地検証されておらずコード互換性が未確認、（2）3.14バイナリを取得できないネットワーク制限下のローカル・サンドボックス開発環境（本プロジェクトの過去のセッションで実際に発生した制約）を今後も継続して塞ぐ、という2点のリスクが残るため採用しなかった。10年以上の保守を前提とする本プロジェクトの方針（[`CLAUDE.md`](../../CLAUDE.md)）に照らし、「実際に検証されてきたバージョンに環境側を合わせる」方をより保守的な選択とした。
- **`>=3.12`（Task1以前の値）に戻す**: CIの現在の指定（3.12）とは一致するが、ローカル開発環境の実体（3.13）とは一致しないままであり、根本的な不整合解消にはならないため採用しなかった。

## 結果（トレードオフ, Consequences）

- CIが正常に`pip install -e ".[dev]"`できるようになり、報告されていた失敗が解消される。
- ローカル開発環境で`poetry run mypy`等の正規ワークフローが、バージョンチェックのバイパスなしに機能するようになる。
- [ADR-0030](0030-strenum-adoption.md)自体の決定（`enum.StrEnum`採用）は変更しない。同ADRが引用する「対象Pythonバージョン」という文脈情報のみが3.14→3.13に更新される（Supersededにはしない）。
- 将来、実際に3.14（またはそれ以降）へ移行する場合は、対象インタプリタでの実地検証を伴う形で改めて新規ADRを起票する。

## Migration

1. `pyproject.toml`の`requires-python`・`[tool.mypy] python_version`・`classifiers`を`3.13`に更新する（同一PR）。
2. `.github/workflows/ci.yml`の2箇所の`python-version`を`"3.13"`に更新する（同一PR）。
3. `docs/api/python-contract.md`のADR-0030に関する記述中の「Python 3.14」を「Python 3.13」に更新する（同一PR）。

## Affected Documents

| ドキュメント | 変更内容 |
|---|---|
| [`pyproject.toml`](../../pyproject.toml) | `requires-python`・`python_version`・`classifiers`を3.13に統一 |
| [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | `python-version`を3.13に統一 |
| [`docs/api/python-contract.md`](../api/python-contract.md) | ADR-0030引用部分の対象Pythonバージョン記述を更新 |

## 関連ADR
- [ADR-0001](0001-python-packaging.md) — Pythonパッケージング・ビルドバックエンドの選定。`pyproject.toml`を設定の唯一の情報源とする方針の前提。
- [ADR-0002](0002-lint-format-typecheck-tooling.md) — Lint/Format/型チェックツールの選定。`mypy`設定の前提。
- [ADR-0009](0009-ai-agent-operating-policy.md) — AIエージェント運用方針。技術選定変更時のADR起票原則の根拠。
- [ADR-0010](0010-ci-cd-and-publish-strategy.md) — CI/CD・公開戦略。本ADRが修正する`.github/workflows/ci.yml`の設計方針の前提。
- [ADR-0030](0030-strenum-adoption.md) — `enum.StrEnum`採用。「対象Pythonバージョン」という文脈情報を本ADRが更新する引用元。

（本ADRはADR-0001/0002/0009/0010/0030のいずれの核心決定も変更しないため、Supersededにはしない。）
