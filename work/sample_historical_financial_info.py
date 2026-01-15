"""yfinanceから取得できる過去の財務情報のサンプル表示スクリプト.

配当利回り、配当性向、PER、PBRの過去データを取得・計算する方法を確認します。
トヨタ自動車（7203）を例に使用します。
"""

import json
from datetime import datetime

import pandas as pd
import yfinance as yf


def fetch_historical_financial_data(symbol: str) -> dict:
    """
    指定された銘柄の過去の財務データを取得します。

    Args:
        symbol: 銘柄コード（例: "7203.T"）

    Returns:
        dict: 各種財務データを格納した辞書
    """
    print(f"\n{'='*60}")
    print(f"銘柄コード: {symbol}")
    print(f"{'='*60}\n")

    ticker = yf.Ticker(symbol)

    result = {
        "symbol": symbol,
        "company_name": ticker.info.get("longName", "N/A"),
    }

    print("データ取得中...")

    # 1. 損益計算書（年次）
    print("  - 損益計算書（年次）を取得中...")
    result["financials"] = ticker.financials

    # 2. 損益計算書（四半期）
    print("  - 損益計算書（四半期）を取得中...")
    result["quarterly_financials"] = ticker.quarterly_financials

    # 3. バランスシート（年次）
    print("  - バランスシート（年次）を取得中...")
    result["balance_sheet"] = ticker.balance_sheet

    # 4. バランスシート（四半期）
    print("  - バランスシート（四半期）を取得中...")
    result["quarterly_balance_sheet"] = ticker.quarterly_balance_sheet

    # 5. 配当履歴
    print("  - 配当履歴を取得中...")
    result["dividends"] = ticker.dividends

    # 6. 株価履歴（過去5年）
    print("  - 株価履歴を取得中...")
    result["history"] = ticker.history(period="5y")

    # 7. 発行済株式数の履歴
    print("  - 株式数情報を取得中...")
    result["shares"] = ticker.get_shares_full(start="2019-01-01")

    print("データ取得完了！\n")

    return result


def display_financials_overview(financials: pd.DataFrame) -> None:
    """
    損益計算書の概要を表示します。

    Args:
        financials: yfinance.Ticker.financialsから取得したDataFrame
    """
    print("\n【損益計算書（年次）】")

    if financials.empty:
        print("  データが取得できませんでした")
        return

    print(f"  取得期間: {len(financials.columns)}期分")
    print(f"  利用可能な項目数: {len(financials.index)}")
    print("\n  主要項目:")

    # 日付を新しい順にソート
    financials_sorted = financials.sort_index(axis=1, ascending=False)

    for idx, item in enumerate(financials_sorted.index[:15], 1):
        print(f"    {idx:2d}. {item}")

    if len(financials_sorted.index) > 15:
        print(f"    ... 他 {len(financials_sorted.index) - 15} 項目")

    # 主要な財務データを表示
    print("\n  【主要データ】")
    key_items = ["Total Revenue", "Net Income", "Basic EPS", "Diluted EPS"]

    for item in key_items:
        if item in financials_sorted.index:
            print(f"\n  ■ {item}")
            for date in financials_sorted.columns[:3]:  # 最新3期分
                value = financials_sorted.loc[item, date]
                if pd.notna(value):
                    print(f"      {date.strftime('%Y-%m-%d')}: {value:,.0f}")


def display_balance_sheet_overview(balance_sheet: pd.DataFrame) -> None:
    """
    バランスシートの概要を表示します。

    Args:
        balance_sheet: yfinance.Ticker.balance_sheetから取得したDataFrame
    """
    print("\n【バランスシート（年次）】")

    if balance_sheet.empty:
        print("  データが取得できませんでした")
        return

    print(f"  取得期間: {len(balance_sheet.columns)}期分")
    print(f"  利用可能な項目数: {len(balance_sheet.index)}")
    print("\n  主要項目:")

    # 日付を新しい順にソート
    bs_sorted = balance_sheet.sort_index(axis=1, ascending=False)

    for idx, item in enumerate(bs_sorted.index[:15], 1):
        print(f"    {idx:2d}. {item}")

    if len(bs_sorted.index) > 15:
        print(f"    ... 他 {len(bs_sorted.index) - 15} 項目")

    # 主要な財務データを表示
    print("\n  【主要データ】")
    key_items = ["Total Assets", "Stockholders Equity", "Total Debt"]

    for item in key_items:
        if item in bs_sorted.index:
            print(f"\n  ■ {item}")
            for date in bs_sorted.columns[:3]:  # 最新3期分
                value = bs_sorted.loc[item, date]
                if pd.notna(value):
                    print(f"      {date.strftime('%Y-%m-%d')}: {value:,.0f}")


