# ER Diagram - Stock Investment Analyzer

## Overview
This ER diagram represents the database schema for the Stock Investment Analyzer application, showing all entities and their relationships.

### Key Design Decisions

**EDINET テーブルの正規化**
- EDINET データは`EDINET_DOCUMENT`テーブルに**ドキュメント・メタデータ**（書類ID、提出日、報告書タイプなど）を集約することで正規化。
- `EDINET_PROFIT_AND_LOSS`、`EDINET_STOCK_DIVIDEND`、`EDINET_CASH_FLOW_STATEMENT`、`EDINET_BALANCE_SHEET` は各々の**実データのみ**を格納し、`EDINET_DOCUMENT_ID`の外部キーを通じてメタデータを参照。
- この設計により、同一のドキュメントから抽出された複数の財務statement に対してメタデータの重複を排除し、データの一貫性と保守性を向上。

## Mermaid ER Diagram

```mermaid
erDiagram
    ACCOUNT ||--o{ ACCOUNT_TRANSACTIONS : has
    ACCOUNT ||--o{ ACCOUNT_PORTFOLIOS : has
    STOCK_MASTER ||--o{ ACCOUNT_PORTFOLIOS : links
    STOCK_MASTER ||--o{ STOCKS_1D : contains
    STOCK_MASTER ||--o{ STOCK_SPLIT : references
    STOCK_MASTER ||--o{ DIVIDEND_YIELD_MONITORING : monitors
    STOCK_MASTER ||--o{ DIVIDEND_YIELD_HISTORY : "contains_history"
    STOCK_MASTER ||--o{ RELATIVE_STRENGTH : analyzes
    STOCK_MASTER ||--o{ SCREENING_RESULTS : evaluates
    STOCK_MASTER ||--o{ STOCK_CODE_MAPPING : has
    STOCK_CODE_MAPPING ||--o{ EDINET_DOCUMENT : connects
    EDINET_DOCUMENT ||--o{ EDINET_PROFIT_AND_LOSS : contains
    EDINET_DOCUMENT ||--o{ EDINET_STOCK_DIVIDEND : contains
    EDINET_DOCUMENT ||--o{ EDINET_CASH_FLOW_STATEMENT : contains
    EDINET_DOCUMENT ||--o{ EDINET_BALANCE_SHEET : contains
    EDINET_DOCUMENT ||--o{ EDINET_DIVIDEND_METRICS : contains
    EDINET_STOCK_DIVIDEND ||--o{ DIVIDEND_YIELD_HISTORY : "references"
    STOCKS_1D ||--o{ DIVIDEND_YIELD_HISTORY : "references_price"
    MARKET_CATEGORY_MASTER ||--o{ STOCK_MASTER : "categorizes"
    SECTOR_33_MASTER ||--o{ STOCK_MASTER : "classifies"
    SECTOR_17_MASTER ||--o{ STOCK_MASTER : "classifies"
    SCALE_MASTER ||--o{ STOCK_MASTER : "categorizes"
    SP500_STOCK_MASTER ||--o{ SP500_STOCKS_1D : contains

    ACCOUNT {
        int id PK "プライマリキー"
        string email UK "メールアドレス（ユニーク）"
        string hashed_password "ハッシュ化されたパスワード"
        string full_name "表示名"
        boolean is_active "アカウント有効フラグ"
        boolean is_superuser "管理者フラグ"
        datetime last_login "最終ログイン時刻"
        string provider "外部認証プロバイダ名"
        string external_id "外部プロバイダの識別子"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    ACCOUNT_TRANSACTIONS {
        int id PK "プライマリキー"
        int account_id FK "アカウントID"
        string transaction_type "取引種類（買付/売却/入出金）"
        string symbol "銘柄コード"
        int quantity "数量"
        decimal amount "金額"
        string currency "通貨コード"
        datetime executed_at "約定日時"
        datetime settled_at "決済日時"
        string status "取引ステータス"
        string external_id "外部取引ID"
        string note "メモ"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    ACCOUNT_PORTFOLIOS {
        int id PK "プライマリキー"
        int account_id FK "アカウントID"
        string portfolio_name "ポートフォリオ名"
        string symbol "銘柄コード"
        int quantity "保有株数"
        decimal avg_price "取得平均単価"
        decimal market_value "時価評価額"
        string currency "通貨コード"
        datetime valuation_date "時価計算日"
        decimal allocation "ポートフォリオ内比率"
        string note "メモ"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    STOCK_MASTER {
        int id PK "プライマリキー"
        string stock_code UK "株式コード（ユニーク）"
        string stock_name "企業名"
        int market_category_id FK "市場区分マスターID"
        string sector_code_33 "業種コード（33分類）"
        int sector_33_id FK "業種(33分類)マスターID"
        string sector_code_17 "業種コード（17分類）"
        int sector_17_id FK "業種(17分類)マスターID"
        string scale_code "規模コード"
        int scale_id FK "規模マスターID"
        string data_date "データ日付"
        int is_active "有効フラグ"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    MARKET_CATEGORY_MASTER {
        int id PK "プライマリキー"
        string code UK "市場区分コード（Prime/Standard/Growth等）"
        string name "市場区分名"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    SECTOR_33_MASTER {
        int id PK "プライマリキー"
        string code UK "業種コード（33分類）"
        string name "業種名（33分類）"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    SECTOR_17_MASTER {
        int id PK "プライマリキー"
        string code UK "業種コード（17分類）"
        string name "業種名（17分類）"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    SCALE_MASTER {
        int id PK "プライマリキー"
        string code UK "規模コード"
        string name "規模名"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    STOCK_MASTER_UPDATES {
        int id PK "プライマリキー"
        string update_type "更新タイプ（fetch等）"
        int total_stocks "総銘柄数"
        int added_stocks "新規追加数"
        int updated_stocks "更新数"
        int removed_stocks "削除数"
        string status "ステータス（running/success/failed）"
        string error_message "エラーメッセージ"
        datetime started_at "開始時刻"
        datetime completed_at "完了時刻"
    }

    STOCK_CODE_MAPPING {
        int id PK "プライマリキー"
        string stock_code FK "JPX株式コード"
        string sec_code UK "EDINET提出企業コード"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    STOCKS_1D {
        int id PK "プライマリキー"
        string symbol FK "銘柄コード"
        datetime timestamp "タイムスタンプ（JST）"
        decimal open "始値"
        decimal high "高値"
        decimal low "安値"
        decimal close "終値"
        decimal adj_close "調整終値"
        bigint volume "出来高"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    SP500_STOCK_MASTER {
        int id PK "プライマリキー"
        string Symbol UK "ティッカーコード（ユニーク）"
        string Security "企業名"
        string "GICS Sector" "セクター（GICS分類）"
        string "GICS Sub-Industry" "サブ業種"
        string "Headquarters Location" "本社所在地"
        date "Date added" "S&P 500追加日"
        string CIK "CIK番号"
        string Founded "設立年"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    SP500_STOCKS_1D {
        int id PK "プライマリキー"
        string symbol FK "ティッカーコード"
        datetime timestamp "タイムスタンプ（JST）"
        decimal open "始値"
        decimal high "高値"
        decimal low "安値"
        decimal close "終値"
        decimal adj_close "調整終値"
        bigint volume "出来高"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    EDINET_DOCUMENT {
        int id PK "プライマリキー"
        string doc_id UK "書類ID（ユニーク）"
        string sec_code FK "証券コード（EDINET提出企業コード）"
        date submission_date "提出日"
        string report_type "報告書タイプ（有価証券報告書等）"
        string candidate_contexts "候補コンテキスト"
        string candidate_keys "候補キー"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    EDINET_PROFIT_AND_LOSS {
        int id PK "プライマリキー"
        int edinet_document_id FK "EDINETドキュメントID"
        date period_end_date "報告期末日"
        int fiscal_year "会計年度"
        boolean is_consolidated "連結フラグ"
        decimal net_sales "売上高"
        decimal operating_income "営業利益"
        decimal eps "1株当たり利益"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    EDINET_STOCK_DIVIDEND {
        int id PK "プライマリキー"
        int edinet_document_id FK "EDINETドキュメントID"
        date period_end_date "報告期末日"
        int fiscal_year "会計年度"
        boolean is_consolidated "連結フラグ"
        decimal dividend_actual "年間配当金（実績）"
        decimal dividend_adj "年間配当金（調整後）"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    EDINET_CASH_FLOW_STATEMENT {
        int id PK "プライマリキー"
        int edinet_document_id FK "EDINETドキュメントID"
        date period_end_date "報告期末日"
        int fiscal_year "会計年度"
        boolean is_consolidated "連結フラグ"
        decimal operating_cf "営業キャッシュフロー"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    EDINET_BALANCE_SHEET {
        int id PK "プライマリキー"
        int edinet_document_id FK "EDINETドキュメントID"
        date period_end_date "報告期末日"
        int fiscal_year "会計年度"
        boolean is_consolidated "連結フラグ"
        decimal total_assets "総資産"
        decimal net_assets "純資産"
        decimal shareholders_equity "株主資本"
        decimal bps "BPS"
        decimal equity_ratio "自己資本比率"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    EDINET_DIVIDEND_METRICS {
        int id PK "プライマリキー"
        int edinet_document_id FK "EDINETドキュメントID"
        date period_end_date "報告期末日"
        int fiscal_year "会計年度"
        boolean is_consolidated "連結フラグ"
        decimal dividend_actual "実績配当金（円）"
        decimal eps "1株当たり利益（円）"
        decimal payout_ratio "配当性向"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    STOCK_SPLIT {
        int id PK "プライマリキー"
        string code "銘柄コード"
        date effective_date "発効日"
        int ratio_from "分割前比率"
        int ratio_to "分割後比率"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    DIVIDEND_YIELD_MONITORING {
        int id PK "プライマリキー"
        string symbol FK "銘柄コード（stock_code）"
        date monitoring_date "監視日"
        decimal latest_dividend_amount "最新配当金"
        decimal latest_stock_price "最新株価"
        decimal dividend_yield "配当利回り"
        string purchase_level "購入レベル"
        string screening_status "スクリーニング判定"
        int screening_total_score "スクリーニング総合スコア"
        date stock_price_source_date "株価参照日"
        date dividend_source_date "配当参照日"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    DIVIDEND_YIELD_HISTORY {
        int id PK "プライマリキー"
        string symbol FK "銘柄コード（stock_code）"
        date date UK "日付（symbol と合わせてユニーク）"
        decimal dividend "使用した年間配当"
        decimal stock_price "計算に使用した株価（COALESCE(adj_close, close)）"
        decimal dividend_yield "配当利回り（dividend/stock_price）"
        int fiscal_year "使用した配当年度"
        int edinet_document_id FK "配当取得元ドキュメントID"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    SCREENING_RESULTS {
        int id PK "プライマリキー"
        string symbol FK "銘柄コード（stock_code）"
        int evaluation_year "評価年度（西暦）"
        date fiscal_year_end "会計年度末"
        boolean pass_required_conditions "必須条件判定"
        int total_score "総合スコア"
        int score_dividend "配当スコア"
        int score_eps "EPS スコア"
        int score_stability "安定性スコア"
        int score_profitability "収益性スコア"
        string status "スクリーニング判定"
        json failed_conditions "不合格条件"
        json screening_details "詳細情報"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }

    RELATIVE_STRENGTH {
        int id PK "プライマリキー"
        string symbol FK "銘柄コード（stock_code）"
        date calculation_date "計算基準日（この日を最新データとして過去の変化率を算出）"
        decimal change_63days "63日間の変化率（%） — 終値を用いて計算（基準日終値 / 63日前終値 - 1）"
        decimal change_126days "126日間の変化率（%） — 終値を用いて計算"
        decimal change_189days "189日間の変化率（%） — 終値を用いて計算"
        decimal change_252days "252日間の変化率（%） — 終値を用いて計算"
        decimal relative_strength_score "レラティブストレングススコア（加重平均、終値ベース）"
        datetime created_at "作成日時"
        datetime updated_at "更新日時"
    }
```

