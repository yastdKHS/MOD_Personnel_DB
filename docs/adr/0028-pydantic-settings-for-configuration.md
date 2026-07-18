# 0028. 設定管理へのPydantic Settings採用

## ステータス
Accepted

## コンテキスト

[`docs/api/package-design.md`](../api/package-design.md#config)は`config/`パッケージの責務を「環境変数・設定ファイルの読み込みと、型付き設定オブジェクトへの変換」と定めているが、その型付き設定オブジェクトを何で実装するかは未決定だった。

一方、[`docs/api/python-contract.md`](../api/python-contract.md#pydantic利用可否)は、内部ドメインモデル（`models/`）についてPydanticを明示的に**不採用**と決定済みである（理由: 既に外部境界の検証手段として`jsonschema`を採用しており、Pydanticを追加すると2つの並行するバリデーション手段が生まれ、[ADR-0001](0001-python-packaging.md)の依存最小化方針に反するため）。

Configuration Architecture（`docs/configuration.md`）の設計にあたり、環境（dev/test/staging/production）ごとに異なる設定値を、型強制・必須項目の検証・秘匿値の誤出力防止を伴って安全に読み込む仕組みが必要になった。この決定を、既存のPydantic不採用決定と矛盾しない形で行う必要がある。

## 決定

- `config/`パッケージの型付き設定オブジェクト（`Settings`）の実装手段として、**Pydantic Settings（`pydantic-settings`）を採用する**。
- この採用は`config/`パッケージの境界に**限定**する。[`python-contract.md`](../api/python-contract.md#pydantic利用可否)が定める「内部ドメインモデル（`models/`）にはPydanticを採用しない」という決定は変更しない（Supersedeしない）。両者は扱う境界が異なる。
  - `models/`: パイプライン内部を流れる値オブジェクト（`jsonschema`が担う外部境界の検証とは別レイヤー）
  - `config/`: 環境変数・`.env`ファイルという**外部入力**の受け口（`jsonschema`がKnowledge YAML・公開JSONという別の外部境界を担うのと同じ位置づけ）
- Pydantic Settingsの`SecretStr`型を、FTP認証情報等の秘匿設定値の型として用いる。ログへの誤出力防止（[`docs/operations/observability.md`](../operations/observability.md#logging)のLogging方針）を型レベルで保証する目的であり、`models/`のバリデーション手段としての採用ではない。
- 依存関係（`pyproject.toml`）に`pydantic`・`pydantic-settings`を新規追加する。これは[ADR-0001](0001-python-packaging.md)の依存最小化方針への例外であり、その正当化は次節に述べる。

## 検討した代替案

- **標準ライブラリ（`dataclasses` + `os.environ`の手動パース）のみで設定を実装する**: 環境ごとの必須/任意項目の切り替え、型強制、`.env`ファイル読み込み、ネストした設定グループの表現を手作業で書くと、`models/`の単純なdataclassとは異なりコード量・保守負荷がむしろ増える。設定は「起動時に一度だけ検証すればよい外部入力の受け口」であり、Pydanticが最も強みを発揮する用途に合致するため、この局面に限り依存追加を正当化できると判断した。
- **`models/`も含めてPydanticへ全面移行する**: [`python-contract.md`](../api/python-contract.md#pydantic利用可否)の既存決定を覆すことになり、当初の懸念（jsonschemaとの二重バリデーション手段の共存）が再燃する。今回はその決定を維持したまま、`config/`という限定された境界にのみ適用範囲を絞った。
- **設定用に独自の軽量バリデータを自作する**: `jsonschema`をここでも流用する案も検討したが、`jsonschema`はJSON文書の検証を主眼としており、環境変数のような文字列キーバリューの型強制・ネスト構造への変換には不向き（変換後の型付きオブジェクトを得るには結局追加のマッピング層が必要になる）と判断し、採用しなかった。

## 結果（トレードオフ）

- `pydantic`が依存関係グラフに加わり、「依存最小化」という原則（[ADR-0001](0001-python-packaging.md)）に例外が生じる。将来「`models/`にもPydanticを採用すべきでは」という提案が出た場合に、本ADRの存在がその判断を不当に後押ししないよう、[`python-contract.md`](../api/python-contract.md#pydantic利用可否)側にも本ADRへの参照と適用範囲の限定を明記する。
- `config/`パッケージは引き続き`utils/`以外のいかなる自パッケージにも依存しない（[`dependency-rule.md`](../api/dependency-rule.md)）。Pydantic Settingsの採用は、この依存関係グラフ上の制約（内部パッケージ間の依存禁止）を変更しない。外部ライブラリへの依存は、この制約とは別軸の関心事である。
- 具体的なバージョン固定・脆弱性スキャンへの組み込みは、[ADR-0026](0026-security-policy.md)の依存ライブラリ脆弱性対応方針に従い、実装着手時に行う。
