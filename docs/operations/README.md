# docs/operations/（運用手順書 / Runbook）

## 責務

システムが実装され本番運用に入った後、日々の運用・障害対応・定型作業の手順を記録する場所。「動かし方」を人が変わっても再現できるようにする。

## 現状

設計フェーズのため、具体的な手順書はまだ存在しない。実装が進み次第、以下のような runbook を順次追加する想定。

- `pipeline_run.md`: パイプラインの定期実行・手動実行の手順
- `incident_response.md`: 抽出失敗・検証NG急増時の対応手順
- `new_layout_rollout.md`: 新しいPDF様式に対応する際の詳細手順（`CONTRIBUTING.md` の概要版を実務レベルに具体化したもの）
- `data_correction.md`: 公開後に誤りが判明した場合の訂正・再公開フロー

## 既存ドキュメント

- [`observability.md`](observability.md): Observability設計（Logging / Metrics / Tracing / Health Check / Alert / Dashboard / SLO / SLI / Error Budget / OpenTelemetry対応方針）。上記runbook群がまだ存在しない現時点でも、「何を観測し、何を異常とみなすか」の設計はここで先に固定する。
