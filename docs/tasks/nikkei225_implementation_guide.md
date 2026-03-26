# Nikkei225_1d テーブル - 実装 Issue

## 何をしたいのか

yfinance から日経225インデックス（`^N225`）のデータを取得し、`NIKKEI225_1D` テーブルに保存するサービスを実装する。
バッチスクリプトから実行でき、`max_period` パラメータで取得期間を制御できる仕様。

**主な要件**:
- `NIKKEI225_1D` テーブルを Alembic で作成（timestamp をユニークキー）
- SQLAlchemy モデル、Pydantic スキーマ、リポジトリを実装
- Fetcher/Converter/Validator/Saver の4層サービスアーキテクチャ
- バッチスクリプト `batch_fetch_nikkei225.py` で `--max-period` オプション指定可能
- `scripts/batch/runner.py` に統合

---

## 何を参考とすればよいのか

### 実装パターンの参考

1. **Stock Price Service** - メインの参考実装
   - `app/services/data_synchronization/market_data/stock_price/` 配下の構造
   - Fetcher/Converter/Validator/Saver 各層の実装
   - `StockPriceService` のオーケストレーション方法

2. **リポジトリ実装** - UPSERT パターン
   - `app/repositories/market_data/stock_price/` の UPSERT ロジック
   - SQLite `INSERT ON CONFLICT DO UPDATE` の使用方法

3. **バッチスクリプト** - CLI 実装パターン
   - `scripts/batch/batch_fetch_stock_prices.py`
   - `--timeframe` オプション指定の例
   - TestClient で API 呼び出しする方法

4. **ER ダイアグラム** - テーブルスキーマ定義
   - `docs/architecture/diagrams/er.md` 内の `NIKKEI225_1D` 定義
   - `STOCKS_1D` との構造比較

5. **テスト ファイル** - 動作確認済みの実装
   - `work/test_nikkei225.py`: 期間指定ありの取得テスト
   - `work/test_nikkei225_max_period.py`: max_period テスト

---

## 何に注意すればよいのか

1. **ユニークキーの設計**
   - `timestamp` をユニークキーに設定（UPSERT 時の重複判定用）
   - `STOCKS_1D` の symbol 別管理と異なり、Nikkei225 は symbol 不要

2. **max_period パラメータの扱い**
   - `max_period=None` → `yf.download("^N225")` で全利用可能データ取得
   - `max_period=365` → 過去365日分を指定期間で取得
   - 0 または負の値の入力検証必須

3. **タイムゾーン処理**
   - yfinance 返データが UTC か JST か確認し、DB は `DateTime(timezone=True)` で正確に記録
   - `work/test_nikkei225_max_period.py` で確認済み

4. **yfinance API 制限**
   - バッチ実行時のレート制限対応（待機時間設定等）
   - ネットワークエラー時の例外処理（`YahooFinanceError` へマッピング）

5. **UPSERT と既存データの扱い**
   - 同じ timestamp の新規データは置き換える（UPDATE）
   - 既存データとの重複チェック時の パフォーマンス（インデックス活用）

6. **ログ出力**
   - Fetcher: 取得行数、期間情報
   - Validator: エラー件数、除外理由
   - Saver: UPSERT 成功数・失敗数

7. **pre-commit ことして通すべき検查**
   - lint (ruff), format (black), typecheck (mypy) が全て pass
   - 参考: `.github/skills/commit_regulation/SKILL.md`

---

## 補足

- **STOCK_PRICE Service との大きな違い**: 複数銘柄管理 vs. 単一インデックス管理
- **インデックス層の独立性**: NIKKEI225_1D は他テーブルと FK 関連を持たない独立テーブル（ER 図参照）
- **バッチの実行順序**: `runner.py` 内で `batch_fetch_stock_prices` の直後に実行予定
- どんな挙動をするのかを確かめたファイルは以下です。
    F:\TAKUMI\GitHub\STOCK-INVESTMENT-ANALYZER\work\test_nikkei225.py
    F:\TAKUMI\GitHub\STOCK-INVESTMENT-ANALYZER\work\test_nikkei225_max_period.py
