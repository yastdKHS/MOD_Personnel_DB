# 0021. レビュー用インターフェース（Review UI）戦略

## ステータス
Accepted

## コンテキスト

`docs/database/schema.md`の`review_sessions`/`review_changes`テーブルは、人手レビューの**記録先**を定義しているが、レビュー担当者が実際に検証NGの一覧を確認し、値を確定するための**インターフェース**（CLI、Webアプリ、その他）は決定されていなかった（[Gap Analysis](gap-analysis.md#review-ui)参照）。[AGENTS.md](../../AGENTS.md)が前提とする「10年運用・複数担当者の交代」を踏まえると、この作業ツールが属人化しない形で設計されている必要がある。

## 決定

- 初期段階では、専用のWebアプリケーションを新規開発せず、`src/mod_personnel_db/cli/`（[ADR-0001](0001-python-packaging.md)のパッケージ構成）が提供するCLIツールで対応する。
- CLIツールは、`candidate_records`（`validation_status='failed'`）および`learning_dataset`（`status IN ('open', 'in_review')`、[ADR-0017](0017-learning-dataset-field-expansion.md)）を一覧表示し、レビュー担当者の入力に応じて`review_changes`・`learning_dataset`を更新する。
- レビューのロジック（検証NGの抽出、確定処理）は、CLIから直接呼び出す形ではなく、`src/`内の再利用可能なAPIとして実装する。将来Web UIへ移行する際に、ロジックを再実装せずインターフェース層のみ差し替えられるようにするため。
- 将来、以下のいずれかの条件に該当した場合、Webベースのレビュー画面導入を新規ADRとして検討する。
  - レビュー待ち件数（`learning_dataset`の`open`/`in_review`）が定常的に閾値を超える
  - プログラミング経験のない担当者がレビュー作業に加わる

## 検討した代替案

- **最初からWebアプリケーションを構築する**: 初期の開発・保守コストが高く、需要（レビュー作業量、担当者の技術レベル）が不明な段階での投資として過大と判断した。
- **スプレッドシート連携（CSVエクスポート→手動編集→再取込）**: 参照整合性（外部キー）や監査証跡（誰が・いつ変更したか）を手作業で維持することになり、誤りの温床になりやすい。CLIによる直接的なDB操作の方が安全と判断した。

## 結果（トレードオフ）

- CLI操作に不慣れな担当者には学習コストが生じる。
- レビューロジックを`src/`のAPIとして分離しておくことで、将来Web UIへ移行する際の手戻りを最小化する。
