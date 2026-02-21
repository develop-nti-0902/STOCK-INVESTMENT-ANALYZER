# 配当利回り監視システム 設計書

## 1. システム概要

### 1.1 目的

高配当株スクリーニングシステムで絞り込まれた監視対象銘柄（`watch` / `active` / `priority`）について、最新の株価データから配当利回りを算出し、購入タイミングを判断するための情報を提供する。

### 1.2 配当利回りの定義

```
配当利回り (%) = (年間配当金 / 現在株価) × 100
```

- **年間配当金**: `edinet_stock_dividend.dividend_actual` の最新値を使用
- **現在株価**: `stocks_1d.close` の最新値を使用

### 1.3 処理フロー

```mermaid
graph LR
    A[screening_results<br/>監視対象銘柄抽出] --> B[DividendYieldMonitoringService<br/>配当・株価データ取得]
    B --> C[配当利回り計算]
    C --> D[ターミナル出力<br/>購入判断レベル付]
```

1. **監視対象抽出**: `ScreeningResultRepository` から `status` が `watch`/`active`/`priority` の銘柄を取得
2. **データ取得**: 各銘柄の最新配当金（EDINET）と最新株価（Yahoo Finance）を取得
3. **配当利回り計算**: 配当金 ÷ 株価 × 100
4. **ターミナル出力**: 銘柄コード、配当利回り、購入判断レベルを表示

---

## 2. ファイル構成

### 2.1 サービス層ディレクトリ構成

**今回追加するファイルは1ファイルのみ。** その他の既存コードは変更しない。

```
app/services/
    integration/           # 外部API・DB保存（既存）
        stock_master/
        stock_price/
        edinet/
    query/                 # DB取得・整形（既存）
        financial_query_service.py
    screening/             # スクリーニング（既存）
        simple_screening_service.py
    monitoring/            # 監視系サービス（新規作成）
        dividend_yield_monitoring_service.py    新規作成
```

### 2.2 スクリプト

```
scripts/
    run_dividend_yield_monitoring.py    新規作成
```

### 2.3 既存コードの活用（新規作成不要）

| カテゴリ           | 既存ファイル / クラス           |
| ------------------ | ------------------------------- |
| スクリーニング結果 | `ScreeningResultRepository`     |
| 配当データ         | `EdinetStockDividendRepository` |
| 株価データ（日足） | `StockData1dRepository`         |
| 銘柄コード変換     | `utils.stock_code_converter`    |

### 2.4 後工程（本ドキュメントのスコープ外）

- `DividendYieldMonitoring` モデル / リポジトリ（DB保存）
- APIエンドポイント (`app/api/v1/monitoring.py`)
- 定期バッチスクリプト（日次実行）
- フロントエンド画面（配当利回り推移グラフ）

---

## 3. データモデル設計

### 3.1 既存テーブル（参照のみ）

| テーブル名              | 内容               | 参照カラム                                       |
| ----------------------- | ------------------ | ------------------------------------------------ |
| `screening_results`     | スクリーニング結果 | `sec_code`, `status`, `evaluation_date`          |
| `edinet_stock_dividend` | 年間配当金実績     | `sec_code`, `dividend_actual`, `period_end_date` |
| `stocks_1d`             | 日足株価データ     | `symbol`, `close`, `timestamp`                   |

### 3.2 新規テーブル: `dividend_yield_monitoring`（Phase 2以降で作成予定）

> **現時点では作成不要。** Phase 2以降でDB保存・API・履歴管理が必要になった際に合わせて作成する。

| カラム名                | 型          | NULL | 説明                                              |
| ----------------------- | ----------- | ---- | ------------------------------------------------- |
| id                      | INTEGER     | NO   | 主キー                                            |
| sec_code                | VARCHAR(10) | NO   | 証券コード                                        |
| monitoring_date         | DATE        | NO   | 監視実施日                                        |
| latest_dividend_amount  | NUMERIC     | NULL | 直近年間配当金（円）                              |
| latest_stock_price      | NUMERIC     | NULL | 直近株価（終値、円）                              |
| dividend_yield          | NUMERIC     | NULL | 配当利回り（%）                                   |
| purchase_level          | VARCHAR(20) | NULL | `watch` / `consider` / `priority` / `unavailable` |
| screening_status        | VARCHAR(20) | NULL | スクリーニングステータス（参考情報）              |
| screening_total_score   | INTEGER     | NULL | スクリーニング総合スコア（参考情報）              |
| stock_price_source_date | DATE        | NULL | 株価データの取得日                                |
| dividend_source_date    | DATE        | NULL | 配当データの決算期末日                            |
| created_at              | TIMESTAMP   | NO   | 作成日時                                          |
| updated_at              | TIMESTAMP   | NO   | 更新日時                                          |

