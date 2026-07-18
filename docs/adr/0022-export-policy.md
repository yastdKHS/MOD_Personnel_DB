# 0022. エクスポート運用方針（Export Policy）

## ステータス
Accepted

## コンテキスト

[ADR-0010](0010-ci-cd-and-publish-strategy.md)は公開（Publish）フロー全体のガバナンス（人手ゲート、forward-only）を、[ADR-0016](0016-public-json-format.md)はJSON形式の詳細契約を定めている。しかし`exports.format`（`docs/database/schema.md`）は`csv` / `parquet` / `json`の3形式を許容する一方、CSV・Parquetの形式仕様・スキーマバージョニングはJSONほどの厳密さで定義されておらず、また公開の頻度（cadence）や過去エクスポートの提供期間といった運用面の方針も決定されていなかった（[Gap Analysis](gap-analysis.md#export-policy)参照）。

## 決定

- **エクスポート頻度**: 新しい発令PDFが取得・検証・確定するたびにエクスポートを再生成する（イベント駆動）ことを基本とし、加えて更新がない場合でも最低月次で強制的に再生成する（鮮度確認のため）。
- **CSV/Parquet形式**: [ADR-0016](0016-public-json-format.md)で定義したJSON形式の`PersonnelRecord`をフラット化した列構成とする。ネストされた`provenance` / `confidence`は、プレフィックス付き列名（例: `provenance_source_pdf_content_hash`）で表現する。CSV/Parquet専用の独自スキーマ検証言語は導入せず、検証済みのJSON形式からの機械的な変換によって整合性を担保する（変換ロジック自体はテスト対象とする）。
- **提供期間**: `exports`テーブル（永久保持、[ADR-0015](0015-sqlite-schema-finalization.md)）に基づき、少なくとも直近の全エクスポートへのアクセスを提供する。古いエクスポートのアーカイブ化・提供終了を行う場合は、影響が大きい変更として別途検討する。

## 検討した代替案

- **CSV/Parquetに対してもJSON Schema同等の厳密な独自スキーマ言語を定義する**: 3形式分の検証ロジックを個別に保守するコストが高く、[ADR-0001](0001-python-packaging.md)の「依存を最小限に保つ」方針に反する。JSON側の検証を正とし、そこからの機械的変換で品質を担保する方針とした。

## 結果（トレードオフ）

- CSV/Parquetの品質は、JSON生成ロジックおよび変換ロジックの正しさに依存する構造になる。変換ロジックのテスト（ゴールデンファイル的な検証、[ADR-0007](0007-golden-file-testing.md)の精神を変換処理にも適用）を実装時に必須とする。
- イベント駆動のエクスポート再生成は、発令PDFの公表頻度が急増した場合に処理負荷が増える可能性があり、その場合はレート制限（最小間隔の設定）を追加で検討する。
