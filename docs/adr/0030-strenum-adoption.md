# 0030. Enum実装方針をenum.StrEnumに統一する

## ステータス
Accepted

## コンテキスト

[`docs/api/python-contract.md`](../api/python-contract.md#enum利用方針)は、文字列としてシリアライズされる必要があるEnumの実装方針として「`str, Enum`の多重継承」を指定しており、[`docs/api/models.md`](../api/models.md)の`LearningStatus`がその具体例として明記されていた。

Phase2 Task2（Domain Model Implementation）でこの方針に従い`ConfidenceBand` / `PipelineStageName`（当時は`PipelineStage`という名称） / `ErrorCategory` / `RegressionStatus` / `LearningStatus`を`str, Enum`の多重継承として実装したところ、以下2つの機械的な摩擦が判明した（[Phase2 Task1](0028-pydantic-settings-for-configuration.md)でPython 3.14を対象バージョンとした`pyproject.toml`の設定と組み合わさって顕在化した）。

1. `ruff`（[ADR-0002](0002-lint-format-typecheck-tooling.md)）の`UP042`ルールが、`str, Enum`の多重継承のたびに`enum.StrEnum`への置き換えを推奨するエラーを出す。`pyproject.toml`の対象Pythonバージョンが3.14（`enum.StrEnum`はPython 3.11で導入済み）であるため、この指摘は正当であり、`# noqa`による抑制を重ねる以外に回避手段がない。
2. `mypy --strict`が、`str, Enum`のメンバーと文字列リテラルを比較するコード（例: テストコードでの`ConfidenceBand.HIGH == "high"`）に対して`comparison-overlap`警告を出す。`enum.StrEnum`はこの種の比較に対してmypyが特別扱いを行うため、警告が生じない。

`docs/api/python-contract.md`の方針を字面どおり守ると、実装のたびに`ruff`の警告を`noqa`で抑制し続けることになり、[ADR-0014](0014-development-discipline.md)が求める「機械的に検出できる問題を放置しない」規律に反する状態が常態化する。

## 決定

- 本プロジェクトのEnum実装は**`enum.StrEnum`に統一する**。新規に文字列としてシリアライズされる必要があるEnumは、`str, Enum`の多重継承ではなく`enum.StrEnum`を継承して実装する。
- 既存の`ConfidenceBand`, `PipelineStageName`, `ErrorCategory`, `RegressionStatus`, `LearningStatus`（`src/mod_personnel_db/models/enums.py`）を`enum.StrEnum`に置き換える。
- [`docs/api/python-contract.md`](../api/python-contract.md#enum利用方針)・[`docs/api/models.md`](../api/models.md)の該当箇所を本ADRと同期して更新する（同一PR、[ADR-0014](0014-development-discipline.md)の1PR1責務の例外として「同じ決定の二重表現の同期」は1つの責務とみなす）。
- `enum.StrEnum`のメンバーは`str`のサブクラスであり、シリアライズ・SQL文字列パラメータへのバインド・文字列との等価比較のいずれについても`str, Enum`の多重継承と実行時の互換性を持つ。既存の`repositories/sqlite/`実装（Confidenceは未参照、他のEnumは今回変更対象外）への影響はない（「結果（トレードオフ）」節を参照）。

## 検討した代替案

- **`str, Enum`の多重継承を維持し、`ruff`側で`UP042`を無効化する**: `pyproject.toml`の`[tool.ruff.lint] ignore`に追加すれば警告は消えるが、`UP042`はこのプロジェクトが対象とするPython 3.14において`enum.StrEnum`という明確に優れた選択肢がある場合にのみ発火する妥当な指摘であり、ルール自体を無効化するとPython 3.14を前提とする他の有用な`pyupgrade`指摘も見落とすリスクが増す。個別の`noqa`を積み重ねる案・ルール全体を無効化する案のいずれも、[ADR-0014](0014-development-discipline.md)の開発規律の精神に反すると判断し、両方とも見送った。
- **`str, Enum`の多重継承のまま、mypyの`comparison-overlap`のみ個別に抑制する**: `ruff`側の摩擦（1点目）が解消されないため、根本的な解決にならない。

## 結果（トレードオフ）

- `enum.StrEnum`はPython 3.11以降でのみ利用可能である。本プロジェクトは既にPython 3.14を対象（[`pyproject.toml`](../../pyproject.toml)）としているため、この制約は実質的な影響を持たない。
- 既存の`ConfidenceBand`等5つのEnumの変更は、いずれもDB（`repositories/sqlite/`）から直接読み書きされていない、またはモデル層に閉じた値であるため、Repository実装の変更を伴わない（詳細は[`docs/api/python-contract.md`](../api/python-contract.md#enum利用方針)の「既存のRepository実装との関係」を参照）。`KnowledgeItem.category`等、Repository実装が既に生の`str`として直接読み書きしているフィールドは、本ADRの対象外（`Literal`のまま据え置き）であり、将来Enum化する場合は対応するRepositoryの変更を同一PRで行うことを[`docs/api/python-contract.md`](../api/python-contract.md#enum利用方針)に明記した。
- `PipelineStageName`という命名変更（旧`PipelineStage`）は、本ADRとは独立した理由（[`docs/api/pipeline.md`](../api/pipeline.md)が定義するStage実装用Protocol`PipelineStage`との名前衝突の回避、Phase2 Task3で発見）によるものであり、本ADRはEnum実装方式（`str, Enum` → `StrEnum`）のみを決定する。