**ユニーク制約**: `(sec_code, monitoring_date)`

**インデックス**:
- `idx_dividend_yield_monitoring_date` (`monitoring_date`)
- `idx_dividend_yield_purchasing_level` (`purchase_level`)
- `idx_dividend_yield_monitoring_yield` (`dividend_yield`)

---

## 4. サービス層設計

### 4.1 `DividendYieldMonitoringService`（`monitoring/dividend_yield_monitoring_service.py`）

**責務**: 監視対象銘柄の配当利回りを計算し、購入判断レベルを付与してターミナルに出力する。**Phase 1ではDB保存なし。**

**依存リポジトリ**:
- `ScreeningResultRepository`
- `EdinetStockDividendRepository`
- `StockData1dRepository`

**内部データクラス**:

| クラス名                        | フィールド                                                                                                                                                                                                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `DividendYieldMonitoringResult` | `sec_code: str`, `dividend_amount: Optional[Decimal]`, `stock_price: Optional[Decimal]`, `dividend_yield: Optional[Decimal]`, `purchase_level: str`, `screening_status: str`, `screening_score: int`, `stock_price_date: Optional[date]`, `dividend_fiscal_year_end: Optional[date]` |

**公開メソッド**:

| メソッド              | 引数                                     | 戻り値                          | 説明                                                       |
| --------------------- | ---------------------------------------- | ------------------------------- | ---------------------------------------------------------- |
| `run`                 | `monitoring_date: date`                  | `None`                          | 監視対象銘柄全件の配当利回りを計算してターミナルに結果出力 |
| `calculate_for_stock` | `sec_code: str`, `monitoring_date: date` | `DividendYieldMonitoringResult` | 単一銘柄の配当利回りを計算してdataclassで結果を返す        |

**出力イメージ（ターミナル）**:
```
[2026-02-21] 配当利回り監視結果
====================================
優先購入候補（利回り ≥ 4.0%）:
  7203: 利回り 4.2% (stock: ¥1,500, dividend: ¥63) [priority/スコア85]
  6758: 利回り 4.5% (stock: ¥2,200, dividend: ¥99) [active/スコア72]

購入検討（利回り ≥ 3.5%）:
  4502: 利回り 3.7% (stock: ¥1,080, dividend: ¥40) [watch/スコア70]

監視強化（利回り ≥ 3.0%）:
  8053: 利回り 3.1% (stock: ¥1,290, dividend: ¥40) [watch/スコア71]

監視継続（利回り < 3.0%）:
  9999: 利回り 2.5% (stock: ¥2,000, dividend: ¥50) [active/スコア82]

データ取得不可:
  1111: 配当データなし
  2222: 株価データなし
====================================
合計監視対象: 7銘柄 / 優先購入候補: 2銘柄 / 購入検討: 1銘柄
```

**購入判断レベルの決定ロジック（privateメソッド）**:

| メソッド                  | 判定内容                                                                            |
| ------------------------- | ----------------------------------------------------------------------------------- |
| `_resolve_purchase_level` | 配当利回りに基づいて購入判断レベル（`priority`/`consider`/`watch`/`monitor`）を決定 |

| 配当利回り範囲 | 購入判断レベル | 説明           |
| -------------- | -------------- | -------------- |
| ≥ 4.0%         | `priority`     | 優先購入候補   |
| ≥ 3.5%         | `consider`     | 購入検討       |
| ≥ 3.0%         | `watch`        | 監視強化       |
| < 3.0%         | `monitor`      | 監視継続       |
| データ取得不可 | `unavailable`  | データ取得不可 |

**ユーティリティメソッド（privateメソッド）**:

| メソッド                    | 説明                                                        |
| --------------------------- | ----------------------------------------------------------- |
| `_get_latest_dividend`      | 最新の配当金データを取得（`EdinetStockDividendRepository`） |
| `_get_latest_stock_price`   | 最新の株価データを取得（`StockData1dRepository`）           |
| `_calculate_dividend_yield` | 配当利回りを計算（配当金 ÷ 株価 × 100）                     |
| `_convert_to_yahoo_code`    | EDINET証券コードをYahoo Finance用銘柄コードに変換           |

---

## 5. 計算ロジック詳細

### 5.1 監視対象銘柄の抽出

`ScreeningResultRepository.list()` で以下条件の銘柄を取得:
- `status` が `watch`, `active`, または `priority`
- 最新の `evaluation_date` でフィルタ（同一銘柄で複数日付がある場合）

### 5.2 配当利回りの計算

```python
dividend_yield = (dividend_amount / stock_price) * 100
```

