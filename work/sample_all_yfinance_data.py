"""yfinanceで取得可能な全データの確認スクリプト."""

import json
from datetime import datetime

import pandas as pd
import yfinance as yf


def print_section(title: str) -> None:
    """セクションタイトルを表示."""
    print("\n" + "=" * 80)
    print(title)
    print("" + "=" * 80 + "\n")


def print_dataframe_info(df: pd.DataFrame, name: str) -> dict:
    """
    DataFrameの構造情報を表示し、辞書として返す.

    Returns:
        dict: テーブル設計の参考情報
    """
    print("【" + name + "】")

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        print("  データなし\n")
        return {"available": False}

    info = {
        "available": True,
        "type": "DataFrame",
        "shape": (df.shape if isinstance(df, pd.DataFrame) else f"Series: {len(df)}"),
    }

    print("  データ型: " + ("DataFrame" if isinstance(df, pd.DataFrame) else "Series"))

    if isinstance(df, pd.DataFrame):
        print(f"  形状: {df.shape[0]}行 × {df.shape[1]}列")
        print(f"  インデックス型: {type(df.index).__name__}")
        print(f"  列一覧 ({len(df.columns)}個):")

        columns_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null = df[col].notna().sum()
            null_count = df[col].isna().sum()
            columns_info.append(
                {
                    "column": str(col),
                    "dtype": dtype,
                    "non_null": int(non_null),
                    "null_count": int(null_count),
                }
            )
            print(f"    - {col} ({dtype}): {non_null}件 (null: {null_count})")

        info["columns"] = columns_info

        # サンプルデータ
        print("\n  サンプルデータ（最初の3行）:")
        print(df.head(3).to_string(max_colwidth=30))

    elif isinstance(df, pd.Series):
        print("  データ数: {}件".format(len(df)))
        print("  インデックス型: {}".format(type(df.index).__name__))
        print("  値の型: {}".format(df.dtype))
        print("\n  サンプルデータ（最初の5件）:")
        for date, value in df.head(5).items():
            print(f"    {date}: {value}")

        info["data_count"] = len(df)
        info["dtype"] = str(df.dtype)

    print()
    return info


