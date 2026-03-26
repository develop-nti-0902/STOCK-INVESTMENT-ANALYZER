#!/usr/bin/env python3
"""
日経225のデータ最大期間取得テスト（複数パターン）
異なる開始日から期間を指定して、最大どれくらい遡れるか確認
"""

import sys
from datetime import datetime

import yfinance as yf


def test_max_period_variants():
    """様々な期間でデータ取得を試行"""
    print("=" * 70)
    print("日経225 - 複数期間パターンテスト")
    print("=" * 70)
    print(f"\n実行環境: {sys.executable}\n")

    test_cases = [
        ("1985-01-01", "1985年1月から"),
        ("1980-01-01", "1980年1月から"),
        ("1975-01-01", "1975年1月から"),
    ]

    for start_date, description in test_cases:
        try:
            print(f"\n[テスト] {description} のデータ取得...")
            print(f"  start={start_date}, end=2026-03-26")

            nikkei = yf.download("^N225", start=start_date, end="2026-03-26", progress=False)

            if len(nikkei) > 0:
                print(f"  ✓ 成功: {len(nikkei)} 行")
                print(f"    期間: {nikkei.index.min().date()} ～ {nikkei.index.max().date()}")
            else:
                print(f"  ✗ データなし")

        except Exception as e:
            print(f"  ✗ エラー: {type(e).__name__}: {e}")

    # 最後に、実際に最大遡れるデータを確認
    print("\n" + "=" * 70)
    print("実際の最大範囲データ取得（1951年から現在）:")
    print("=" * 70)

    try:
        nikkei_full = yf.download("^N225", start="1951-01-01", end="2026-03-26", progress=False)

        if len(nikkei_full) > 0:
            print(f"\n✓ 成功: {len(nikkei_full)} 行のデータが取得できました")
            print(f"\n期間: {nikkei_full.index.min().date()} ～ {nikkei_full.index.max().date()}")
            print(f"営業日数: {len(nikkei_full)} 日")

            # 年代ごとのデータ数を集計
            print("\n年代ごとのデータ行数:")
            nikkei_full.index = nikkei_full.index.to_series().dt.year
            year_counts = nikkei_full.groupby(level=0).size()
            print(year_counts.to_string())
        else:
            print("✗ データなし")

    except Exception as e:
        print(f"✗ エラー: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_max_period_variants()