## Entity Descriptions

### Account Management
- **Account**: ユーザーアカウント情報。複数のトランザクションとポートフォリオを保有。
- **AccountTransactions**: 各アカウントの買付・売却・入出金などの取引履歴。
- **AccountPortfolios**: 各アカウントが保有する銘柄ごとのポートフォリオ情報。

### Market Data - Stock Master & Prices & Mapping
- **StockMaster**: 銘柄マスタ（銘柄コード、名称、セクター情報など）。JPX株式コード（stock_code）で管理。
- **StockMasterUpdates**: 銘柄マスタ更新の履歴と統計情報。
- **StockCodeMapping**: JPX株式コード（stock_code）とEDINET提出企業コード（sec_code）の対応関係を管理するマッピングテーブル。1つのJPX企業が複数のEDINET企業コードを持つ可能性に対応。
- **Stocks_1d（他の時間軸1m/5m/15m/30m/1h/1wkも同様）**: 複数の時間軸における株価データ。OHLCV データを格納。ER図では日足（1d）を代表として表示。

### S&P 500 Market Data
- **SP500StockMaster**: S&P 500 の構成企業マスタ。Wikipedia の S&P 500 企業リストから取得し、ティッカーコード（symbol）を主キーとして管理。企業名、セクター、サブ業種、本社所在地、S&P 500 追加日、CIK番号、設立年などの企業情報を格納。
- **SP500Stocks_1d（他の時間軸1m/5m/15m/30m/1h/1wkも同様）**: S&P 500 構成企業の複数時間軸株価データ。OHLCV データを格納。ティッカーコード（symbol）でSP500StockMasterを参照。日本株データ（STOCKS_1D）と並行して管理。

