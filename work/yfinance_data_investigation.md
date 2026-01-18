# yfinanceデータ取得調査レポート

**調査日**: 2026年1月15日
**対象**: yfinanceライブラリから取得可能なデータ
**サンプル銘柄**: トヨタ自動車（7203.T）

---

## 📋 目次

1. [調査の概要](#調査の概要)
2. [yfinanceから取得可能なデータ一覧](#yfinanceから取得可能なデータ一覧)
3. [データの分類](#データの分類)
4. [テーブル設計の推奨案](#テーブル設計の推奨案)
5. [実装の優先順位](#実装の優先順位)
6. [サンプルコード](#サンプルコード)
7. [参考情報](#参考情報)

---

## 調査の概要

### 調査目的

本プロジェクトでは既に株価データ（OHLCV）の取得・保存が実装済みだが、財務分析やスクリーニング機能を実装するためには、以下の情報も必要：

- 時価総額
- PER（株価収益率）
- PBR（株価純資産倍率）
- 配当利回り
- 配当性向
- 財務諸表データ

これらのデータがyfinanceから取得可能かを調査し、データベース設計の指針を提供する。

### 調査結果サマリー

- ✅ yfinance.Ticker.info から**166個のキー**を持つ財務情報を取得可能
- ✅ 時価総額、PER、PBR、配当利回りなどは**現在値**として直接取得可能
- ✅ 過去のPER、PBRなどは、株価履歴・財務諸表・配当履歴から**計算が必要**
- ✅ 財務諸表（損益計算書・バランスシート・キャッシュフロー）を年次・四半期で取得可能
- ✅ 配当履歴、株式分割履歴、発行済株式数の履歴も取得可能

---

## yfinanceから取得可能なデータ一覧

### 1. 基本情報 (Ticker.info)

**取得可能なキー数**: 166個

#### 企業基本情報
```python
info = yf.Ticker("7203.T").info

# 企業情報
symbol = info['symbol']              # 銘柄コード
shortName = info['shortName']        # 短縮名
longName = info['longName']          # 正式名称
sector = info['sector']              # セクター
industry = info['industry']          # 業種
country = info['country']            # 国
city = info['city']                  # 都市
website = info['website']            # ウェブサイト
fullTimeEmployees = info['fullTimeEmployees']  # 従業員数
```

#### 株価情報
```python
currentPrice = info['currentPrice']          # 現在株価
previousClose = info['previousClose']        # 前日終値
open = info['open']                          # 始値
dayHigh = info['dayHigh']                    # 日中高値
dayLow = info['dayLow']                      # 日中安値
fiftyTwoWeekHigh = info['fiftyTwoWeekHigh']  # 52週高値
fiftyTwoWeekLow = info['fiftyTwoWeekLow']    # 52週安値
volume = info['volume']                      # 出来高
averageVolume = info['averageVolume']        # 平均出来高
```

#### 評価指標
```python
marketCap = info['marketCap']                              # 時価総額
enterpriseValue = info['enterpriseValue']                  # 企業価値
trailingPE = info['trailingPE']                           # PER（実績）
forwardPE = info['forwardPE']                             # PER（予想）
priceToBook = info['priceToBook']                         # PBR
priceToSalesTrailing12Months = info['priceToSalesTrailing12Months']  # PSR
```

#### 収益性指標
```python
trailingEps = info['trailingEps']        # EPS（実績）
forwardEps = info['forwardEps']          # EPS（予想）
bookValue = info['bookValue']            # 1株当たり純資産
profitMargins = info['profitMargins']    # 利益率
operatingMargins = info['operatingMargins']  # 営業利益率
returnOnEquity = info['returnOnEquity']  # ROE
returnOnAssets = info['returnOnAssets']  # ROA
```

#### 配当情報
```python
dividendRate = info['dividendRate']      # 年間配当
dividendYield = info['dividendYield']    # 配当利回り
payoutRatio = info['payoutRatio']        # 配当性向
exDividendDate = info['exDividendDate']  # 配当権利落ち日
```

#### 財務健全性
```python
totalCash = info['totalCash']            # 現金・預金
totalDebt = info['totalDebt']            # 総負債
debtToEquity = info['debtToEquity']      # 負債比率
currentRatio = info['currentRatio']      # 流動比率
quickRatio = info['quickRatio']          # 当座比率
```

#### 成長性
```python
revenueGrowth = info['revenueGrowth']    # 売上成長率
earningsGrowth = info['earningsGrowth']  # 利益成長率
totalRevenue = info['totalRevenue']      # 総売上高
revenuePerShare = info['revenuePerShare']  # 1株当たり売上高
```

#### アナリスト評価
```python
targetMeanPrice = info['targetMeanPrice']                # 目標株価（平均）
targetHighPrice = info['targetHighPrice']                # 目標株価（高値）
targetLowPrice = info['targetLowPrice']                  # 目標株価（安値）
recommendationKey = info['recommendationKey']            # 推奨評価
numberOfAnalystOpinions = info['numberOfAnalystOpinions']  # 推奨数
```

### 2. 株価履歴 (Ticker.history)

```python
ticker = yf.Ticker("7203.T")
history = ticker.history(period="1mo", interval="1d")

# 取得できるカラム（7個）
# - Open: 始値
# - High: 高値
# - Low: 安値
# - Close: 終値
# - Volume: 出来高
# - Dividends: 配当金
# - Stock Splits: 株式分割
```

**インデックス**: DatetimeIndex（日付）
**データ形式**: DataFrame
**取得期間**: 1日～max（全期間）

### 3. 損益計算書 (Ticker.financials / Ticker.quarterly_financials)

#### 年次損益計算書
```python
financials = ticker.financials  # 5期分取得可能
```

**主要項目（46項目）**:
- Total Revenue: 総売上高
- Net Income: 純利益
- Basic EPS: 基本的EPS
- Diluted EPS: 希薄化後EPS
- EBITDA: EBITDA
- Operating Income: 営業利益
- Gross Profit: 粗利益
- Cost Of Revenue: 売上原価
- Operating Expense: 営業費用
- Interest Income: 受取利息
- Interest Expense: 支払利息
- Tax Provision: 税金費用
- その他多数

#### 四半期損益計算書
```python
quarterly_financials = ticker.quarterly_financials  # 6期分取得可能
```

**主要項目**: 年次と同様（43項目）

### 4. バランスシート (Ticker.balance_sheet / Ticker.quarterly_balance_sheet)

#### 年次バランスシート
```python
balance_sheet = ticker.balance_sheet  # 4期分取得可能
```

**主要項目（84項目）**:
- Total Assets: 総資産
- Stockholders Equity: 株主資本
- Total Debt: 総負債
- Current Assets: 流動資産
- Current Liabilities: 流動負債
- Cash And Cash Equivalents: 現金及び現金同等物
- Accounts Receivable: 売掛金
- Inventory: 棚卸資産
- Property Plant Equipment: 有形固定資産
- Goodwill: のれん
- その他多数

#### 四半期バランスシート
```python
quarterly_balance_sheet = ticker.quarterly_balance_sheet  # 5期分取得可能
```

### 5. キャッシュフロー計算書 (Ticker.cashflow / Ticker.quarterly_cashflow)

#### 年次キャッシュフロー
```python
cashflow = ticker.cashflow  # 4期分取得可能
```

**主要項目（53項目）**:
- Free Cash Flow: フリーキャッシュフロー
- Operating Cash Flow: 営業CF
- Investing Cash Flow: 投資CF
- Financing Cash Flow: 財務CF
- Capital Expenditure: 設備投資
- Issuance Of Debt: 借入
- Repayment Of Debt: 返済
- その他多数

#### 四半期キャッシュフロー
```python
quarterly_cashflow = ticker.quarterly_cashflow  # 5期分取得可能
```

### 6. 配当履歴 (Ticker.dividends)

```python
dividends = ticker.dividends
```

**データ形式**: Series
**インデックス**: DatetimeIndex（配当権利落ち日）
**値**: 配当金額
**取得期間**: トヨタの場合、1999年から53回分

### 7. 株式分割履歴 (Ticker.splits)

```python
splits = ticker.splits
```

**データ形式**: Series
**インデックス**: DatetimeIndex（分割実施日）
**値**: 分割比率
**取得期間**: トヨタの場合、2件（2021年に5分割）

### 8. 発行済株式数の履歴 (Ticker.get_shares_full)

```python
shares = ticker.get_shares_full(start="2020-01-01")
```

**データ形式**: Series
**インデックス**: DatetimeIndex
**値**: 発行済株式数
**取得期間**: 日次データで327件以上

### 9. アナリスト推奨 (Ticker.recommendations)

```python
recommendations = ticker.recommendations
```

**データ形式**: DataFrame
**主要カラム**:
- period: 期間（0m, -1m, -2m, -3m）
- strongBuy: 強気買い推奨数
- buy: 買い推奨数
- hold: 中立推奨数
- sell: 売り推奨数
- strongSell: 強気売り推奨数

### 10. 機関投資家保有状況 (Ticker.institutional_holders)

```python
institutional_holders = ticker.institutional_holders
```

**主要カラム**:
- Date Reported: 報告日
- Holder: 保有者名
- pctHeld: 保有比率
- Shares: 保有株数
- Value: 保有額
- pctChange: 変化率

**備考**: 日本株では限定的なデータ

### 11. 投資信託保有状況 (Ticker.mutualfund_holders)

```python
mutualfund_holders = ticker.mutualfund_holders
```

**主要カラム**: 機関投資家保有と同様

### 12. インサイダー取引 (Ticker.insider_transactions)

```python
insider_transactions = ticker.insider_transactions
```

**主要カラム**:
- Start Date: 取引日
- Insider: インサイダー名
- Position: 役職
- Transaction: 取引種別
- Shares: 株数
- Value: 金額

**備考**: 日本株では限定的なデータ

---

## データの分類

### 🕐 時系列データ（過去情報を含めて保持が必要）

| No  | データ名                   | データソース                   | 期間   | 項目数 |
| --- | -------------------------- | ------------------------------ | ------ | ------ |
| 1   | 株価データ                 | Ticker.history()               | 任意   | 7      |
| 2   | 配当履歴                   | Ticker.dividends               | 1999～ | 53回   |
| 3   | 株式分割履歴               | Ticker.splits                  | 全期間 | 2件    |
| 4   | 発行済株式数               | Ticker.get_shares_full()       | 日次   | 327+   |
| 5   | 損益計算書（年次）         | Ticker.financials              | 5期    | 46     |
| 6   | 損益計算書（四半期）       | Ticker.quarterly_financials    | 6期    | 43     |
| 7   | バランスシート（年次）     | Ticker.balance_sheet           | 4期    | 84     |
| 8   | バランスシート（四半期）   | Ticker.quarterly_balance_sheet | 5期    | 84     |
| 9   | キャッシュフロー（年次）   | Ticker.cashflow                | 4期    | 53     |
| 10  | キャッシュフロー（四半期） | Ticker.quarterly_cashflow      | 5期    | 45     |
| 11  | 財務指標スナップショット   | Ticker.info（日次保存）        | 日次   | 約20   |
| 12  | アナリスト推奨             | Ticker.recommendations         | 4期    | 6      |
| 13  | 機関投資家保有             | Ticker.institutional_holders   | 四半期 | 6      |
| 14  | 投資信託保有               | Ticker.mutualfund_holders      | 四半期 | 6      |
| 15  | インサイダー取引           | Ticker.insider_transactions    | 取引時 | 9      |

#### 時系列データの特徴

- ✅ 過去データを削除せず、追加・更新のみ
- ✅ `UNIQUE(symbol, date)` 制約で重複防止
- ✅ インデックスを `(symbol, date DESC)` に設定してクエリ高速化
- ✅ 過去との比較分析が可能
- ✅ トレンド分析、推移分析に使用

### 📌 マスタデータ（現在の情報のみを保持）

| No  | データ名     | データソース         | 更新頻度 |
| --- | ------------ | -------------------- | -------- |
| 1   | 企業基本情報 | Ticker.info          | 低頻度   |
| 2   | 主要株主構成 | Ticker.major_holders | 四半期   |

#### マスタデータの特徴

- ✅ 最新情報で上書き
- ✅ `symbol`をPKまたはUNIQUE制約
- ✅ 更新頻度が低い
- ✅ JOIN用の参照テーブルとして機能

---

## テーブル設計の推奨案

### フェーズ2: 財務指標（優先度: 高）

#### 1. stock_basic_info - 企業基本情報

```sql
CREATE TABLE stock_basic_info (
    symbol VARCHAR(20) PRIMARY KEY,
    short_name VARCHAR(100),
    long_name VARCHAR(200),
    sector VARCHAR(100),
    industry VARCHAR(100),
    country VARCHAR(50),
    city VARCHAR(100),
    website VARCHAR(200),
    full_time_employees INTEGER,
    phone VARCHAR(50),
    address VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_stock_basic_sector ON stock_basic_info(sector);
CREATE INDEX idx_stock_basic_industry ON stock_basic_info(industry);
```

**データソース**: Ticker.info
**更新頻度**: 低頻度（企業情報変更時）
**備考**: 既存のstock_masterに統合することも検討可能

#### 2. stock_financial_info - 日次財務指標

```sql
CREATE TABLE stock_financial_info (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    date DATE NOT NULL,

    -- 評価指標
    market_cap BIGINT,
    enterprise_value BIGINT,
    trailing_pe DECIMAL(10,2),
    forward_pe DECIMAL(10,2),
    price_to_book DECIMAL(10,2),
    price_to_sales DECIMAL(10,2),
    peg_ratio DECIMAL(10,2),

    -- 収益性
    trailing_eps DECIMAL(10,2),
    forward_eps DECIMAL(10,2),
    book_value DECIMAL(10,2),
    profit_margins DECIMAL(6,4),
    operating_margins DECIMAL(6,4),
    return_on_equity DECIMAL(6,4),
    return_on_assets DECIMAL(6,4),

    -- 配当
    dividend_rate DECIMAL(10,2),
    dividend_yield DECIMAL(6,4),
    payout_ratio DECIMAL(6,4),

    -- 株価
    current_price DECIMAL(10,2),
    previous_close DECIMAL(10,2),
    fifty_two_week_high DECIMAL(10,2),
    fifty_two_week_low DECIMAL(10,2),

    -- 財務健全性
    total_cash BIGINT,
    total_debt BIGINT,
    debt_to_equity DECIMAL(10,2),
    current_ratio DECIMAL(6,2),
    quick_ratio DECIMAL(6,2),

    -- 成長性
    revenue_growth DECIMAL(6,4),
    earnings_growth DECIMAL(6,4),
    total_revenue BIGINT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, date)
);

-- インデックス
CREATE INDEX idx_financial_info_symbol_date ON stock_financial_info(symbol, date DESC);
CREATE INDEX idx_financial_info_date ON stock_financial_info(date);
CREATE INDEX idx_financial_info_pe ON stock_financial_info(trailing_pe);
CREATE INDEX idx_financial_info_pbr ON stock_financial_info(price_to_book);
CREATE INDEX idx_financial_info_dividend_yield ON stock_financial_info(dividend_yield);
```

**データソース**: Ticker.info（日次スナップショット）
**更新頻度**: 毎日
**用途**: スクリーニング、時系列分析、割安度判定

#### 3. stock_dividends - 配当履歴

```sql
CREATE TABLE stock_dividends (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    ex_dividend_date DATE NOT NULL,
    dividend_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, ex_dividend_date)
);

-- インデックス
CREATE INDEX idx_dividends_symbol_date ON stock_dividends(symbol, ex_dividend_date DESC);
CREATE INDEX idx_dividends_date ON stock_dividends(ex_dividend_date);
```

**データソース**: Ticker.dividends
**更新頻度**: 配当発表時
**用途**: 配当利回り計算、配当成長率分析

#### 4. stock_splits - 株式分割履歴

```sql
CREATE TABLE stock_splits (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    split_date DATE NOT NULL,
    split_ratio DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, split_date)
);

-- インデックス
CREATE INDEX idx_splits_symbol_date ON stock_splits(symbol, split_date DESC);
```

**データソース**: Ticker.splits
**更新頻度**: 分割実施時
**用途**: 株価の正しい解釈、調整後株価の計算

### フェーズ3: 財務諸表（優先度: 中）

#### 5. stock_financials_annual - 年次損益計算書

```sql
CREATE TABLE stock_financials_annual (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    fiscal_date DATE NOT NULL,

    -- 主要項目
    total_revenue BIGINT,
    net_income BIGINT,
    basic_eps DECIMAL(10,2),
    diluted_eps DECIMAL(10,2),
    ebitda BIGINT,
    operating_income BIGINT,
    gross_profit BIGINT,
    cost_of_revenue BIGINT,
    operating_expense BIGINT,
    interest_income BIGINT,
    interest_expense BIGINT,
    tax_provision BIGINT,

    -- その他の項目（JSONBで柔軟に保存）
    additional_data JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, fiscal_date)
);

-- インデックス
CREATE INDEX idx_financials_annual_symbol_date ON stock_financials_annual(symbol, fiscal_date DESC);
CREATE INDEX idx_financials_annual_revenue ON stock_financials_annual(total_revenue);
```

**データソース**: Ticker.financials
**更新頻度**: 年次（決算発表時）
**用途**: 業績推移分析、成長性評価

#### 6. stock_balance_sheet_annual - 年次バランスシート

```sql
CREATE TABLE stock_balance_sheet_annual (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    fiscal_date DATE NOT NULL,

    -- 資産
    total_assets BIGINT,
    current_assets BIGINT,
    cash_and_cash_equivalents BIGINT,
    accounts_receivable BIGINT,
    inventory BIGINT,
    property_plant_equipment BIGINT,

    -- 負債
    total_liabilities BIGINT,
    current_liabilities BIGINT,
    total_debt BIGINT,

    -- 純資産
    stockholders_equity BIGINT,

    -- その他の項目
    additional_data JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, fiscal_date)
);

-- インデックス
CREATE INDEX idx_balance_sheet_annual_symbol_date ON stock_balance_sheet_annual(symbol, fiscal_date DESC);
```

**データソース**: Ticker.balance_sheet
**更新頻度**: 年次
**用途**: 財務健全性分析、自己資本比率計算

#### 7. stock_cashflow_annual - 年次キャッシュフロー

```sql
CREATE TABLE stock_cashflow_annual (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    fiscal_date DATE NOT NULL,

    -- キャッシュフロー
    operating_cashflow BIGINT,
    investing_cashflow BIGINT,
    financing_cashflow BIGINT,
    free_cashflow BIGINT,
    capital_expenditure BIGINT,

    -- その他の項目
    additional_data JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, fiscal_date)
);

-- インデックス
CREATE INDEX idx_cashflow_annual_symbol_date ON stock_cashflow_annual(symbol, fiscal_date DESC);
```

**データソース**: Ticker.cashflow
**更新頻度**: 年次
**用途**: CF分析、設備投資動向

#### 8. stock_shares_outstanding - 発行済株式数

```sql
CREATE TABLE stock_shares_outstanding (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
    date DATE NOT NULL,
    shares_outstanding BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, date)
);

-- インデックス
CREATE INDEX idx_shares_outstanding_symbol_date ON stock_shares_outstanding(symbol, date DESC);
```

**データソース**: Ticker.get_shares_full()
**更新頻度**: 変更時
**用途**: 時価総額計算、希薄化分析

### フェーズ4以降: 四半期データ・その他

以下は四半期ベースや保有・インサイダー情報など、フェーズ4以降で実装を検討するテーブル案です。各テーブルは yfinance の四半期系 API（`quarterly_financials` / `quarterly_balance_sheet` / `quarterly_cashflow`）や保有・推奨データを元に設計しています。

#### stock_financials_quarterly - 四半期損益計算書
```sql
CREATE TABLE stock_financials_quarterly (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   fiscal_date DATE NOT NULL,
   period_end DATE NOT NULL,

   -- 主要項目（必要な行だけ明示、残りは JSONB）
   total_revenue BIGINT,
   net_income BIGINT,
   basic_eps DECIMAL(10,2),
   diluted_eps DECIMAL(10,2),
   operating_income BIGINT,
   gross_profit BIGINT,

   additional_data JSONB,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, fiscal_date)
);

CREATE INDEX idx_financials_q_symbol_date ON stock_financials_quarterly(symbol, fiscal_date DESC);
```
データソース: `Ticker.quarterly_financials`（6期分程度）
更新頻度: 決算発表時（四半期毎）
備考: 年次テーブルと同様に主要項目を列として持ち、残りは `additional_data` に格納して柔軟性を確保する。

#### stock_balance_sheet_quarterly - 四半期バランスシート
```sql
CREATE TABLE stock_balance_sheet_quarterly (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   fiscal_date DATE NOT NULL,
   period_end DATE NOT NULL,

   total_assets BIGINT,
   current_assets BIGINT,
   cash_and_cash_equivalents BIGINT,
   accounts_receivable BIGINT,
   inventory BIGINT,
   total_liabilities BIGINT,
   current_liabilities BIGINT,
   total_debt BIGINT,
   stockholders_equity BIGINT,

   additional_data JSONB,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, fiscal_date)
);

CREATE INDEX idx_balance_q_symbol_date ON stock_balance_sheet_quarterly(symbol, fiscal_date DESC);
```
データソース: `Ticker.quarterly_balance_sheet`（5期分程度）
更新頻度: 四半期毎
備考: 四半期データは年次より観測数が多く、差分計算や QoQ 比較に使う。

#### stock_cashflow_quarterly - 四半期キャッシュフロー
```sql
CREATE TABLE stock_cashflow_quarterly (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   fiscal_date DATE NOT NULL,
   period_end DATE NOT NULL,

   operating_cashflow BIGINT,
   investing_cashflow BIGINT,
   financing_cashflow BIGINT,
   free_cashflow BIGINT,
   capital_expenditure BIGINT,

   additional_data JSONB,
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, fiscal_date)
);

CREATE INDEX idx_cashflow_q_symbol_date ON stock_cashflow_quarterly(symbol, fiscal_date DESC);
```
データソース: `Ticker.quarterly_cashflow`（5期分程度）
更新頻度: 四半期毎
備考: 四半期CFは季節性の影響が大きいため、年率換算や累積比較の取り扱いルールを運用で定義すること。

#### stock_analyst_recommendations - アナリスト推奨
```sql
CREATE TABLE stock_analyst_recommendations (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   period DATE NOT NULL,
   strong_buy INTEGER,
   buy INTEGER,
   hold INTEGER,
   sell INTEGER,
   strong_sell INTEGER,

   source VARCHAR(100),
   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, period, source)
);

CREATE INDEX idx_recommendations_symbol_period ON stock_analyst_recommendations(symbol, period DESC);
```
データソース: `Ticker.recommendations`
更新頻度: 月次〜四半期（変動あり）
備考: `source` でデータ元（Yahoo 集計など）を明示し、期間ごとの推移を保存する。

注意（yfinance列名）: `period`, `strongBuy`, `buy`, `hold`, `sell`, `strongSell` → 上記の DB 列名にマッピング（例: `strongBuy` → `strong_buy`）。

#### stock_holders_institutional - 機関投資家保有
```sql
CREATE TABLE stock_holders_institutional (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   report_date DATE NOT NULL,
   holder VARCHAR(200),
   shares BIGINT,
   value BIGINT,
   pct_held DECIMAL(6,4),

   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, report_date, holder)
);

CREATE INDEX idx_institutional_symbol_date ON stock_holders_institutional(symbol, report_date DESC);
```
データソース: `Ticker.institutional_holders`
更新頻度: 四半期（または報告更新時）
備考: 日本株では空欄や限定的なデータがあるため NULL 安全に扱う。保持者名は正規化テーブル化を検討。

注意（yfinance列名）: `Date Reported`, `Holder`, `pctHeld`, `Shares`, `Value`, `pctChange` → DB 列名は `report_date`, `holder`, `pct_held`, `shares`, `value`, `pct_change` 等にマップしてください。

#### stock_holders_mutualfund - 投資信託保有
```sql
CREATE TABLE stock_holders_mutualfund (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   report_date DATE NOT NULL,
   holder VARCHAR(200),
   shares BIGINT,
   value BIGINT,
   pct_held DECIMAL(6,4),

   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, report_date, holder)
);

CREATE INDEX idx_mutualfund_symbol_date ON stock_holders_mutualfund(symbol, report_date DESC);
```
データソース: `Ticker.mutualfund_holders`
更新頻度: 四半期（または報告更新時）
備考: `stock_holders_institutional` とスキーマを揃え、集計クエリで結合しやすくする。

注意（yfinance列名）: `Date Reported`, `Holder`, `pctHeld`, `Shares`, `Value`, `pctChange` → DB 列名は `report_date`, `holder`, `pct_held`, `shares`, `value`, `pct_change` 等にマップしてください。

#### stock_insider_transactions - インサイダー取引
```sql
CREATE TABLE stock_insider_transactions (
   id BIGSERIAL PRIMARY KEY,
   symbol VARCHAR(20) NOT NULL REFERENCES stock_master(symbol),
   transaction_date DATE NOT NULL,
   insider VARCHAR(200),
   position VARCHAR(100),
   transaction_type VARCHAR(50),
   shares BIGINT,
   value BIGINT,
   url TEXT,
   text TEXT,
   ownership VARCHAR(100),

   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

   UNIQUE(symbol, transaction_date, insider, transaction_type, shares)
);

CREATE INDEX idx_insider_symbol_date ON stock_insider_transactions(symbol, transaction_date DESC);
```
データソース: `Ticker.insider_transactions`
更新頻度: 随時（発生時）
備考: 日本株ではデータ量が限られるが、米国株で有益。セキュリティ・PII 層で扱う必要があるか検討する。

注意（yfinance列名）: `Start Date`, `Insider`, `Position`, `Transaction`, `Shares`, `Value`, `URL`, `Text`, `Ownership` → `transaction_date` は `Start Date` を利用、`transaction_type` は `Transaction` にマップします。`URL`/`Text`/`Ownership` は補助情報として `url`/`text`/`ownership` に保存します。

---

これらのテーブルはフェーズ4での導入候補で、まずは `stock_financials_quarterly` と `stock_cashflow_quarterly` を優先してモデル化・マイグレーション作成することを推奨します。

---

## 実装の優先順位

### Phase 2: 基本財務指標（次の実装候補）

**目標**: 基本的なスクリーニング機能の実装

1. **stock_basic_info** - 企業基本情報
   - マイグレーション作成
   - モデル定義
   - データ取得・保存ロジック

2. **stock_financial_info** - 日次財務指標
   - マイグレーション作成
   - モデル定義（Ticker.infoから主要指標を抽出）
   - Fetcher実装（StockFinancialInfoFetcher）
   - Service実装（取得・保存）
   - バッチ処理実装

3. **stock_dividends** - 配当履歴
   - マイグレーション作成
   - モデル定義
   - Fetcher実装
   - Service実装

4. **stock_splits** - 株式分割履歴
   - マイグレーション作成
   - モデル定義
   - Fetcher実装
   - Service実装

**実装後の機能**:
- PER/PBRでのスクリーニング
- 配当利回りでの絞り込み
- 時価総額でのフィルタリング
- 財務指標の時系列分析

### Phase 3: 財務諸表（中期）

**目標**: 詳細な財務分析機能

5. **stock_financials_annual** - 年次損益計算書
6. **stock_balance_sheet_annual** - 年次バランスシート
7. **stock_cashflow_annual** - 年次キャッシュフロー
8. **stock_shares_outstanding** - 発行済株式数

**実装後の機能**:
- 売上・利益成長率の分析
- ROE/ROAの推移分析
- 自己資本比率の監視
- FCFマージンの計算

### Phase 4: 四半期データ（長期）

9. 各種四半期データテーブル

**実装後の機能**:
- 四半期ベースの業績分析
- より細かいトレンド把握

### Phase 5: 高度な分析（オプション）

10. アナリスト推奨
11. 機関投資家保有
12. インサイダー取引

**備考**: 主に米国株向けの機能

---

## サンプルコード

### 1. 現在の財務情報取得

```python
import yfinance as yf

ticker = yf.Ticker("7203.T")
info = ticker.info

# 主要指標の取得
market_cap = info.get('marketCap')           # 時価総額
trailing_pe = info.get('trailingPE')         # PER (実績)
price_to_book = info.get('priceToBook')      # PBR
dividend_yield = info.get('dividendYield')   # 配当利回り
roe = info.get('returnOnEquity')             # ROE
```

### 2. 過去の株価データ取得

```python
# 過去5年間の日次データ
history = ticker.history(period="5y", interval="1d")

# 特定期間の指定
from datetime import datetime
history = ticker.history(start="2020-01-01", end="2025-12-31")
```

### 3. 配当履歴の取得

```python
# 配当履歴
dividends = ticker.dividends

# 年間配当の集計
yearly_dividends = dividends.resample('YE').sum()

# 最新10件の配当
recent_dividends = dividends.tail(10)
```

### 4. 財務諸表の取得

```python
# 損益計算書（年次）
financials = ticker.financials

# 特定項目の取得
total_revenue = financials.loc['Total Revenue']
net_income = financials.loc['Net Income']
eps = financials.loc['Basic EPS']

# バランスシート（年次）
balance_sheet = ticker.balance_sheet
total_assets = balance_sheet.loc['Total Assets']
equity = balance_sheet.loc['Stockholders Equity']

# キャッシュフロー（年次）
cashflow = ticker.cashflow
operating_cf = cashflow.loc['Operating Cash Flow']
free_cf = cashflow.loc['Free Cash Flow']
```

### 5. 過去のPER/PBRの計算例

```python
import pandas as pd

# 株価履歴（月末）
history = ticker.history(period="5y")
monthly_prices = history['Close'].resample('ME').last()

# 財務データ
financials = ticker.financials
balance_sheet = ticker.balance_sheet
shares = ticker.get_shares_full(start="2020-01-01")

# 各年度ごとにPER/PBRを計算
for date in financials.columns:
    year = date.year

    # その年の12月末の株価
    year_end_price = monthly_prices[monthly_prices.index.year == year].iloc[-1]

    # EPS
    eps = financials.loc['Basic EPS', date]

    # 純資産と株式数からBPS計算
    equity = balance_sheet.loc['Stockholders Equity', date]
    shares_count = shares[shares.index.year <= year].iloc[-1]
    bps = equity / shares_count

    # PER/PBR計算
    per = year_end_price / eps if eps > 0 else None
    pbr = year_end_price / bps if bps > 0 else None

    print(f"{year}年度: 株価={year_end_price:.2f}, PER={per:.2f}, PBR={pbr:.2f}")
```

### 6. データ取得のベストプラクティス

```python
import asyncio
from typing import Dict, Any

class FinancialDataFetcher:
    """財務データ取得クラス"""

    async def fetch_all_data(self, symbol: str) -> Dict[str, Any]:
        """全データを非同期で取得"""
        loop = asyncio.get_event_loop()
        ticker = await loop.run_in_executor(None, lambda: yf.Ticker(symbol))

        # 並列取得
        info_task = loop.run_in_executor(None, lambda: ticker.info)
        history_task = loop.run_in_executor(
            None, lambda: ticker.history(period="1mo")
        )
        dividends_task = loop.run_in_executor(None, lambda: ticker.dividends)

        # 結果を待機
        info, history, dividends = await asyncio.gather(
            info_task, history_task, dividends_task
        )

        return {
            "info": info,
            "history": history,
            "dividends": dividends
        }
```

---

## 参考情報

### yfinanceの主要なメソッド・属性

| メソッド/属性                    | 説明                   | 戻り値の型 |
| -------------------------------- | ---------------------- | ---------- |
| `Ticker.info`                    | 基本情報（166キー）    | dict       |
| `Ticker.history()`               | 株価履歴               | DataFrame  |
| `Ticker.financials`              | 年次損益計算書         | DataFrame  |
| `Ticker.quarterly_financials`    | 四半期損益計算書       | DataFrame  |
| `Ticker.balance_sheet`           | 年次バランスシート     | DataFrame  |
| `Ticker.quarterly_balance_sheet` | 四半期バランスシート   | DataFrame  |
| `Ticker.cashflow`                | 年次キャッシュフロー   | DataFrame  |
| `Ticker.quarterly_cashflow`      | 四半期キャッシュフロー | DataFrame  |
| `Ticker.dividends`               | 配当履歴               | Series     |
| `Ticker.splits`                  | 株式分割履歴           | Series     |
| `Ticker.actions`                 | 配当+分割              | DataFrame  |
| `Ticker.get_shares_full()`       | 発行済株式数           | Series     |
| `Ticker.recommendations`         | アナリスト推奨         | DataFrame  |
| `Ticker.institutional_holders`   | 機関投資家保有         | DataFrame  |
| `Ticker.mutualfund_holders`      | 投資信託保有           | DataFrame  |
| `Ticker.insider_transactions`    | インサイダー取引       | DataFrame  |
| `Ticker.major_holders`           | 主要株主               | DataFrame  |
| `Ticker.sustainability`          | ESG情報                | DataFrame  |
| `Ticker.options`                 | オプション有効期限     | tuple      |
| `Ticker.calendar`                | カレンダー             | dict       |
| `Ticker.earnings_dates`          | 決算発表日             | DataFrame  |

### 注意事項

1. **データの信頼性**
   - yfinanceは非公式ライブラリ
   - データの遅延や欠損がある可能性
   - 本番環境では定期的なデータ検証が必要

2. **レート制限**
   - Yahoo Financeのレート制限に注意
   - バッチ処理では適切な待機時間を設定
   - 1秒あたり1-2リクエスト程度が目安

3. **日本株固有の注意点**
   - 銘柄コードに「.T」を付与
   - 一部の米国株向け機能は利用不可
   - ESG情報、オプション情報は取得不可

4. **データ形式**
   - 日付はUTC（協定世界時）で返される
   - 日本時間に変換する場合は+9時間
   - 金額の単位に注意（円、千円、億円など）

### サンプルスクリプトの場所

本調査で作成したサンプルスクリプトは以下に保存されています：

1. `scripts/sample_financial_info.py`
   - 現在の財務情報を表示

2. `scripts/sample_historical_financial_info.py`
   - 過去のPER/PBR/配当利回り/配当性向を計算

3. `scripts/sample_all_yfinance_data.py`
   - yfinanceで取得可能な全データを網羅的に確認

### 関連ドキュメント

- yfinance公式: https://github.com/ranaroussi/yfinance
- 本プロジェクトのアーキテクチャ: `docs/architecture/README.md`
- 開発ワークフロー: `docs/develop-guide/development-workflow.md`

---

## まとめ

### 調査で明らかになったこと

✅ **yfinanceから豊富な財務データが取得可能**
- 現在値: 166個のキーを持つ財務情報
- 時系列: 株価、配当、分割、財務諸表など

✅ **PER/PBRなどの過去データは計算が必要**
- 株価履歴 + 財務諸表 + 発行済株式数から算出

✅ **段階的な実装が推奨される**
- フェーズ2: 基本財務指標（スクリーニング）
- フェーズ3: 財務諸表（詳細分析）
- フェーズ4以降: 四半期データ、高度な分析

### 次のアクションアイテム

1. **フェーズ2の実装開始**
   - [ ] stock_basic_info テーブル作成
   - [ ] stock_financial_info テーブル作成
   - [ ] stock_dividends テーブル作成
   - [ ] stock_splits テーブル作成

2. **Fetcher/Service実装**
   - [ ] StockFinancialInfoFetcher
   - [ ] StockDividendsFetcher
   - [ ] StockSplitsFetcher

3. **バッチ処理の追加**
   - [ ] 日次財務指標取得バッチ
   - [ ] 配当・分割履歴取得バッチ

4. **APIエンドポイントの追加**
   - [ ] GET /api/v1/stocks/{symbol}/financial-info
   - [ ] GET /api/v1/stocks/{symbol}/dividends
   - [ ] GET /api/v1/stocks/screen（スクリーニング）

---

**文書作成日**: 2026年1月15日
**作成者**: GitHub Copilot
**バージョン**: 1.0