def explore_all_yfinance_data(symbol: str) -> dict:
    """
    yfinanceの全データを取得して探索する.

    Returns:
        dict: 全データの構造情報
    """
    print_section(f"yfinance 全データ探索: {symbol}")

    ticker = yf.Ticker(symbol)
    all_data_info = {}

    # 1. 基本情報 (info)
    print_section("1. 基本情報 (Ticker.info)")
    info = ticker.info
    print(f"取得可能なキー数: {len(info)}")
    print("主要なキー:")

    # カテゴリごとに分類
    categories = {
        "企業基本情報": [
            "symbol",
            "shortName",
            "longName",
            "sector",
            "industry",
            "country",
            "city",
            "website",
            "fullTimeEmployees",
        ],
        "株価情報": [
            "currentPrice",
            "previousClose",
            "open",
            "dayHigh",
            "dayLow",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
            "volume",
            "averageVolume",
        ],
        "評価指標": [
            "marketCap",
            "enterpriseValue",
            "trailingPE",
            "forwardPE",
            "priceToBook",
            "priceToSalesTrailing12Months",
            "pegRatio",
        ],
        "収益性": [
            "trailingEps",
            "forwardEps",
            "bookValue",
            "profitMargins",
            "operatingMargins",
            "returnOnEquity",
            "returnOnAssets",
        ],
        "配当": [
            "dividendRate",
            "dividendYield",
            "payoutRatio",
            "exDividendDate",
        ],
        "財務健全性": [
            "totalCash",
            "totalDebt",
            "debtToEquity",
            "currentRatio",
            "quickRatio",
        ],
        "成長性": [
            "revenueGrowth",
            "earningsGrowth",
            "totalRevenue",
            "revenuePerShare",
        ],
        "アナリスト評価": [
            "targetMeanPrice",
            "targetHighPrice",
            "targetLowPrice",
            "recommendationKey",
            "numberOfAnalystOpinions",
        ],
    }

    info_structure = {}
    for category, keys in categories.items():
        print("\n  【" + category + "】")
        available_keys = []
        for key in keys:
            value = info.get(key)
            if value is not None:
                print("    ✓ {}: {}".format(key, type(value).__name__))
                available_keys.append({"key": key, "type": type(value).__name__})
            else:
                print("    ✗ {}: (データなし)".format(key))
        info_structure[category] = available_keys

    all_data_info["info"] = {
        "total_keys": len(info),
        "categories": info_structure,
    }

    # 2. 株価履歴 (history)
    print_section("2. 株価履歴 (Ticker.history)")
    history = ticker.history(period="1mo")
    all_data_info["history"] = print_dataframe_info(history, "株価履歴")

    # 3. 損益計算書（年次）
    print_section("3. 損益計算書 - 年次 (Ticker.financials)")
    financials = ticker.financials
    all_data_info["financials"] = print_dataframe_info(financials, "損益計算書（年次）")

    # 4. 損益計算書（四半期）
    print_section("4. 損益計算書 - 四半期 (Ticker.quarterly_financials)")
    quarterly_financials = ticker.quarterly_financials
    all_data_info["quarterly_financials"] = print_dataframe_info(
        quarterly_financials, "損益計算書（四半期）"
    )

    # 5. バランスシート（年次）
    print_section("5. バランスシート - 年次 (Ticker.balance_sheet)")
    balance_sheet = ticker.balance_sheet
    all_data_info["balance_sheet"] = print_dataframe_info(balance_sheet, "バランスシート（年次）")

    # 6. バランスシート（四半期）
    print_section("6. バランスシート - 四半期 (Ticker.quarterly_balance_sheet)")
    quarterly_balance_sheet = ticker.quarterly_balance_sheet
    all_data_info["quarterly_balance_sheet"] = print_dataframe_info(
        quarterly_balance_sheet, "バランスシート（四半期）"
    )

    # 7. キャッシュフロー計算書（年次）
    print_section("7. キャッシュフロー - 年次 (Ticker.cashflow)")
    cashflow = ticker.cashflow
    all_data_info["cashflow"] = print_dataframe_info(cashflow, "キャッシュフロー（年次）")

    # 8. キャッシュフロー計算書（四半期）
    print_section("8. キャッシュフロー - 四半期 (Ticker.quarterly_cashflow)")
    quarterly_cashflow = ticker.quarterly_cashflow
    all_data_info["quarterly_cashflow"] = print_dataframe_info(
        quarterly_cashflow, "キャッシュフロー（四半期）"
    )

    # 9. 配当履歴
    print_section("9. 配当履歴 (Ticker.dividends)")
    dividends = ticker.dividends
    all_data_info["dividends"] = print_dataframe_info(dividends, "配当履歴")

    # 10. 株式分割履歴
    print_section("10. 株式分割履歴 (Ticker.splits)")
    splits = ticker.splits
    all_data_info["splits"] = print_dataframe_info(splits, "株式分割履歴")

    # 11. アクション（配当+分割）
    print_section("11. アクション (Ticker.actions)")
    actions = ticker.actions
    all_data_info["actions"] = print_dataframe_info(actions, "アクション")

    # 12. 発行済株式数
    print_section("12. 発行済株式数の履歴 (Ticker.get_shares_full)")
    try:
        shares = ticker.get_shares_full(start="2020-01-01")
        all_data_info["shares"] = print_dataframe_info(shares, "発行済株式数")
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["shares"] = {"available": False, "error": str(e)}

    # 13. アナリスト推奨
    print_section("13. アナリスト推奨 (Ticker.recommendations)")
    try:
        recommendations = ticker.recommendations
        all_data_info["recommendations"] = print_dataframe_info(recommendations, "アナリスト推奨")
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["recommendations"] = {
            "available": False,
            "error": str(e),
        }

    # 14. カレンダー（イベント）
    print_section("14. カレンダー (Ticker.calendar)")
    try:
        calendar = ticker.calendar
        print("【カレンダー】")
        if calendar is not None and not calendar.empty:
            print(calendar)
            all_data_info["calendar"] = {
                "available": True,
                "data": str(calendar),
            }
        else:
            print("  データなし\n")
            all_data_info["calendar"] = {"available": False}
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["calendar"] = {"available": False, "error": str(e)}

    # 15. 決算発表日
    print_section("15. 決算発表日 (Ticker.earnings_dates)")
    try:
        earnings_dates = ticker.earnings_dates
        all_data_info["earnings_dates"] = print_dataframe_info(earnings_dates, "決算発表日")
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["earnings_dates"] = {"available": False, "error": str(e)}

    # 16. 機関投資家保有状況
    print_section("16. 機関投資家保有 (Ticker.institutional_holders)")
    try:
        institutional_holders = ticker.institutional_holders
        all_data_info["institutional_holders"] = print_dataframe_info(
            institutional_holders, "機関投資家保有"
        )
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["institutional_holders"] = {
            "available": False,
            "error": str(e),
        }

    # 17. 主要株主
    print_section("17. 主要株主 (Ticker.major_holders)")
    try:
        major_holders = ticker.major_holders
        all_data_info["major_holders"] = print_dataframe_info(major_holders, "主要株主")
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["major_holders"] = {"available": False, "error": str(e)}

    # 18. 投資信託保有状況
    print_section("18. 投資信託保有 (Ticker.mutualfund_holders)")
    try:
        mutualfund_holders = ticker.mutualfund_holders
        all_data_info["mutualfund_holders"] = print_dataframe_info(
            mutualfund_holders, "投資信託保有"
        )
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["mutualfund_holders"] = {
            "available": False,
            "error": str(e),
        }

    # 19. インサイダー取引
    print_section("19. インサイダー取引 (Ticker.insider_transactions)")
    try:
        insider_transactions = ticker.insider_transactions
        all_data_info["insider_transactions"] = print_dataframe_info(
            insider_transactions, "インサイダー取引"
        )
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["insider_transactions"] = {
            "available": False,
            "error": str(e),
        }

    # 20. 内部関係者保有
    print_section("20. 内部関係者保有 (Ticker.insider_roster_holders)")
    try:
        insider_roster_holders = ticker.insider_roster_holders
        all_data_info["insider_roster_holders"] = print_dataframe_info(
            insider_roster_holders, "内部関係者保有"
        )
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["insider_roster_holders"] = {
            "available": False,
            "error": str(e),
        }

    # 21. ESG/サステナビリティ
    print_section("21. ESG情報 (Ticker.sustainability)")
    try:
        sustainability = ticker.sustainability
        all_data_info["sustainability"] = print_dataframe_info(sustainability, "ESG情報")
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["sustainability"] = {"available": False, "error": str(e)}

    # 22. オプション有効期限
    print_section("22. オプション有効期限 (Ticker.options)")
    try:
        options = ticker.options
        print("【オプション有効期限】")
        if options and len(options) > 0:
            print("  利用可能な期限: {}件".format(len(options)))
            for opt in options[:5]:
                print("    - {}".format(opt))
            all_data_info["options"] = {
                "available": True,
                "count": len(options),
            }
        else:
            print("  データなし\n")
            all_data_info["options"] = {"available": False}
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["options"] = {"available": False, "error": str(e)}

    # 23. 四半期決算（EPS）
    print_section("23. 四半期決算 (Ticker.earnings)")
    try:
        earnings = ticker.earnings
        all_data_info["earnings"] = print_dataframe_info(earnings, "四半期決算")
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["earnings"] = {"available": False, "error": str(e)}

    # 24. 四半期決算詳細
    print_section("24. 四半期決算詳細 (Ticker.quarterly_earnings)")
    try:
        quarterly_earnings = ticker.quarterly_earnings
        all_data_info["quarterly_earnings"] = print_dataframe_info(
            quarterly_earnings, "四半期決算詳細"
        )
    except Exception as e:
        print(f"  取得エラー: {e}\n")
        all_data_info["quarterly_earnings"] = {
            "available": False,
            "error": str(e),
        }

    return all_data_info


