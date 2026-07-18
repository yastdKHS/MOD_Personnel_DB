# Architecture Decision Records（ADR）

## これは何か

後から「なぜこの設計にしたのか」を問われたときに答えられるようにするための記録。10年以上保守するプロジェクトでは、コードやコミット履歴だけでは「なぜ」が失われる。ADRはそれを防ぐ。

## いつADRを書くか

- データモデルの決定・変更
- 技術選定（言語・ライブラリ・データストア・ビルドツール等）
- パイプラインの構造（ステージ分割、責務分担）
- 運用・公開ポリシー、データ倫理に関わる方針
- 既存ADRを覆す決定

小さなバグ修正や、既存方針の範囲内の実装詳細にはADRは不要。

## フォーマット

ファイル名: `NNNN-短い説明.md`（4桁連番、既存の最大値+1）

```markdown
# NNNN. タイトル

## ステータス
Proposed / Accepted / Superseded by ADR-XXXX / Deprecated

## コンテキスト
なぜこの決定が必要になったか。前提・制約。

## 決定
何を決定したか。

## 検討した代替案
他にどんな選択肢を検討し、なぜ採用しなかったか。

## 結果（トレードオフ）
この決定によって得られるもの・失うもの・将来への影響。
```

## 既存ADRを変更する場合

ADRは基本的に不変（immutable）として扱う。決定を覆す場合は、既存ADRのステータスを `Superseded by ADR-XXXX` に更新し、新しいADRを追加する。過去のADRを書き換えて履歴を消さない。

## 一覧

| # | タイトル | ステータス |
|---|---|---|
| [0001](0001-python-packaging.md) | Pythonパッケージング・ビルドバックエンドの選定 | Accepted |
| [0002](0002-lint-format-typecheck-tooling.md) | Lint / Format / 型チェックツールの選定 | Accepted |
| [0003](0003-layout-definition-strategy.md) | PDFレイアウトの外部データ定義化 | Accepted |
| [0004](0004-sqlite-as-datastore.md) | データストアとしてのSQLite採用 | Accepted |
| [0005](0005-knowledge-base-normalization.md) | ドメイン知識ベースによる名寄せ・正規化戦略 | Accepted |
| [0006](0006-pipeline-provenance.md) | パイプライン段階分割と来歴（Provenance）管理 | Accepted |
| [0007](0007-golden-file-testing.md) | ゴールデンファイルテスト戦略 | Accepted |
| [0008](0008-data-ethics-policy.md) | 個人情報・データ倫理方針 | Accepted |
| [0009](0009-ai-agent-operating-policy.md) | AIコーディングエージェント運用方針 | Accepted |
| [0010](0010-ci-cd-and-publish-strategy.md) | CI/CDと公開戦略 | Accepted |
| [0011](0011-fixed-core-pipeline.md) | 中核処理パイプラインの固定化 | Accepted（変更には高いハードル） |
| [0012](0012-error-handling-priority-order.md) | 未知パターンへの対応優先順位（Knowledge Base > Layout > 例外処理） | Accepted |
| [0013](0013-learning-dataset-not-correction-log.md) | 誤り修正情報をLearning Datasetとして設計する | Accepted |
| [0014](0014-development-discipline.md) | 開発規律（設計品質優先・1PR1責務・関数サイズ制限） | Accepted |
| [0015](0015-sqlite-schema-finalization.md) | SQLiteスキーマの確定 | Accepted |