### EDINET Financial Data（正規化済み）
- **EdinetDocument**: EDINET文書メタデータの集約テーブル。`doc_id`（書類ID）、`sec_code`（EDINET提出企業コード）、提出日、報告書タイプなど、複数の財務statement間で共通するドキュメント情報を管理。これにより、同一のドキュメントから抽出された複数の財務指標に対して単一のメタデータソースを提供。
- **EdinetProfitAndLoss**: EDINET損益計算書データ。`edinet_document_id`で EdinetDocument を参照。売上高、営業利益、EPS など実際の財務データのみを格納。
- **EdinetStockDividend**: EDINET配当情報データ。`edinet_document_id`で EdinetDocument を参照。年間配当金（実績/調整後）のみを格納。
- **EdinetCashFlowStatement**: EDINETキャッシュフロー計算書データ。`edinet_document_id`で EdinetDocument を参照。営業キャッシュフローなどの実データのみを格納。
- **EdinetBalanceSheet**: EDINET貸借対照表データ。`edinet_document_id`で EdinetDocument を参照。総資産、負債、資本などのバランスシート実データのみを格納。
- **EdinetDividendMetrics**: EDINET配当メトリクスデータ。`edinet_document_id`で EdinetDocument を参照。配当実績、EPS、配当性向などの計算指標データを格納。このテーブルは計算テーブルであり、既存の EdinetStockDividend と EdinetProfitAndLoss データから派生した指標を保持。

