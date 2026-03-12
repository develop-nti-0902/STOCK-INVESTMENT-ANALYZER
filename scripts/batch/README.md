# scripts/batch

このディレクトリは日次／バッチ処理用のスクリプトを格納します。簡易説明と実行コマンド例を示します。

概要
- `runner.py` : デフォルトで登録されたバッチジョブを順次実行するランナー（`python -m scripts.batch.runner`）。ジョブ別のログを `log/` 配下に出力します（毎回上書き、先頭に実行時刻を出力）。

主要スクリプト（簡易説明）
- `batch_fetch_stock_master.py` : `/api/v1/stock-master/fetch` を TestClient 経由で呼び出して銘柄マスタを更新します。`--sample` オプションあり。
- `batch_fetch_stock_prices.py` : 全銘柄の株価を一定期間分取得して保存するバッチ。`--days`/`--timeframe`/`--batch-size` オプションあり。
- `batch_fetch_edinet_data.py` : EDINET データを取得するバッチ（`--start-date`/`--end-date` が必須）。ランナーは既定で前日を指定して呼び出します。
- `batch_run_screening.py` : スクリーニング処理を実行するバッチ（ScreeningService を使用）。
- `batch_dividend_yield_monitoring.py` / `batch_dividend_yield_history.py` : 配当利回り関連の監視・履歴処理バッチ。

- `initial_only_update_stock_master_and_prices.py` : プロジェクトの初回セットアップ時にのみ実行することを意図したスクリプト。銘柄マスタを全取得して保存し、全銘柄の `1d` 株価を取得してDBに保存します（大規模処理のため通常運用では実行しないでください）。

ログ
- ジョブ実行ログは `log/` 配下に `scripts_batch_<module>.log` の形式で出力されます（ランナー経由で実行した場合）。

実行例（リポジトリルートで実行）
```powershell
poetry run python -m scripts.batch.runner
poetry run python -m scripts.batch.runner --dry-run
poetry run python -m scripts.batch.runner --continue-on-error

# 単体ジョブを直接実行
poetry run python -m scripts.batch.batch_fetch_stock_master
poetry run python -m scripts.batch.batch_fetch_stock_master --sample --sample-size 100 --batch-size 500
poetry run python -m scripts.batch.batch_fetch_stock_prices --days 30
poetry run python -m scripts.batch.batch_fetch_edinet_data --start-date 2025-06-24 --end-date 2025-06-24
# 初回セットアップ専用スクリプトの実行例（注意: 基本1回だけ実行）
poetry run python -m scripts.batch.initial_only_update_stock_master_and_prices --timeframe 1d --batch-size 500
```

スケジューラへの登録（例）
- Windows タスクスケジューラで PowerShell を実行する場合、アクションに次を指定します。
```powershell
cd "F:\TAKUMI\GitHub\STOCK-INVESTMENT-ANALYZER"
poetry run python -m scripts.batch.runner
```

運用上の注意（短く）
- バッチは冪等性を意識してください（再実行で重複登録しないこと）。
- 長時間処理や大データ投入は `--continue-on-error` を慎重に使ってください。
- 必要ならログローテーションや監視（失敗時通知）を追加してください。