def display_dividends_history(dividends: pd.Series) -> None:
    """
    配当履歴を表示します。

    Args:
        dividends: yfinance.Ticker.dividendsから取得したSeries
    """
    print("\n【配当履歴】")

    if dividends.empty:
        print("  データが取得できませんでした")
        return

    print(f"  取得期間: {len(dividends)}回分")
    print(
        f"  期間: {dividends.index[0].strftime('%Y-%m-%d')} ～ {dividends.index[-1].strftime('%Y-%m-%d')}"
    )

    # 最新10件を表示
    print("\n  最新の配当記録:")
    for date, dividend in dividends.tail(10).items():
        print(f"    {date.strftime('%Y-%m-%d')}: ¥{dividend:.2f}")

    # 年間配当の集計
    print("\n  年間配当の推移:")
    yearly_dividends = dividends.resample("YE").sum()
    for date, total in yearly_dividends.tail(5).items():
        print(f"    {date.year}年: ¥{total:.2f}")


def display_shares_history(shares) -> None:
    """
    発行済株式数の履歴を表示します。

    Args:
        shares: 発行済株式数のDataFrameまたはSeries
    """
    print("\n【発行済株式数の履歴】")

    if shares is None or shares.empty:
        print("  データが取得できませんでした")
        return

    print(f"  取得期間: {len(shares)}件")

    # 最新10件を表示
    print("\n  最新の記録:")
    if isinstance(shares, pd.Series):
        for date, shares_count in shares.tail(10).items():
            print(f"    {date.strftime('%Y-%m-%d')}: {shares_count:,.0f}株")
    else:
        for date, row in shares.tail(10).iterrows():
            shares_count = row.iloc[0] if len(row) > 0 else row
            print(f"    {date.strftime('%Y-%m-%d')}: {shares_count:,.0f}株")


def calculate_historical_metrics(data: dict) -> pd.DataFrame:
    """
    過去のPER、PBR、配当利回り、配当性向を計算します。

    Args:
        data: fetch_historical_financial_dataで取得したデータ

    Returns:
        pd.DataFrame: 計算結果のDataFrame
    """
    print("\n" + "=" * 60)
    print("指標の計算")
    print("=" * 60)

    results = []

    # 株価データを取得（月末の終値を使用）
    history = data["history"]
    monthly_prices = history["Close"].resample("ME").last()

    # 財務データを取得
    financials = data["financials"]
    balance_sheet = data["balance_sheet"]
    dividends = data["dividends"]

    # 年次配当を計算
    yearly_dividends = dividends.resample("YE").sum()

    print("\n計算方法:")
    print("  - PER = 株価 ÷ EPS（1株当たり利益）")
    print("  - PBR = 株価 ÷ BPS（1株当たり純資産）")
    print("  - 配当利回り = 年間配当 ÷ 株価")
    print("  - 配当性向 = 配当 ÷ 純利益\n")

    # 各年度ごとに計算
    for date in financials.columns:
        year = date.year

        # その年の12月末の株価を取得
        year_end_prices = monthly_prices[monthly_prices.index.year == year]
        if year_end_prices.empty:
            continue

        stock_price = year_end_prices.iloc[-1]

        # EPS
        eps = None
        if "Basic EPS" in financials.index:
            eps = financials.loc["Basic EPS", date]
        elif "Diluted EPS" in financials.index:
            eps = financials.loc["Diluted EPS", date]

        # 純資産
        equity = None
        if "Stockholders Equity" in balance_sheet.index:
            if date in balance_sheet.columns:
                equity = balance_sheet.loc["Stockholders Equity", date]

        # 発行済株式数（infoから取得）
        shares_outstanding = data.get("shares")
        shares_count = None
        if shares_outstanding is not None and not shares_outstanding.empty:
            # その年に最も近い株式数を取得
            if isinstance(shares_outstanding, pd.Series):
                shares_for_year = shares_outstanding[
                    shares_outstanding.index.year <= year
                ]
                if not shares_for_year.empty:
                    shares_count = shares_for_year.iloc[-1]
                else:
                    shares_count = None
            else:
                shares_for_year = shares_outstanding[
                    shares_outstanding.index.year <= year
                ]
                if not shares_for_year.empty:
                    shares_count = (
                        shares_for_year.iloc[-1].iloc[0]
                        if len(shares_for_year.iloc[-1]) > 0
                        else shares_for_year.iloc[-1]
                    )
                else:
                    shares_count = None

        # BPS（1株当たり純資産）を計算
        bps = None
        if (
            equity is not None
            and shares_count is not None
            and shares_count > 0
        ):
            bps = equity / shares_count

        # 純利益
        net_income = None
        if "Net Income" in financials.index:
            net_income = financials.loc["Net Income", date]

        # その年の配当
        year_dividends = yearly_dividends[yearly_dividends.index.year == year]
        total_dividend = (
            year_dividends.iloc[0] if not year_dividends.empty else None
        )

        # 指標を計算
        per = stock_price / eps if eps and eps > 0 else None
        pbr = stock_price / bps if bps and bps > 0 else None
        dividend_yield = (
            (total_dividend / stock_price * 100)
            if total_dividend and stock_price > 0
            else None
        )

        # 配当性向 = 配当総額 ÷ 純利益
        dividend_payout = None
        if total_dividend and net_income and shares_count and net_income > 0:
            total_dividend_amount = total_dividend * shares_count
            dividend_payout = total_dividend_amount / net_income * 100

        results.append(
            {
                "年度": year,
                "株価": stock_price,
                "EPS": eps,
                "BPS": bps,
                "純利益": net_income,
                "年間配当": total_dividend,
                "PER": per,
                "PBR": pbr,
                "配当利回り(%)": dividend_yield,
                "配当性向(%)": dividend_payout,
            }
        )

    df = pd.DataFrame(results)
    df = df.sort_values("年度", ascending=False)

    return df