### Analysis & Monitoring
- **StockSplit**: 株式分割イベントの履歴。
- **DividendYieldMonitoring**: 配当利回り監視結果（スナップショット）。`symbol`（stock_code）を使用してStockMasterと紐付け。最新の監視情報を保持。
- **DividendYieldHistory**: 日次配当利回り履歴。EDINETから取得した年間配当と株価データから生成された時系列データ。計算に使用した``stock_price``は``COALESCE(adj_close, close)``で決定され、スナップショットとして保持（履歴の不変性を確保）。`symbol`（stock_code）でStockMasterを参照し、`edinet_document_id`でEdinetDocumentを参照。(symbol, date)をユニークキーとしてUPSERT可能。配当利回りレンジ分析やグラフ表示に利用。
- **RelativeStrength**: レラティブストレングス（William O'Neill式）を日次で算出・保存するテーブル。各レコードは「計算基準日（calculation_date）」を持ち、その日を最新データとして過去データを用いてスコアを算出します。主なポイント：

    - 変化率の算出は終値（`close`）を用い、基準日 D に対して次のように定義します。
        - 63日変化率 = (close[D] / close[D-63] - 1) × 100
        - 126日変化率 = (close[D] / close[D-126] - 1) × 100
        - 189日変化率 = (close[D] / close[D-189] - 1) × 100
        - 252日変化率 = (close[D] / close[D-252] - 1) × 100

    - 加重平均スコア（`relative_strength_score`）は終値ベースの変化率に対して次の重みを適用して算出します：
        - score = 0.4 × change_63days + 0.2 × change_126days + 0.2 × change_189days + 0.2 × change_252days

    - 例：2026-03-21 のスコアは基準日を 2026-03-21 として、当日の終値とそれぞれの遡及終値を参照して計算します。2026-03-20 のスコアは同様に基準日を 2026-03-20 として算出します。

    - 保存設計：`symbol` と `calculation_date` をユニークキーとし、UPSERT により各日付ごとのスコアを時系列で保持します。スクリーニング、チャート描画、日次バッチ出力の参照先として利用します。

    - 補足：過去データが不足する場合は `NULL` を許容する、または計算をスキップして不足フラグを付与する等の運用ルールを設けてください。