def generate_table_design_recommendations(all_data_info: dict) -> None:
    """取得したデータ構造に基づいて、テーブル設計の推奨案を生成."""
    print_section("テーブル設計の推奨案")

    tables = {
        "1. stock_basic_info": {
            "説明": "銘柄の基本情報（企業情報）",
            "更新頻度": "低頻度（企業情報変更時のみ）",
            "主要カラム": [
                "symbol (PK)",
                "short_name",
                "long_name",
                "sector",
                "industry",
                "country",
                "city",
                "website",
                "full_time_employees",
                "updated_at",
            ],
            "データソース": "Ticker.info",
        },
        "2. stock_price_daily": {
            "説明": "日次株価データ（既存）",
            "更新頻度": "毎日",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "trade_date",
                "open_price",
                "high",
                "low",
                "close",
                "volume",
                "adj_close",
            ],
            "データソース": "Ticker.history()",
        },
        "3. stock_financial_info": {
            "説明": "日次更新される財務指標（時価総額、PER、PBRなど）",
            "更新頻度": "毎日",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "date",
                "market_cap",
                "enterprise_value",
                "trailing_pe",
                "forward_pe",
                "price_to_book",
                "price_to_sales",
                "trailing_eps",
                "forward_eps",
                "book_value",
                "dividend_rate",
                "dividend_yield",
                "payout_ratio",
                "current_price",
                "updated_at",
            ],
            "データソース": "Ticker.info（日次スナップショット）",
        },
        "4. stock_financials_annual": {
            "説明": "年次損益計算書",
            "更新頻度": "年次（決算発表時）",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "fiscal_date",
                "total_revenue",
                "net_income",
                "basic_eps",
                "diluted_eps",
                "ebitda",
                "operating_income",
                "gross_profit",
                "...（財務諸表の全項目）",
                "updated_at",
            ],
            "データソース": "Ticker.financials",
        },
        "5. stock_financials_quarterly": {
            "説明": "四半期損益計算書",
            "更新頻度": "四半期",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "fiscal_date",
                "total_revenue",
                "net_income",
                "...（財務諸表の全項目）",
                "updated_at",
            ],
            "データソース": "Ticker.quarterly_financials",
        },
        "6. stock_balance_sheet_annual": {
            "説明": "年次バランスシート",
            "更新頻度": "年次",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "fiscal_date",
                "total_assets",
                "stockholders_equity",
                "total_debt",
                "current_assets",
                "current_liabilities",
                "...（BS全項目）",
                "updated_at",
            ],
            "データソース": "Ticker.balance_sheet",
        },
        "7. stock_balance_sheet_quarterly": {
            "説明": "四半期バランスシート",
            "更新頻度": "四半期",
            "主要カラム": ["（年次と同様）"],
            "データソース": "Ticker.quarterly_balance_sheet",
        },
        "8. stock_cashflow_annual": {
            "説明": "年次キャッシュフロー",
            "更新頻度": "年次",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "fiscal_date",
                "operating_cashflow",
                "investing_cashflow",
                "financing_cashflow",
                "free_cashflow",
                "...（CF全項目）",
                "updated_at",
            ],
            "データソース": "Ticker.cashflow",
        },
        "9. stock_cashflow_quarterly": {
            "説明": "四半期キャッシュフロー",
            "更新頻度": "四半期",
            "主要カラム": ["（年次と同様）"],
            "データソース": "Ticker.quarterly_cashflow",
        },
        "10. stock_dividends": {
            "説明": "配当履歴",
            "更新頻度": "配当発表時",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "ex_dividend_date",
                "dividend_amount",
                "updated_at",
            ],
            "データソース": "Ticker.dividends",
        },
        "11. stock_splits": {
            "説明": "株式分割履歴",
            "更新頻度": "分割実施時",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "split_date",
                "split_ratio",
                "updated_at",
            ],
            "データソース": "Ticker.splits",
        },
        "12. stock_shares_outstanding": {
            "説明": "発行済株式数の履歴",
            "更新頻度": "変更時",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "date",
                "shares_outstanding",
                "updated_at",
            ],
            "データソース": "Ticker.get_shares_full()",
        },
        "13. stock_analyst_recommendations": {
            "説明": "アナリスト推奨（米国株のみ）",
            "更新頻度": "推奨変更時",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "date",
                "firm",
                "to_grade",
                "from_grade",
                "action",
                "updated_at",
            ],
            "データソース": "Ticker.recommendations",
        },
        "14. stock_earnings_dates": {
            "説明": "決算発表日",
            "更新頻度": "四半期",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "earnings_date",
                "eps_estimate",
                "reported_eps",
                "surprise_percent",
                "updated_at",
            ],
            "データソース": "Ticker.earnings_dates",
        },
        "15. stock_holders_institutional": {
            "説明": "機関投資家保有状況（米国株のみ）",
            "更新頻度": "四半期",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "date_reported",
                "holder",
                "shares",
                "value",
                "percent_held",
                "updated_at",
            ],
            "データソース": "Ticker.institutional_holders",
        },
        "16. stock_insider_transactions": {
            "説明": "インサイダー取引（米国株のみ）",
            "更新頻度": "取引発生時",
            "主要カラム": [
                "id (PK)",
                "symbol (FK)",
                "start_date",
                "insider",
                "position",
                "transaction",
                "shares",
                "value",
                "updated_at",
            ],
            "データソース": "Ticker.insider_transactions",
        },
    }

    for table_name, info in tables.items():
        print(f"\n{table_name}")
        print(f"  説明: {info['説明']}")
        print(f"  更新頻度: {info['更新頻度']}")
        print(f"  データソース: {info['データソース']}")
        print("  主要カラム:")
        for col in info["主要カラム"]:
            print(f"    - {col}")

    print("\n" + "=" * 80)
    print("実装の優先順位の推奨")
    print("=" * 80)
    print(
        """
【フェーズ1: 基本機能】（既存実装済み）
  ✓ stock_master（銘柄マスタ）
  ✓ stock_price_daily（日次株価）

【フェーズ2: 財務指標】（次の実装候補）
  → stock_financial_info（日次財務指標: PER, PBR, 時価総額など）
  → stock_dividends（配当履歴）
  → stock_splits（株式分割履歴）

【フェーズ3: 財務諸表】
  → stock_financials_annual（年次損益計算書）
  → stock_balance_sheet_annual（年次バランスシート）
  → stock_cashflow_annual（年次キャッシュフロー）
  → stock_shares_outstanding（発行済株式数）

【フェーズ4: 四半期データ】
  → 各種四半期データテーブル

【フェーズ5: 高度な分析】（主に米国株向け）
  → アナリスト推奨、機関投資家保有、インサイダー取引など
    """
    )


def save_results(all_data_info: dict, symbol: str) -> None:
    """結果をJSONファイルに保存."""
    filename = f"work/yfinance_all_data_structure_{symbol.replace('.', '_')}.json"

    # DataFrameなどをJSON化できる形式に変換
    def convert_to_serializable(obj):
        if isinstance(obj, (pd.DataFrame, pd.Series)):
            return str(obj)
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        return obj

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            all_data_info,
            f,
            ensure_ascii=False,
            indent=2,
            default=convert_to_serializable,
        )

    print("\n\n" + "=" * 80)
    print("データ構造情報を {} に保存しました".format(filename))
    print("" + "=" * 80)


def main():
    """メイン処理."""
    symbol = "7203.T"  # トヨタ自動車

    try:
        # 全データを探索
        all_data_info = explore_all_yfinance_data(symbol)

        # テーブル設計の推奨案を生成
        generate_table_design_recommendations(all_data_info)

        # 結果を保存
        save_results(all_data_info, symbol)

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
