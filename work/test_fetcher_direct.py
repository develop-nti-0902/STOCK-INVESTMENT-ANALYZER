#!/usr/bin/env python3
"""
Nikkei225Fetcher の動作確認
修正済みの fetcher で実際に何行取得されるか確認
"""

import asyncio
import sys

from app.services.data_synchronization.market_data.nikkei225.fetcher import Nikkei225Fetcher


async def main():
    fetcher = Nikkei225Fetcher()

    print("=" * 60)
    print("Nikkei225Fetcher 直接テスト")
    print("=" * 60)

    print("\n[テスト1] max_period=None（全データ取得）")
    df = await fetcher.fetch(max_period=None)
    print(f"取得データ: {len(df)} 行")
    if len(df) > 0:
        print(f"期間: {df.index.min()} ～ {df.index.max()}")
        print(f"カラム: {list(df.columns)}")
        print(f"\n最初の5行:")
        print(df.head())
        print(f"\n最後の5行:")
        print(df.tail())

    print("\n[テスト2] max_period=30（過去30日）")
    df2 = await fetcher.fetch(max_period=30)
    print(f"取得データ: {len(df2)} 行")
    if len(df2) > 0:
        print(f"期間: {df2.index.min()} ～ {df2.index.max()}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\nエラー: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