def display_calculated_metrics(df: pd.DataFrame) -> None:
    """
    計算された指標を表示します。

    Args:
        df: 計算結果のDataFrame
    """
    print("\n" + "=" * 60)
    print("過去の財務指標")
    print("=" * 60)

    if df.empty:
        print("  計算できるデータがありませんでした")
        return

    print("\n")

    # 表示形式を整える
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.float_format", lambda x: f"{x:.2f}")

    # 主要指標のみ表示
    display_columns = [
        "年度",
        "株価",
        "PER",
        "PBR",
        "配当利回り(%)",
        "配当性向(%)",
    ]
    display_df = df[display_columns].copy()

    print(display_df.to_string(index=False))

    # 詳細情報
    print("\n" + "-" * 60)
    print("詳細データ")
    print("-" * 60)

    for _, row in df.iterrows():
        print(f"\n【{int(row['年度'])}年度】")
        print(f"  株価: ¥{row['株価']:.2f}")
        if pd.notna(row["EPS"]):
            print(f"  EPS: ¥{row['EPS']:.2f}")
        if pd.notna(row["BPS"]):
            print(f"  BPS: ¥{row['BPS']:.2f}")
        if pd.notna(row["純利益"]):
            print(f"  純利益: ¥{row['純利益']:,.0f}")
        if pd.notna(row["年間配当"]):
            print(f"  年間配当: ¥{row['年間配当']:.2f}")
        if pd.notna(row["PER"]):
            print(f"  → PER: {row['PER']:.2f}倍")
        if pd.notna(row["PBR"]):
            print(f"  → PBR: {row['PBR']:.2f}倍")
        if pd.notna(row["配当利回り(%)"]):
            print(f"  → 配当利回り: {row['配当利回り(%)']:.2f}%")
        if pd.notna(row["配当性向(%)"]):
            print(f"  → 配当性向: {row['配当性向(%)']:.2f}%")


def save_to_csv(df: pd.DataFrame, symbol: str) -> None:
    """
    計算結果をCSVファイルに保存します。

    Args:
        df: 計算結果のDataFrame
        symbol: 銘柄コード
    """
    filename = f"work/historical_metrics_{symbol.replace('.', '_')}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n{'='*60}")
    print(f"計算結果を {filename} に保存しました")
    print(f"{'='*60}")


def main():
    """メイン処理"""
    symbol = "7203.T"

    try:
        # 過去の財務データを取得
        data = fetch_historical_financial_data(symbol)

        # 各データの概要を表示
        display_financials_overview(data["financials"])
        display_balance_sheet_overview(data["balance_sheet"])
        display_dividends_history(data["dividends"])
        display_shares_history(data["shares"])

        # 過去の指標を計算
        metrics_df = calculate_historical_metrics(data)

        # 結果を表示
        display_calculated_metrics(metrics_df)

        # CSVに保存
        save_to_csv(metrics_df, symbol)

        print("\n【注意事項】")
        print("  - 計算には年度末（12月末）の株価を使用しています")
        print(
            "  - N/A や計算できない項目は、元データが取得できなかった項目です"
        )
        print(
            "  - EPSやBPSはyfinanceから取得した財務諸表データを使用しています"
        )
        print("  - 配当性向は、配当総額を純利益で割って計算しています")

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
