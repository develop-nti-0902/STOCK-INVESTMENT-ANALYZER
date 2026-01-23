# バッチジョブ管理 — 設計と運用手順

最終更新: 2026-01-23

このドキュメントは、プロジェクトにおけるバッチ実行のジョブ管理設計と運用手順をまとめたもの。主に `jpx_all/multi` 系バッチの運用を想定しています。

## 目的
- ジョブライフサイクルと `batch_execution_details` の扱いを明確化する
- バッチ再実行、進捗管理、ログ保持／削除ポリシーを運用担当者へ提示する

## ジョブライフサイクル

1. init: ジョブ（バッチ実行）を初期化する。`batch_executions` レコードを作成し、関連する `batch_execution_details` を初期化する。
2. inc / create detail: 実行対象ごとに `batch_execution_details` を生成し、ステータスを `queued` に設定する。
3. set_status: 実行中は `in_progress`、成功で `completed`、失敗で `failed` を設定する。
4. get_progress: `batch_execution` と `batch_execution_details` を集約して進捗率を算出する。

運用上は、ジョブ起動 → 対象分割（details生成）→ ワーカー実行 → 結果反映（set_status）という流れになります。

## `batch_execution_details` のスキーマと更新ポリシー

- 参照実装ファイル: [app/models/batch_execution_details.py](../../app/models/batch_execution_details.py)
- リポジトリ実装: [app/repositories/batch_execution_details_repository.py](../../app/repositories/batch_execution_details_repository.py)

主要フィールド（要約）:
- `id` : 主キー
- `batch_execution_id` : 親バッチ実行への外部キー
- `stock_code` : 対象識別子（例: 銘柄コード）
- `interval` : 集計間隔や処理対象の粒度
- `status` : `queued` / `in_progress` / `completed` / `failed`
- `progress` : 任意で進捗数値を保持

更新ポリシー:
- **頻度**: ワーカーは状態変更（`status` / `progress` / `error_message` 等）を逐次更新する。大量更新時はバッチ単位でまとめて更新すること。
- **集計戦略**: 進捗表示用は `batch_execution_id` ごとに `COUNT` や `SUM` を用いて集約する。DB負荷が問題となる場合は、キャッシュ層（Redis等）を導入することを検討する。

## バッチの再実行手順

1. 失敗箇所の `batch_execution_details` を `failed` から `queued` に戻す（再試行回数ポリシーに従う）。
2. 必要であれば同一 `batch_execution` をクローンして新しい `batch_execution` レコードを作り、再実行履歴を保持する。
3. 再実行時は `set_status` ロジックが二重実行にならないようロック（DBの行ロックや分散ロック）を検討する。

実装上の参考箇所:
- テーブル定義 SQL: [scripts/databaseSetup/sql/create_management_tables.sql](../../scripts/databaseSetup/sql/create_management_tables.sql)
- テスト: [tests/unit/models/test_batch_execution_details.py](../../tests/unit/models/test_batch_execution_details.py)

## 保持期間削除（cleanup）

- 運用上の要件に応じて、`batch_execution` / `batch_execution_details` の古い履歴を削除する。保持期間は運用ポリシー（例: 90日）で決定する。
- 推奨スクリプト配置: `scripts/cleanup_batch_history.py`（現状は未作成。`scripts/databaseSetup/sql/create_management_tables.sql` を参照して適切なDELETEクエリを実装してください）。

削除方針（例）:
- 1) 古い `batch_execution`（完了済み、かつ `completed_at` が閾値より古い）をターゲットにする
- 2) 関連する `batch_execution_details` を削除 / アーカイブ
- 3) 必要に応じてログや集計テーブルも掃除する

## 運用上の注意点

- 再実行ポリシー（何回再試行するか、指数バックオフの有無）を明文化すること
- 大量アクセス時のDB負荷に注意し、可能ならば状態更新をまとめる設計を採ること
- 監視（Prometheus/Grafana等）で `failed` 件数や再実行率を監視すること

## 参照とリンク
- モデル: [app/models/batch_execution_details.py](../../app/models/batch_execution_details.py)
- リポジトリ: [app/repositories/batch_execution_details_repository.py](../../app/repositories/batch_execution_details_repository.py)
- SQL: [scripts/databaseSetup/sql/create_management_tables.sql](../../scripts/databaseSetup/sql/create_management_tables.sql)
- 関連テスト: [tests/unit/repositories/test_batch_execution_details_repository.py](../../tests/unit/repositories/test_batch_execution_details_repository.py)

---

このドキュメントはIssue #243 の実装（ドキュメント追加）を目的として作成しました。レビュー後に `docs/README.md` の目次へリンクを追加します。
