"""yfinanceから取得できる財務情報のサンプル表示スクリプト.

トヨタ自動車（7203）を例に、yfinance.Ticker.infoから取得できる
財務情報を確認します。
"""

import json

import yfinance as yf


def fetch_financial_info(symbol: str) -> dict:
    """
    指定された銘柄の財務情報を取得します。

    Args:
        symbol: 銘柄コード（例: "7203.T"）

    Returns:
        dict: 財務情報の辞書
    """
    print(f"\n{'='*60}")
    print(f"銘柄コード: {symbol}")
    print(f"{'='*60}\n")

    ticker = yf.Ticker(symbol)
    info = ticker.info

    return info


def display_key_financial_metrics(info: dict) -> None:
    """
    主要な財務指標を見やすく表示します。

    Args:
        info: yfinance.Ticker.infoから取得した情報
    """
    print("【基本情報】")
    print(f"  会社名: {info.get('longName', 'N/A')}")
    print(f"  短縮名: {info.get('shortName', 'N/A')}")
    print(f"  セクター: {info.get('sector', 'N/A')}")
    print(f"  業種: {info.get('industry', 'N/A')}")
    print(f"  国: {info.get('country', 'N/A')}")
    print(f"  通貨: {info.get('currency', 'N/A')}")
    print(f"  取引所: {info.get('exchange', 'N/A')}")

    print("\n【株価情報】")
    print(f"  現在株価: {info.get('currentPrice', 'N/A')}")
    print(f"  前日終値: {info.get('previousClose', 'N/A')}")
    print(f"  始値: {info.get('open', 'N/A')}")
    print(f"  日中高値: {info.get('dayHigh', 'N/A')}")
    print(f"  日中安値: {info.get('dayLow', 'N/A')}")
    print(f"  52週高値: {info.get('fiftyTwoWeekHigh', 'N/A')}")
    print(f"  52週安値: {info.get('fiftyTwoWeekLow', 'N/A')}")

    print("\n【企業規模・評価指標】")
    market_cap = info.get("marketCap")
    if market_cap:
        print(f"  時価総額: ¥{market_cap:,}")
    else:
        print(f"  時価総額: N/A")

    enterprise_value = info.get("enterpriseValue")
    if enterprise_value:
        print(f"  企業価値: ¥{enterprise_value:,}")
    else:
        print(f"  企業価値: N/A")

    print(f"  PER (実績): {info.get('trailingPE', 'N/A')}")
    print(f"  PER (予想): {info.get('forwardPE', 'N/A')}")
    print(f"  PBR: {info.get('priceToBook', 'N/A')}")
    print(f"  PSR: {info.get('priceToSalesTrailing12Months', 'N/A')}")
    print(f"  PEG Ratio: {info.get('pegRatio', 'N/A')}")

    print("\n【収益性指標】")
    print(f"  EPS (実績): {info.get('trailingEps', 'N/A')}")
    print(f"  EPS (予想): {info.get('forwardEps', 'N/A')}")
    print(f"  1株当たり純資産: {info.get('bookValue', 'N/A')}")
    print(f"  利益率: {info.get('profitMargins', 'N/A')}")
    print(f"  営業利益率: {info.get('operatingMargins', 'N/A')}")
    print(f"  ROE: {info.get('returnOnEquity', 'N/A')}")
    print(f"  ROA: {info.get('returnOnAssets', 'N/A')}")

    print("\n【配当情報】")
    dividend_rate = info.get("dividendRate")
    dividend_yield = info.get("dividendYield")
    if dividend_rate:
        print(f"  年間配当: ¥{dividend_rate}")
    else:
        print(f"  年間配当: N/A")

    if dividend_yield:
        print(f"  配当利回り: {dividend_yield * 100:.2f}%")
    else:
        print(f"  配当利回り: N/A")

    print(f"  配当性向: {info.get('payoutRatio', 'N/A')}")
    print(f"  ex配当日: {info.get('exDividendDate', 'N/A')}")

    print("\n【財務健全性】")
    total_cash = info.get("totalCash")
    total_debt = info.get("totalDebt")
    if total_cash:
        print(f"  現金・預金: ¥{total_cash:,}")
    else:
        print(f"  現金・預金: N/A")

    if total_debt:
        print(f"  総負債: ¥{total_debt:,}")
    else:
        print(f"  総負債: N/A")

    print(f"  負債比率: {info.get('debtToEquity', 'N/A')}")
    print(f"  流動比率: {info.get('currentRatio', 'N/A')}")
    print(f"  当座比率: {info.get('quickRatio', 'N/A')}")

    print("\n【売上・利益】")
    total_revenue = info.get("totalRevenue")
    if total_revenue:
        print(f"  総売上高: ¥{total_revenue:,}")
    else:
        print(f"  総売上高: N/A")

    revenue_per_share = info.get("revenuePerShare")
    print(
        f"  1株当たり売上高: {revenue_per_share if revenue_per_share else 'N/A'}"
    )

    print(f"  売上成長率: {info.get('revenueGrowth', 'N/A')}")
    print(f"  利益成長率: {info.get('earningsGrowth', 'N/A')}")

    print("\n【取引情報】")
    print(f"  出来高: {info.get('volume', 'N/A')}")
    print(f"  平均出来高: {info.get('averageVolume', 'N/A')}")
    print(f"  ベータ値: {info.get('beta', 'N/A')}")
    print(f"  発行済株式数: {info.get('sharesOutstanding', 'N/A')}")
    print(f"  浮動株: {info.get('floatShares', 'N/A')}")

    print("\n【アナリスト評価】")
    print(f"  目標株価: {info.get('targetMeanPrice', 'N/A')}")
    print(f"  目標株価（高値）: {info.get('targetHighPrice', 'N/A')}")
    print(f"  目標株価（安値）: {info.get('targetLowPrice', 'N/A')}")
    print(f"  推奨評価: {info.get('recommendationKey', 'N/A')}")
    print(f"  推奨数: {info.get('numberOfAnalystOpinions', 'N/A')}")


def save_full_info_to_json(info: dict, symbol: str) -> None:
    """
    取得した全情報をJSONファイルに保存します。

    Args:
        info: yfinance.Ticker.infoから取得した情報
        symbol: 銘柄コード
    """
    filename = f"work/financial_info_{symbol.replace('.', '_')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"全情報を {filename} に保存しました")
    print(f"取得できたキーの総数: {len(info)}")
    print(f"{'='*60}\n")

    print("【取得できたキー一覧】")
    for i, key in enumerate(sorted(info.keys()), 1):
        print(f"  {i:3d}. {key}")


def main():
    """メイン処理"""
    # トヨタ自動車の財務情報を取得
    symbol = "7203.T"

    try:
        info = fetch_financial_info(symbol)

        # 主要な財務指標を表示
        display_key_financial_metrics(info)

        # 全情報をJSONに保存
        save_full_info_to_json(info, symbol)

        print("\n【注意事項】")
        print("  - N/A と表示される項目は、データが取得できなかった項目です")
        print("  - 財務情報はリアルタイムではなく、遅延がある場合があります")
        print("  - 一部の指標は米国株のみで提供される場合があります")

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