このテーブルは「各日を基準にその日のスコアを出す」用途に特化しており、終値を基準にした日次の相対強さ指標を時系列で扱うためのデータソースとなります。
- **ScreeningResults**: 高配当スクリーニング結果とスコア情報。`symbol`（stock_code）を使用してStockMasterと紐付け。

## Key Relationships

| From             | To                                                               | Type | Description                                             |
| ---------------- | ---------------------------------------------------------------- | ---- | ------------------------------------------------------- |
| Account          | AccountTransactions                                              | 1:N  | アカウントは複数の取引履歴を持つ                        |
| Account          | AccountPortfolios                                                | 1:N  | アカウントは複数のポートフォリオを保有                  |
| StockMaster      | AccountPortfolios                                                | 1:N  | 銘柄は複数のポートフォリオで参照される                  |
| StockMaster      | Stocks_1d（他の時間軸も同様）                                    | 1:N  | 銘柄は複数の日足株価データを持つ                        |
| StockMaster      | StockSplit                                                       | 1:N  | 銘柄は複数の分割イベントを持つ                          |
| StockMaster      | DividendYieldMonitoring                                          | 1:N  | 銘柄は複数の監視レコードを持つ                          |
| StockMaster      | DividendYieldHistory                                             | 1:N  | 銘柄は複数の日次配当利回り履歴を持つ                    |
| EdinetDocument   | DividendYieldHistory                                             | 1:N  | ドキュメントは複数の履歴レコードで参照される            |
| StockMaster      | RelativeStrength                                                 | 1:N  | 銘柄は複数のレラティブストレングス計算結果を持つ        |
| StockMaster      | ScreeningResults                                                 | 1:N  | 銘柄は複数のスクリーニング結果を持つ                    |
| StockMaster      | StockCodeMapping                                                 | 1:N  | 銘柄はEDINET対応企業コード（1つ以上）を持つ可能性がある |
| StockCodeMapping | EdinetDocument                                                   | 1:N  | マッピングを通じてEDINETドキュメントと連結              |
| EdinetDocument   | EdinetProfitAndLoss/StockDividend/CashFlowStatement/BalanceSheet | 1:N  | ドキュメントメタデータは複数の財務データを共有           |
| SP500StockMaster | SP500Stocks_1d（他の時間軸も同様）                               | 1:N  | S&P500銘柄は複数の日足株価データを持つ                  |

## Naming Conventions

- **PK**: Primary Key（主キー）
- **FK**: Foreign Key（外部キー）
- **UK**: Unique Key（ユニークキー）
- テーブル名: snake_case
- カラム名: snake_case
- タイムスタンプ: `created_at`, `updated_at`（UTC, timezone aware）