**計算不可の条件**:
- 配当金データがNULLまたは0以下
- 株価データがNULLまたは0以下
- いずれかのデータが取得できない

これらの場合、`purchase_level` を `unavailable` とし、配当利回りは `None` とする。

### 5.3 銘柄コードの変換

EDINET証券コード（例: `7203`）を Yahoo Finance用銘柄コード（例: `7203.T`）に変換する必要がある。

**既存の変換ユーティリティ**:
- `app.utils.stock_code_converter.to_yahoo_code()` を使用

**株価データのsymbol**:
- `stocks_1d.symbol` には Yahoo Finance形式（例: `7203.T`）で保存されている

### 5.4 最新データの取得方法

**配当金**:
```python
# EdinetStockDividendRepositoryで最新の決算期末日のデータを取得
# sec_code でフィルタ → period_end_date の降順 → 最初の1件
```

**株価**:
```python
# StockData1dRepositoryで最新のtimestampのデータを取得
# symbol でフィルタ → timestamp の降順 → 最初の1件
```

---

## 6. 依存ライブラリ

既存ライブラリのみで実装可能。新規追加なし。

| ライブラリ   | 用途             | 追加が必要か |
| ------------ | ---------------- | ------------ |
| `sqlalchemy` | データベース接続 | 既存         |
| `decimal`    | 高精度計算       | 既存（標準） |

---

## 7. 実装順序

### Phase 1（今回実装）- 監視最小実装

**目標**: ターミナルで監視対象銘柄の配当利回りと購入判断レベルを確認できること。DB保存・APIは不要。

- [ ] `app/services/monitoring/dividend_yield_monitoring_service.py` 実装
  - `DividendYieldMonitoringResult` dataclass 定義（同ファイル内）
  - `DividendYieldMonitoringService` クラス実装
- [ ] `scripts/run_dividend_yield_monitoring.py` 実装（CLI実行スクリプト）
- [ ] ユニットテスト（`tests/unit/services/monitoring/test_dividend_yield_monitoring_service.py`）

### Phase 2（後工程）- DB保存・バッチ化

- [ ] `DividendYieldMonitoring` モデル定義
- [ ] `DividendYieldMonitoringRepository` 実装
- [ ] Alembicマイグレーション（`dividend_yield_monitoring` テーブル）
- [ ] `DividendYieldMonitoringService` にDB保存機能追加
- [ ] 定期バッチスクリプト（`scripts/batch/batch_dividend_yield_monitoring.py`）

### Phase 3（後工程）- API / フロントエンド

- [ ] APIエンドポイント (`app/api/v1/monitoring.py`)
  - `GET /api/v1/monitoring/dividend-yield` - 最新の監視結果取得
  - `GET /api/v1/monitoring/dividend-yield/{sec_code}` - 特定銘柄の履歴取得
- [ ] フロントエンド画面
  - 配当利回り一覧表示
  - 配当利回り推移グラフ
  - 購入判断レベル別フィルタ

---

## 8. 注意事項

### 8.1 データの鮮度

- **株価データ**: 市場が閉まっている時間帯は前営業日の終値が最新となる
- **配当金データ**: 決算発表後にEDINETデータが更新されるまでタイムラグがある可能性
- 週末・祝日の実行時は、前営業日のデータで計算される

### 8.2 銘柄コードの対応

- `screening_results.sec_code`: EDINET形式（例: `7203`）
- `stocks_1d.symbol`: Yahoo Finance形式（例: `7203.T`）
- 変換には `to_yahoo_code()` を使用

### 8.3 配当利回りの解釈

- **実績配当**: 過去の実績値を使用（予想配当ではない）
- 減配・無配が決定済みでEDINETデータが更新されていない場合、実際より高い利回りが表示される可能性
- あくまで**スクリーニング通過銘柄**の監視であり、配当利回りのみで購入判断すべきではない

### 8.4 エラーハンドリング

- データ取得失敗時は `purchase_level` を `unavailable` とし、エラーメッセージを出力
- 一部銘柄のエラーで全体処理を中断しない（Best Effort）

---

## 9. 将来的な拡張案（Phase 4以降）

- **アラート機能**: 配当利回りが設定閾値を超えた場合にメール通知
- **過去データ分析**: 配当利回りの推移から割安・割高を判定
- **セクター別集計**: セクターごとの平均配当利回りを表示
- **配当性向の追加表示**: 配当金の持続可能性を評価
- **予想配当対応**: EDINETデータに予想配当が含まれる場合はそちらも表示

---

## 10. 関連ドキュメント

- [高配当株スクリーニングシステム設計書](./high_dividend_screening_design.md)
- [投資ルール](./ルール.md)
- [データアクセス層設計](../architecture/layers/data_access_layer.md)
